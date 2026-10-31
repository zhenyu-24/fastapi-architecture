from collections.abc import Sequence

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.model.user import User
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.core.storage import UPLOAD_DIR
from backend.plugin.files.crud.crud_file import file_dao
from backend.plugin.files.enums import UploadType
from backend.plugin.files.model.file import FileRecord
from backend.plugin.files.model.reference import FileReference
from backend.plugin.files.schema.file import FileBrowseDetail, FileFolder, ManagedFileDetail
from backend.plugin.files.service.cleanup_service import cleanup_service
from backend.plugin.files.service.file_service import file_service
from backend.plugin.files.service.reference_service import reference_service
from backend.plugin.files.service.validation import validate_content


class FileManageService:
    """管理员文件资源管理"""

    async def resource_folders(self, *, db: AsyncSession, is_public: bool) -> list[str]:
        statement = await file_dao.get_manage_select(
            name=None, upload_type='resource', is_public=is_public, user_id=None
        )
        urls = (await db.scalars(statement.with_only_columns(FileRecord.url_path))).all()
        folders: set[str] = set()
        for url in urls:
            try:
                relative = file_service.resolve_record_path(url).relative_to(UPLOAD_DIR.resolve()).as_posix()
            except (errors.RequestError, OSError, ValueError):
                continue
            relative = relative.removeprefix('public/')
            parts = relative.split('/')
            # Resource storage adds a YYYY/MM/DD suffix after the chosen directory.
            custom = parts[1:-4]
            folders.update('/'.join(custom[:index]) for index in range(1, len(custom) + 1))
        return sorted(folders)

    @staticmethod
    def sort_columns() -> dict:
        return {
            'username': select(User.username).where(User.id == FileRecord.user_id).scalar_subquery(),
            'is_public': file_dao.public_condition(),
        }

    @staticmethod
    async def require_storage() -> None:
        if not await to_thread.run_sync(UPLOAD_DIR.is_dir):
            raise errors.RequestError(msg='文件存储目录不可用，已取消操作')

    @staticmethod
    def is_public(record: FileRecord) -> bool:
        return (
            record.url_path.startswith('/static/upload/') and not record.url_path.startswith('/static/upload/private/')
        ) or record.url_path.startswith('/storage/public/files/')

    async def detail(
        self, *, db: AsyncSession, record: FileRecord, usernames: dict[int, str] | None = None
    ) -> ManagedFileDetail:
        exists = False
        owner_uses_avatar = False
        storage_path = ''
        try:
            path = await to_thread.run_sync(file_service.resolve_record_path, record.url_path)
            storage_path = path.relative_to(UPLOAD_DIR.resolve()).as_posix()
            exists = await to_thread.run_sync(path.is_file)
            if record.upload_type == 'avatar':
                owner_uses_avatar = await cleanup_service.owner_uses_avatar(db=db, record=record, path=path)
        except (errors.RequestError, OSError):
            pass
        return ManagedFileDetail(
            **file_service.record_detail(record, is_public=self.is_public(record)).model_dump(),
            name=record.name,
            url_path=record.url_path,
            mime_type=record.mime_type,
            user_id=str(record.user_id) if record.user_id is not None else None,
            exists=exists,
            owner_uses_avatar=owner_uses_avatar,
            username=usernames.get(record.user_id)
            if usernames is not None
            else (
                await db.scalar(select(User.username).where(User.id == record.user_id))
                if record.user_id is not None
                else None
            ),
            storage_path=storage_path,
            retention_policy=record.retention_policy,
            unreferenced_at=record.unreferenced_at,
            references=[
                {'business_type': ref.business_type, 'business_id': str(ref.business_id), 'field': ref.field}
                for ref in (await db.scalars(select(FileReference).where(FileReference.file_id == record.id))).all()
            ],
        )

    async def details(self, *, db: AsyncSession, records: Sequence[FileRecord]) -> list[ManagedFileDetail]:
        user_ids = {record.user_id for record in records if record.user_id is not None}
        usernames = dict((await db.execute(select(User.id, User.username).where(User.id.in_(user_ids)))).all())
        return [await self.detail(db=db, record=record, usernames=usernames) for record in records]

    async def get(self, *, db: AsyncSession, file_id: int) -> ManagedFileDetail:
        record = await file_dao.get_managed(db, file_id=file_id)
        if record is None:
            raise errors.NotFoundError(msg='文件不存在')
        return await self.detail(db=db, record=record)

    async def get_list(
        self,
        *,
        db: AsyncSession,
        name: str | None,
        upload_type: str | None,
        is_public: bool | None,
        user_id: int | None,
        username: str | None = None,
    ) -> dict:
        statement = await file_dao.get_manage_select(
            name=name, upload_type=upload_type, is_public=is_public, user_id=user_id, username=username
        )

        async def transform(records: Sequence[FileRecord]) -> list[ManagedFileDetail]:
            return await self.details(db=db, records=records)

        return await paging_data(db, statement, transformer=transform, sort_columns=self.sort_columns())

    async def browse(
        self,
        *,
        db: AsyncSession,
        path: str,
        name: str | None,
        upload_type: str | None,
        is_public: bool | None,
        username: str | None,
        recursive: bool = False,
    ) -> FileBrowseDetail:
        if path:
            file_service._validate_relative_path(path)
        statement = await file_dao.get_manage_select(
            name=name, upload_type=upload_type, is_public=is_public, user_id=None, username=username
        )
        # Only project metadata here; file details and disk checks stay limited to the selected page.
        entries = (await db.execute(statement.with_only_columns(FileRecord.id, FileRecord.url_path))).all()
        folders: dict[str, int] = {}
        direct_ids: list[int] = []
        root = UPLOAD_DIR.resolve()
        prefix = f'{path}/' if path else ''
        for file_id, url_path in entries:
            try:
                relative = file_service.resolve_record_path(url_path).relative_to(root).as_posix()
            except (errors.RequestError, OSError, ValueError):
                continue
            if not relative.startswith(prefix):
                continue
            remaining = relative[len(prefix) :]
            if recursive:
                direct_ids.append(file_id)
            elif '/' in remaining:
                folder = remaining.split('/', 1)[0]
                folders[folder] = folders.get(folder, 0) + 1
            else:
                direct_ids.append(file_id)

        async def transform(records: Sequence[FileRecord]) -> list[ManagedFileDetail]:
            return await self.details(db=db, records=records)

        files = await paging_data(
            db, statement.where(FileRecord.id.in_(direct_ids)), transformer=transform, sort_columns=self.sort_columns()
        )
        return FileBrowseDetail(
            path=path,
            files=files,
            folders=[
                FileFolder(name=key, path=f'{prefix}{key}', count=count) for key, count in sorted(folders.items())
            ],
        )

    async def set_visibility(self, *, db: AsyncSession, file_id: int, is_public: bool) -> ManagedFileDetail:
        await self.require_storage()
        record = await file_dao.get_managed(db, file_id=file_id, lock=True)
        if record is None:
            raise errors.NotFoundError(msg='文件不存在')
        if self.is_public(record) == is_public:
            return await self.detail(db=db, record=record)
        if record.upload_type != 'avatar':
            await reference_service.require_unused(db=db, file_id=record.id)
        source = file_service.resolve_record_path(record.url_path)
        if not await to_thread.run_sync(source.is_file):
            raise errors.NotFoundError(msg='磁盘文件不存在')
        root = UPLOAD_DIR.resolve()
        relative = source.relative_to(root).as_posix().removeprefix('public/')
        destination = file_service._resolve_storage_path(
            root / 'public' if is_public and record.upload_type != 'avatar' else root, relative
        )
        prefix = (
            '/static/upload'
            if is_public and record.upload_type == 'avatar'
            else ('/static/upload/public' if is_public else '/storage/files')
        )
        new_url = f'{prefix}/{relative}'
        duplicate = await db.scalar(
            select(FileRecord.id)
            .where(FileRecord.id != record.id, FileRecord.url_path.in_([record.url_path, new_url]))
            .limit(1)
        )
        if duplicate is not None or (source != destination and await to_thread.run_sync(destination.exists)):
            raise errors.ConflictError(msg='目标存储路径已存在，请先核查')
        uses_avatar = record.upload_type == 'avatar' and await cleanup_service.owner_uses_avatar(
            db=db, record=record, path=source
        )
        try:
            if source != destination:
                await to_thread.run_sync(lambda: destination.parent.mkdir(parents=True, exist_ok=True))
                await to_thread.run_sync(lambda: source.replace(destination))
        except OSError as exc:
            raise errors.RequestError(msg='修改可见性失败，文件记录已保留') from exc
        record.url_path = new_url
        if uses_avatar:
            from backend.app.admin.crud.crud_user import user_dao
            from backend.core.conf import settings
            from backend.database.redis import redis_client

            avatar = new_url if is_public else f'{settings.FASTAPI_API_V1_PATH}/files/download/{record.id}'
            await user_dao.update_avatar(db, record.user_id, avatar)
            await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{record.user_id}')
        await db.flush()
        return await self.detail(db=db, record=record)

    async def delete_batch(self, *, db: AsyncSession, ids: list[int]) -> dict:
        deleted: list[str] = []
        failed: list[dict[str, str]] = []
        for file_id in sorted(set(ids)):
            try:
                await self.delete(db=db, file_id=file_id)
                deleted.append(str(file_id))
            except errors.BaseExceptionError as exc:
                failed.append({'file_id': str(file_id), 'message': exc.msg})
        return {'deleted': deleted, 'failed': failed}

    async def replace(self, *, db: AsyncSession, file_id: int, source_file_id: int, user_id: int) -> ManagedFileDetail:
        await self.require_storage()
        if file_id == source_file_id:
            raise errors.RequestError(msg='不能用同一文件替换自身')
        records = (
            await db.scalars(
                select(FileRecord)
                .where(FileRecord.id.in_([file_id, source_file_id]), FileRecord.deleted == 0)
                .order_by(FileRecord.id)
                .with_for_update()
            )
        ).all()
        indexed = {record.id: record for record in records}
        target, source = indexed.get(file_id), indexed.get(source_file_id)
        if target is None or source is None:
            raise errors.NotFoundError(msg='原文件或替换文件不存在')
        if source.user_id != user_id:
            raise errors.AuthorizationError(msg='只能使用当前管理员上传的文件进行替换')
        if target.extension != source.extension:
            raise errors.RequestError(msg='替换文件必须与原文件扩展名相同')
        file_service.validate_metadata(
            source.original_name, UploadType(target.upload_type), source.size, source.mime_type
        )
        destination = file_service.resolve_record_path(target.url_path)
        incoming = file_service.resolve_record_path(source.url_path)
        if incoming == destination:
            raise errors.ConflictError(msg='替换文件与原文件使用同一存储路径')
        if source.upload_type == 'avatar':
            raise errors.RequestError(msg='不能将头像记录作为替换来源')
        await reference_service.require_unused(db=db, file_id=source.id)
        duplicate = await db.scalar(
            select(FileRecord.id)
            .where(
                FileRecord.url_path.in_([target.url_path, source.url_path]),
                FileRecord.id.not_in([file_id, source_file_id]),
            )
            .limit(1)
        )
        if duplicate is not None:
            raise errors.ConflictError(msg='存储路径存在重复记录，不能替换')
        if not await to_thread.run_sync(incoming.is_file):
            raise errors.NotFoundError(msg='替换文件不存在')
        file_service.validate_metadata(
            source.original_name,
            UploadType(target.upload_type),
            (await to_thread.run_sync(incoming.stat)).st_size,
            source.mime_type,
        )
        mime = await to_thread.run_sync(validate_content, incoming, target.extension, source.mime_type)
        try:
            await to_thread.run_sync(lambda: destination.parent.mkdir(parents=True, exist_ok=True))
            await to_thread.run_sync(lambda: incoming.replace(destination))
        except OSError as exc:
            raise errors.RequestError(msg='替换失败，文件记录已保留') from exc
        target.size = (await to_thread.run_sync(destination.stat)).st_size
        target.mime_type = mime
        await db.delete(source)
        await db.flush()
        return await self.detail(db=db, record=target)

    async def delete(self, *, db: AsyncSession, file_id: int) -> None:
        await self.require_storage()
        record = await file_dao.get_managed(db, file_id=file_id, lock=True)
        if record is None:
            raise errors.NotFoundError(msg='文件不存在')
        path = await to_thread.run_sync(file_service.resolve_record_path, record.url_path)
        if record.upload_type == 'avatar' and await cleanup_service.owner_uses_avatar(db=db, record=record, path=path):
            raise errors.ConflictError(msg='该文件是用户正在使用的头像，请先更换头像')
        await reference_service.require_unused(db=db, file_id=record.id)
        duplicate = await db.scalar(
            select(FileRecord.id).where(FileRecord.url_path == record.url_path, FileRecord.id != record.id).limit(1)
        )
        if duplicate is not None:
            raise errors.ConflictError(msg='该存储路径存在其他文件记录，请先核查')
        try:
            await to_thread.run_sync(lambda: path.unlink(missing_ok=True))
        except OSError as exc:
            raise errors.RequestError(msg='磁盘文件删除失败，文件记录已保留，请稍后重试') from exc
        await db.delete(record)
        await db.flush()


file_manage_service = FileManageService()
