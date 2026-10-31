import asyncio

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_user import user_dao
from backend.app.admin.model import User
from backend.common.exception import errors
from backend.common.log import log
from backend.common.pagination import paging_data
from backend.core.conf import settings
from backend.database.db import async_db_session
from backend.plugin.opensandbox.crud import sandbox_dao
from backend.plugin.opensandbox.model import SandboxRecord
from backend.plugin.opensandbox.schema.sandbox import (
    AdminOverview,
    CreateSandboxParam,
    SandboxInfo,
    SandboxOverview,
    SandboxRecordCreate,
    SandboxServiceStatus,
    UserOption,
)
from backend.plugin.opensandbox.utils.client import OpenSandboxError, open_sandbox_client
from backend.plugin.opensandbox.utils.dynamic_config import (
    ensure_sandbox_api_enabled,
    is_sandbox_api_enabled,
    load_sandbox_config,
)
from backend.utils.timezone import timezone


class SandboxService:
    """沙盒业务服务"""

    def __init__(self) -> None:
        self.active_sandboxes: set[str] = set()

    def mark_active(self, sandbox_id: str) -> None:
        self.active_sandboxes.add(sandbox_id)

    def unmark_active(self, sandbox_id: str) -> None:
        self.active_sandboxes.discard(sandbox_id)

    async def service_status(self, *, db: AsyncSession | None = None) -> SandboxServiceStatus:
        """获取 OpenSandbox 服务状态"""

        api_enabled = True
        if db is not None:
            api_enabled = await is_sandbox_api_enabled(db)
        server_available, version, message = await open_sandbox_client.health()
        if not api_enabled:
            available = False
            message = (
                '管理员已暂停沙盒 API；OpenSandbox Server 进程仍在运行'
                if server_available
                else '管理员已暂停沙盒 API；OpenSandbox Server 当前不可达'
            )
        else:
            available = server_available
        return SandboxServiceStatus(
            configured=open_sandbox_client.enabled,
            api_enabled=api_enabled,
            server_available=server_available,
            available=available,
            version=version,
            url=open_sandbox_client.base_url,
            api_key_configured=bool(settings.OPEN_SANDBOX_API_KEY),
            start_command_configured=bool(settings.OPEN_SANDBOX_SERVICE_START_COMMAND.strip()),
            stop_command_configured=bool(settings.OPEN_SANDBOX_SERVICE_STOP_COMMAND.strip()),
            message=message,
            checked_time=timezone.now(),
        )

    async def overview(self, *, db: AsyncSession, is_admin: bool) -> SandboxOverview:
        """获取工作台概览"""

        await load_sandbox_config(db)
        return SandboxOverview(
            service=await self.service_status(db=db),
            is_admin=is_admin,
            max_sandboxes=settings.OPEN_SANDBOX_MAX_SANDBOXES_PER_USER,
            idle_timeout_seconds=settings.OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS,
            auto_pause_enabled=settings.OPEN_SANDBOX_AUTO_PAUSE_ENABLED,
            default_image=settings.OPEN_SANDBOX_IMAGE,
            workspace_root=settings.OPEN_SANDBOX_WORKSPACE_ROOT,
        )

    async def admin_overview(self, *, db: AsyncSession) -> AdminOverview:
        """获取管理员概览"""

        await load_sandbox_config(db)
        return AdminOverview(
            service=await self.service_status(db=db),
            total_sandboxes=await sandbox_dao.count_all(db),
            running_sandboxes=await sandbox_dao.count_state(db, 'Running'),
            paused_sandboxes=await sandbox_dao.count_state(db, 'Paused'),
            total_users=await sandbox_dao.count_users(db),
            total_commands=await self._command_count(db),
        )

    async def _command_count(self, db: AsyncSession) -> int:
        from backend.plugin.opensandbox.crud.crud_command_log import command_log_dao

        return await command_log_dao.count_all(db)

    def _record_to_info(self, record: SandboxRecord | dict[str, Any]) -> SandboxInfo:
        def value(key: str) -> Any:
            return record.get(key) if isinstance(record, dict) else getattr(record, key, None)

        status = value('status') or 'Unknown'
        return SandboxInfo(
            sandbox_id=str(value('sandbox_id') or ''),
            name=value('name') or '',
            image=value('image') or '',
            state=status,
            reason=None,
            message=None,
            owner_id=int(value('user_id') or 0),
            owner_username=value('username') or '未关联用户',
            created_at=value('created_time'),
            expires_at=value('expires_at'),
            last_activity_time=value('last_activity_time'),
            auto_paused=status == 'Paused',
            workspace_root=settings.OPEN_SANDBOX_WORKSPACE_ROOT,
        )

    async def _resolve_owner(
        self,
        db: AsyncSession,
        *,
        user_id: int | None,
        username: str | None,
        fallback_user_id: int,
        fallback_username: str,
    ) -> tuple[int, str]:
        owner_id = user_id or fallback_user_id
        owner_username = username or fallback_username
        if owner_id:
            user = await user_dao.get(db, owner_id)
            if user:
                owner_username = user.username
        return owner_id, owner_username

    async def _upsert_remote(
        self,
        db: AsyncSession,
        remote: Any,
        *,
        fallback_user_id: int | None = None,
        fallback_username: str | None = None,
    ) -> SandboxRecord:
        metadata = dict(remote.metadata or {})
        remote_user_id = None
        try:
            if metadata.get('fba_user_id'):
                remote_user_id = int(metadata['fba_user_id'])
        except (TypeError, ValueError):
            remote_user_id = None
        owner_id, owner_username = await self._resolve_owner(
            db,
            user_id=remote_user_id or fallback_user_id,
            username=metadata.get('fba_username') or fallback_username,
            fallback_user_id=fallback_user_id or 0,
            fallback_username=fallback_username or '未关联用户',
        )
        state = remote.status.state if remote.status else 'Unknown'
        image = getattr(remote.image, 'image', None) or metadata.get('fba_image') or ''
        name = metadata.get('fba_name') or (remote.id[:8] if remote.id else 'sandbox')
        record = await sandbox_dao.get_by_sandbox_id(db, remote.id, include_deleted=True)
        if record:
            if record.deleted:
                await sandbox_dao.revive(db, remote.id)
            await sandbox_dao.update_by_sandbox_id(
                db,
                remote.id,
                {
                    'status': state,
                    'name': name,
                    'image': image,
                    'user_id': owner_id,
                    'username': owner_username,
                    'expires_at': remote.expires_at,
                },
            )
            return await sandbox_dao.get_by_sandbox_id(db, remote.id)  # type: ignore[return-value]

        return await sandbox_dao.create_record(
            db,
            SandboxRecordCreate(
                sandbox_id=remote.id,
                name=name,
                image=image,
                user_id=owner_id,
                username=owner_username,
                status=state,
                last_activity_time=timezone.now(),
                expires_at=remote.expires_at,
            ),
        )

    @staticmethod
    async def _guard_remote_expiration(remote: Any) -> Any:
        """兼容旧沙盒的有限 TTL，避免 OpenSandbox 到期直接删除容器"""

        if not settings.OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED or remote.expires_at is None:
            return remote
        deadline = timezone.now() + timedelta(seconds=settings.OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_SECONDS)
        if remote.expires_at > deadline:
            return remote
        await open_sandbox_client.renew_sandbox(remote.id, settings.OPEN_SANDBOX_LEGACY_EXPIRY_EXTEND_MINUTES)
        log.warning(f'OpenSandbox 旧沙盒使用有限 TTL，已自动续期以避免删除：{remote.id}')
        return await open_sandbox_client.get_info(remote.id)

    async def sync_remote(
        self,
        db: AsyncSession,
        *,
        user_id: int | None = None,
        states: list[str] | None = None,
        max_pages: int = 30,
    ) -> int:
        """将 OpenSandbox 中的沙盒同步到本地记录"""

        await load_sandbox_config(db)
        await ensure_sandbox_api_enabled(db)
        if not open_sandbox_client.enabled:
            return 0
        server_available, _, health_message = await open_sandbox_client.health()
        if not server_available:
            log.warning(f'OpenSandbox 不可达，跳过远端同步：{health_message}')
            return 0
        metadata = {'fba_managed': 'true'}
        if user_id is not None:
            metadata['fba_user_id'] = str(user_id)
        count = 0
        try:
            for page in range(1, max_pages + 1):
                data = await open_sandbox_client.list_sandboxes(
                    page=page,
                    page_size=200,
                    states=states,
                    metadata=metadata,
                )
                for remote in data.sandbox_infos:
                    await self._upsert_remote(
                        db,
                        remote,
                        fallback_user_id=user_id,
                        fallback_username=None,
                    )
                    count += 1
                if not data.pagination.has_next_page:
                    break
        except OpenSandboxError as exc:
            log.warning(f'OpenSandbox 沙盒同步失败：{exc}')
            return 0
        else:
            await db.flush()
            return count

    async def list_user(self, *, db: AsyncSession, user_id: int, username: str) -> list[SandboxInfo]:
        """获取用户沙盒"""

        await load_sandbox_config(db)
        if await is_sandbox_api_enabled(db):
            await self.sync_remote(db, user_id=user_id)
        records = await sandbox_dao.get_active_by_user(db, user_id)
        if not records:
            stmt = select(SandboxRecord).where(SandboxRecord.deleted == 0, SandboxRecord.user_id == user_id)
            records = list((await db.execute(stmt)).scalars().all())
        return [self._record_to_info(record) for record in records]

    async def list_admin(
        self,
        *,
        db: AsyncSession,
        user_id: int | None,
        username: str | None,
        status: str | None,
        keyword: str | None,
    ) -> dict[str, Any]:
        """管理员分页获取全部沙盒"""

        await load_sandbox_config(db)
        if await is_sandbox_api_enabled(db):
            await self.sync_remote(db)
        page_data = await paging_data(
            db,
            await sandbox_dao.get_select(user_id=user_id, username=username, status=status, keyword=keyword),
        )
        page_data['items'] = [self._record_to_info(record).model_dump() for record in page_data.get('items', [])]
        return page_data

    async def _owner_for_create(
        self,
        *,
        db: AsyncSession,
        current_user_id: int,
        current_username: str,
        is_admin: bool,
        obj: CreateSandboxParam,
    ) -> tuple[int, str]:
        if obj.owner_id or obj.owner_username:
            if not is_admin:
                raise errors.ForbiddenError(msg='只有管理员可以为其他用户创建沙盒')
            owner = None
            if obj.owner_id:
                owner = await user_dao.get(db, obj.owner_id)
            elif obj.owner_username:
                owner = await user_dao.get_by_username(db, obj.owner_username)
            if not owner:
                raise errors.NotFoundError(msg='目标用户不存在')
            return owner.id, owner.username
        return current_user_id, current_username

    async def create(
        self,
        *,
        db: AsyncSession,
        current_user_id: int,
        current_username: str,
        is_admin: bool,
        obj: CreateSandboxParam,
    ) -> SandboxInfo:
        """创建沙盒"""

        await load_sandbox_config(db)
        await ensure_sandbox_api_enabled(db)
        status = await self.service_status(db=db)
        if not status.configured:
            raise errors.RequestError(msg='未配置 OPEN_SANDBOX_ENABLED/OPEN_SANDBOX_URL')
        if not status.available:
            raise errors.GatewayError(msg=f'OpenSandbox 服务不可用：{status.message}')
        owner_id, owner_username = await self._owner_for_create(
            db=db,
            current_user_id=current_user_id,
            current_username=current_username,
            is_admin=is_admin,
            obj=obj,
        )
        active = await sandbox_dao.get_active_by_user(db, owner_id)
        if len(active) >= settings.OPEN_SANDBOX_MAX_SANDBOXES_PER_USER:
            raise errors.ConflictError(msg=f'每个用户最多保留 {settings.OPEN_SANDBOX_MAX_SANDBOXES_PER_USER} 个沙盒')
        name = obj.name.strip() or f'{owner_username}-sandbox'
        try:
            sandbox_id = await open_sandbox_client.create_sandbox(
                image=obj.image or settings.OPEN_SANDBOX_IMAGE,
                name=name,
                user_id=owner_id,
                username=owner_username,
                resource={'cpu': settings.OPEN_SANDBOX_RESOURCE_CPU, 'memory': settings.OPEN_SANDBOX_RESOURCE_MEMORY},
            )
            remote = await open_sandbox_client.get_info(sandbox_id)
            remote = await self._guard_remote_expiration(remote)
            record = await self._upsert_remote(
                db,
                remote,
                fallback_user_id=owner_id,
                fallback_username=owner_username,
            )
            await db.flush()
            return self._record_to_info(record)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'创建沙盒失败：{exc}') from exc

    async def ensure_access(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        user_id: int,
        is_admin: bool,
        username: str | None = None,
    ) -> SandboxRecord:
        """校验沙盒访问权限"""

        await load_sandbox_config(db)
        await ensure_sandbox_api_enabled(db)
        record = await sandbox_dao.get_by_sandbox_id(db, sandbox_id)
        if not record:
            await self.sync_remote(db)
            record = await sandbox_dao.get_by_sandbox_id(db, sandbox_id)
        if not record:
            try:
                remote = await open_sandbox_client.get_info(sandbox_id)
                record = await self._upsert_remote(
                    db,
                    remote,
                    fallback_user_id=user_id if not is_admin else None,
                    fallback_username=username,
                )
                await db.flush()
            except OpenSandboxError as exc:
                raise errors.NotFoundError(msg=f'沙盒不存在或不可访问：{exc}') from exc
        if not is_admin and record.user_id != user_id:
            raise errors.ForbiddenError(msg='无权访问该沙盒')
        return record

    async def get_info(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        user_id: int,
        is_admin: bool,
        username: str | None = None,
    ) -> SandboxInfo:
        """获取并刷新沙盒状态"""

        record = await self.ensure_access(
            db=db, sandbox_id=sandbox_id, user_id=user_id, is_admin=is_admin, username=username
        )
        try:
            remote = await open_sandbox_client.get_info(sandbox_id)
            await sandbox_dao.update_by_sandbox_id(db, sandbox_id, {'status': remote.status.state})
            record.status = remote.status.state
        except OpenSandboxError:
            pass
        return self._record_to_info(record)

    async def _wait_state(self, sandbox_id: str, expected: str, timeout_seconds: int | None = None) -> None:
        timeout_seconds = timeout_seconds or settings.OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            info = await open_sandbox_client.get_info(sandbox_id)
            if info.status.state == expected:
                return
            if info.status.state in {'Failed', 'Terminated'}:
                raise errors.GatewayError(msg=info.status.message or f'沙盒状态异常：{info.status.state}')
            await asyncio.sleep(0.5)
        raise errors.GatewayError(msg=f'等待沙盒进入 {expected} 状态超时')

    async def action(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        action: str,
        user_id: int,
        is_admin: bool,
        username: str | None = None,
    ) -> SandboxInfo:
        """暂停、恢复、重启或删除沙盒"""

        record = await self.ensure_access(
            db=db, sandbox_id=sandbox_id, user_id=user_id, is_admin=is_admin, username=username
        )
        try:
            if action == 'pause':
                await open_sandbox_client.pause_sandbox(sandbox_id)
                await self._wait_state(sandbox_id, 'Paused')
                await sandbox_dao.update_by_sandbox_id(
                    db, sandbox_id, {'status': 'Paused', 'paused_time': timezone.now()}
                )
                record.status = 'Paused'
            elif action == 'resume':
                await open_sandbox_client.resume_sandbox(sandbox_id)
                await self._wait_state(sandbox_id, 'Running')
                await sandbox_dao.update_by_sandbox_id(
                    db, sandbox_id, {'status': 'Running', 'paused_time': None, 'last_activity_time': timezone.now()}
                )
                record.status = 'Running'
            elif action == 'restart':
                await open_sandbox_client.pause_sandbox(sandbox_id)
                await self._wait_state(sandbox_id, 'Paused')
                await open_sandbox_client.resume_sandbox(sandbox_id)
                await self._wait_state(sandbox_id, 'Running')
                await sandbox_dao.update_by_sandbox_id(
                    db, sandbox_id, {'status': 'Running', 'paused_time': None, 'last_activity_time': timezone.now()}
                )
                record.status = 'Running'
            elif action == 'delete':
                await open_sandbox_client.kill_sandbox(sandbox_id)
                await sandbox_dao.soft_delete(db, sandbox_id)
                record.status = 'Terminated'
            else:
                raise errors.RequestError(msg='不支持的操作')
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'沙盒操作失败：{exc}') from exc
        return self._record_to_info(record)

    async def rename(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        name: str,
        user_id: int,
        is_admin: bool,
        username: str | None = None,
    ) -> SandboxInfo:
        """修改沙盒显示名称，并同步 OpenSandbox 元数据"""

        record = await self.ensure_access(
            db=db, sandbox_id=sandbox_id, user_id=user_id, is_admin=is_admin, username=username
        )
        normalized_name = name.strip()
        if not normalized_name:
            raise errors.RequestError(msg='沙盒名称不能为空')
        try:
            await open_sandbox_client.patch_metadata(sandbox_id, {'fba_name': normalized_name})
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'重命名沙盒失败：{exc}') from exc
        await sandbox_dao.update_by_sandbox_id(db, sandbox_id, {'name': normalized_name})
        record.name = normalized_name
        return self._record_to_info(record)

    async def renew(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        minutes: int,
        user_id: int,
        is_admin: bool,
        username: str | None = None,
    ) -> SandboxInfo:
        """续期沙盒"""

        record = await self.ensure_access(
            db=db, sandbox_id=sandbox_id, user_id=user_id, is_admin=is_admin, username=username
        )
        try:
            await open_sandbox_client.renew_sandbox(sandbox_id, minutes)
            remote = await open_sandbox_client.get_info(sandbox_id)
            await sandbox_dao.update_by_sandbox_id(db, sandbox_id, {'expires_at': remote.expires_at})
            record.expires_at = remote.expires_at
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'沙盒续期失败：{exc}') from exc
        return self._record_to_info(record)

    async def touch(self, db: AsyncSession, *, sandbox_id: str, status: str | None = None) -> None:
        """刷新沙盒活动时间"""

        data: dict[str, Any] = {'last_activity_time': timezone.now()}
        if status:
            data['status'] = status
        try:
            await sandbox_dao.update_by_sandbox_id(db, sandbox_id, data)
        except Exception:
            log.exception(f'更新 OpenSandbox 活动时间失败：{sandbox_id}')

    async def protect_legacy_expirations(self) -> None:
        """在旧沙盒到期前续期，避免服务端按 TTL 删除而不是暂停"""

        if not settings.OPEN_SANDBOX_ENABLED:
            return
        deadline = timezone.now() + timedelta(seconds=settings.OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_SECONDS)
        async with async_db_session() as db:
            await load_sandbox_config(db)
            if not await is_sandbox_api_enabled(db):
                return
            await self.sync_remote(db)
            if not settings.OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED:
                return
            records = await sandbox_dao.get_all_active(db)
            targets = [
                (record.sandbox_id, record.name)
                for record in records
                if record.expires_at is not None and record.expires_at <= deadline
            ]
        for sandbox_id, sandbox_name in targets:
            try:
                remote = await open_sandbox_client.get_info(sandbox_id)
                remote = await self._guard_remote_expiration(remote)
                async with async_db_session.begin() as db:
                    await sandbox_dao.update_by_sandbox_id(
                        db,
                        sandbox_id,
                        {'expires_at': remote.expires_at},
                    )
                log.info(f'OpenSandbox 旧沙盒已纳入不删除策略：{sandbox_name} ({sandbox_id})')
            except OpenSandboxError as exc:
                log.warning(f'OpenSandbox 旧沙盒续期失败：{sandbox_id} {exc}')

    async def list_users(self, *, db: AsyncSession) -> list[UserOption]:
        """管理员用户选项"""

        stmt = (
            select(User.id, User.username, User.nickname).where(User.deleted == 0, User.status == 1).order_by(User.id)
        )
        result = await db.execute(stmt)
        return [UserOption(id=row.id, username=row.username, nickname=row.nickname) for row in result.all()]

    async def auto_pause_idle(self) -> None:
        """空闲自动暂停，保留沙盒状态而不是删除"""

        async with async_db_session() as db:
            await load_sandbox_config(db)
            if not await is_sandbox_api_enabled(db):
                return
            if not (settings.OPEN_SANDBOX_ENABLED and settings.OPEN_SANDBOX_AUTO_PAUSE_ENABLED):
                return
            cutoff = timezone.now() - timedelta(seconds=settings.OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS)
            records = await sandbox_dao.get_idle(db, cutoff)
            targets = [(record.sandbox_id, record.name) for record in records]

        for sandbox_id, sandbox_name in targets[:20]:
            if sandbox_id in self.active_sandboxes:
                continue
            try:
                info = await open_sandbox_client.get_info(sandbox_id)
                if info.status.state == 'Paused':
                    status = 'Paused'
                elif info.status.state == 'Running':
                    await open_sandbox_client.pause_sandbox(sandbox_id)
                    await self._wait_state(sandbox_id, 'Paused')
                    status = 'Paused'
                    log.info(f'OpenSandbox 空闲暂停：{sandbox_name} ({sandbox_id})')
                elif info.status.state in {'Terminated', 'Failed'}:
                    status = info.status.state
                else:
                    continue
                async with async_db_session.begin() as db:
                    await sandbox_dao.update_by_sandbox_id(
                        db,
                        sandbox_id,
                        {'status': status, 'paused_time': timezone.now() if status == 'Paused' else None},
                    )
            except Exception as exc:
                log.warning(f'OpenSandbox 自动暂停失败：{sandbox_id} {exc}')


sandbox_service: SandboxService = SandboxService()
