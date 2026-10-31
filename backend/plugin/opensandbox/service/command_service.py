import posixpath
import time

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.log import log
from backend.common.pagination import paging_data
from backend.core.conf import settings
from backend.plugin.opensandbox.crud import command_log_dao
from backend.plugin.opensandbox.model import CommandLog
from backend.plugin.opensandbox.schema.sandbox import (
    CommandLogCreate,
    CommandLogDetail,
    CommandResult,
    CreateSessionParam,
    RunCommandParam,
    TerminalSessionResult,
)
from backend.plugin.opensandbox.service.sandbox_service import sandbox_service
from backend.plugin.opensandbox.utils.client import OpenSandboxError, open_sandbox_client
from backend.plugin.opensandbox.utils.dynamic_config import load_sandbox_config
from backend.utils.timezone import timezone


def normalize_workspace_path(path: str | None, *, allow_root: bool = True) -> str:
    """限制文件操作位于工作区根目录内"""

    root = posixpath.normpath(settings.OPEN_SANDBOX_WORKSPACE_ROOT or '/workspace')
    raw = (path or root).strip().replace('\\', '/')
    if not raw.startswith('/'):
        raw = posixpath.join(root, raw)
    normalized = posixpath.normpath(raw)
    if normalized == root and allow_root:
        return normalized
    if not normalized.startswith(f'{root}/'):
        raise errors.ForbiddenError(msg=f'路径必须位于工作区 {root} 内')
    return normalized


def _join_output(messages: Sequence[Any] | None) -> str:
    if not messages:
        return ''
    result = ''
    for message in messages:
        text = str(getattr(message, 'text', ''))
        if result and not result.endswith(('\n', '\r')):
            result += '\n'
        result += text
    return result


def _truncate_output(stdout: str, stderr: str) -> tuple[str, str, bool]:
    limit = max(1024, settings.OPEN_SANDBOX_MAX_OUTPUT_CHARS)
    total = len(stdout) + len(stderr)
    if total <= limit:
        return stdout, stderr, False
    stdout = stdout[:limit]
    remaining = max(0, limit - len(stdout))
    stderr = stderr[:remaining]
    return stdout, stderr, True


class CommandService:
    """命令执行与审计服务"""

    async def execute(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        obj: RunCommandParam,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> CommandResult:
        """执行命令并写入审计日志"""

        await load_sandbox_config(db)
        record = await sandbox_service.ensure_access(
            db=db,
            sandbox_id=sandbox_id,
            user_id=user_id,
            is_admin=is_admin,
            username=username,
        )
        cwd = obj.cwd or settings.OPEN_SANDBOX_WORKSPACE_ROOT
        if not obj.session_id:
            cwd = normalize_workspace_path(cwd)
        started = time.perf_counter()
        if obj.source == 'terminal' and obj.command.strip() == 'clear':
            duration_ms = int((time.perf_counter() - started) * 1000)
            created_time = timezone.now()
            log_record = await self._write_log(
                db,
                sandbox_id=sandbox_id,
                sandbox_name=record.name,
                user_id=user_id,
                username=username,
                obj=obj,
                cwd=cwd,
                stdout='',
                stderr='',
                exit_code=0,
                status='success',
                duration_ms=duration_ms,
                truncated=False,
            )
            await sandbox_service.touch(db, sandbox_id=sandbox_id, status='Running')
            return CommandResult(
                log_id=log_record.id if log_record else None,
                command=obj.command,
                stdout='',
                stderr='',
                exit_code=0,
                status='success',
                duration_ms=duration_ms,
                truncated=False,
                created_time=created_time,
            )
        sandbox_service.mark_active(sandbox_id)
        try:
            execution = await open_sandbox_client.run_command(
                sandbox_id,
                obj.command,
                cwd=cwd,
                timeout_seconds=obj.timeout_seconds,
                session_id=obj.session_id,
            )
        except OpenSandboxError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            created_time = timezone.now()
            log_record = await self._write_log(
                db,
                sandbox_id=sandbox_id,
                sandbox_name=record.name,
                user_id=user_id,
                username=username,
                obj=obj,
                cwd=cwd,
                stdout='',
                stderr=str(exc),
                exit_code=-1,
                status='error',
                duration_ms=duration_ms,
                truncated=False,
            )
            await sandbox_service.touch(db, sandbox_id=sandbox_id)
            return CommandResult(
                log_id=log_record.id if log_record else None,
                command=obj.command,
                cwd=None,
                stdout='',
                stderr=str(exc),
                exit_code=-1,
                status='error',
                duration_ms=duration_ms,
                truncated=False,
                created_time=created_time,
            )
        finally:
            sandbox_service.unmark_active(sandbox_id)

        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = _join_output(execution.logs.stdout)
        stderr = _join_output(execution.logs.stderr)
        stdout, stderr, truncated = _truncate_output(stdout, stderr)
        exit_code = execution.exit_code
        if exit_code is None:
            exit_code = 0 if execution.error is None else -1
        result_cwd = None
        if obj.session_id and exit_code == 0 and obj.command.strip().split(maxsplit=1)[:1] == ['cd']:
            try:
                pwd_execution = await open_sandbox_client.run_command(
                    sandbox_id,
                    'pwd',
                    cwd=None,
                    timeout_seconds=min(obj.timeout_seconds, 10),
                    session_id=obj.session_id,
                )
                result_cwd = _join_output(pwd_execution.logs.stdout).strip() or None
            except OpenSandboxError:
                result_cwd = None
        status = 'success' if exit_code == 0 else 'failed'
        created_time = timezone.now()
        log_record = await self._write_log(
            db,
            sandbox_id=sandbox_id,
            sandbox_name=record.name,
            user_id=user_id,
            username=username,
            obj=obj,
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            status=status,
            duration_ms=duration_ms,
            truncated=truncated,
        )
        await sandbox_service.touch(db, sandbox_id=sandbox_id, status='Running')
        return CommandResult(
            log_id=log_record.id if log_record else None,
            command=obj.command,
            cwd=result_cwd,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            status=status,
            duration_ms=duration_ms,
            truncated=truncated,
            created_time=created_time,
        )

    async def _write_log(
        self,
        db: AsyncSession,
        *,
        sandbox_id: str,
        sandbox_name: str,
        user_id: int,
        username: str,
        obj: RunCommandParam,
        cwd: str,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        status: str,
        duration_ms: int,
        truncated: bool,
    ) -> CommandLog | None:
        try:
            record = await command_log_dao.create(
                db,
                CommandLogCreate(
                    sandbox_id=sandbox_id,
                    sandbox_name=sandbox_name,
                    user_id=user_id,
                    username=username,
                    source=obj.source,
                    session_id=obj.session_id,
                    command=obj.command,
                    cwd=cwd,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    status=status,
                    duration_ms=duration_ms,
                    truncated=truncated,
                ),
            )
        except Exception:
            log.exception('写入 OpenSandbox 命令审计日志失败')
            return None
        else:
            await db.flush()
            return record

    async def create_session(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        obj: CreateSessionParam,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> TerminalSessionResult:
        """创建 Bash 会话"""

        await sandbox_service.ensure_access(
            db=db, sandbox_id=sandbox_id, user_id=user_id, is_admin=is_admin, username=username
        )
        cwd = normalize_workspace_path(obj.cwd) if obj.cwd else settings.OPEN_SANDBOX_WORKSPACE_ROOT
        try:
            session_id = await open_sandbox_client.create_session(sandbox_id, cwd)
            await sandbox_service.touch(db, sandbox_id=sandbox_id, status='Running')
            return TerminalSessionResult(session_id=session_id, cwd=cwd)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'创建终端会话失败：{exc}') from exc

    async def delete_session(self, *, sandbox_id: str, session_id: str) -> None:
        """删除 Bash 会话"""

        try:
            await open_sandbox_client.delete_session(sandbox_id, session_id)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'关闭终端会话失败：{exc}') from exc

    async def list_logs(
        self,
        *,
        db: AsyncSession,
        user_id: int | None,
        username: str | None,
        sandbox_id: str | None,
        keyword: str | None,
        status: str | None,
        start_time: Any,
        end_time: Any,
    ) -> dict[str, Any]:
        """管理员分页查询命令审计"""

        page_data = await paging_data(
            db,
            await command_log_dao.get_select(
                user_id=user_id,
                username=username,
                sandbox_id=sandbox_id,
                keyword=keyword,
                status=status,
                start_time=start_time,
                end_time=end_time,
            ),
        )
        page_data['items'] = [CommandLogDetail.model_validate(item).model_dump() for item in page_data.get('items', [])]
        return page_data

    async def get_log(self, *, db: AsyncSession, pk: int) -> CommandLogDetail:
        """获取审计详情"""

        record = await command_log_dao.get(db, pk)
        if not record:
            raise errors.NotFoundError(msg='命令日志不存在')
        return CommandLogDetail.model_validate(record)


command_service: CommandService = CommandService()
