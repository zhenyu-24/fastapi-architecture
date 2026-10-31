import re

from pathlib import Path
from typing import Literal
from uuid import uuid4

from anyio import open_file, to_thread
from fastapi import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.core.storage import UPLOAD_DIR
from backend.plugin.files.crud.crud_file import file_dao
from backend.plugin.files.enums import UPLOAD_TYPE_EXTENSIONS, UPLOAD_TYPE_SIZE_LIMITS, UploadType
from backend.plugin.files.model.file import FileRecord
from backend.plugin.files.schema.file import UploadFileDetail
from backend.plugin.files.service.validation import validate_content
from backend.utils.timezone import timezone


class FileService:
    """文件上传下载服务"""

    @staticmethod
    def _validate_relative_path(value: str) -> str:
        """同时拒绝 POSIX 和 Windows 路径穿越及歧义路径"""
        parts = value.split('/')
        reserved = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'}
        reserved.update(f'{prefix}{index}' for prefix in ('COM', 'LPT') for index in range(1, 10))
        if (
            len(value) > 240
            or any(char in value for char in '\\:%<>|"?#*')
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or any(
                not part
                or part in {'.', '..'}
                or part != part.strip()
                or part.endswith('.')
                or part.split('.')[0].upper() in reserved
                for part in parts
            )
        ):
            raise errors.RequestError(msg='文件路径必须是安全的相对路径')
        return value

    @classmethod
    def _resolve_storage_path(cls, root: Path, relative_path: str) -> Path:
        """解析符号链接后检查文件仍在指定存储根目录内"""
        cls._validate_relative_path(relative_path)
        try:
            resolved_root = root.resolve()
            path = (resolved_root / relative_path).resolve()
        except (OSError, RuntimeError, ValueError):
            raise errors.RequestError(msg='文件路径无效') from None
        if path == resolved_root or not path.is_relative_to(resolved_root):
            raise errors.RequestError(msg='文件路径超出存储目录')
        return path

    @classmethod
    def resolve_record_path(cls, url_path: str) -> Path:
        """仅接受已知存储前缀，兼容原有公开上传记录"""
        for prefix, root in (
            ('/static/upload/private/', UPLOAD_DIR),
            ('/static/upload/public/avatar/', UPLOAD_DIR / 'avatar'),
            ('/static/upload/public/', UPLOAD_DIR / 'public'),
            ('/static/upload/avatar/', UPLOAD_DIR / 'avatar'),
            ('/static/upload/', UPLOAD_DIR / 'public'),
            ('/storage/public/files/', UPLOAD_DIR / 'public'),
            ('/storage/files/', UPLOAD_DIR),
        ):
            if url_path.startswith(prefix):
                return cls._resolve_storage_path(root, url_path[len(prefix) :])
        raise errors.RequestError(msg='文件存储记录无效')

    async def download(
        self, *, db: AsyncSession, file_id: int, user_id: int | None = None, managed: bool = False
    ) -> FileResponse:
        """先校验公开状态或上传者归属，再解析文件路径并准备下载"""
        record = (
            await file_dao.get_managed(db, file_id=file_id)
            if managed
            else await file_dao.get_accessible(db, file_id=file_id, user_id=user_id)
        )
        if record is None:
            raise errors.NotFoundError(msg='文件不存在')
        try:
            path = await to_thread.run_sync(self.resolve_record_path, record.url_path)
            exists = await to_thread.run_sync(path.is_file)
        except (errors.RequestError, OSError):
            raise errors.NotFoundError(msg='文件不存在') from None
        if not exists:
            raise errors.NotFoundError(msg='文件不存在')
        filename = re.split(r'[/\\]', record.original_name)[-1]
        filename = ''.join(char for char in filename if ord(char) >= 32 and ord(char) != 127) or 'download'
        return FileResponse(
            path,
            filename=filename,
            media_type='application/octet-stream',
            content_disposition_type='attachment',
            headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'},
        )

    @staticmethod
    def _get_upload_sub_dir(upload_type: UploadType, target_path: str | None = None) -> str:
        """
        获取上传子目录

        :param upload_type: 上传类型
        :param target_path: 目标路径（仅 resource 类型使用）
        :return:
        """
        now = timezone.now()
        date_path = now.strftime('%Y/%m/%d')

        if target_path is not None:
            if upload_type != UploadType.resource:
                raise errors.RequestError(msg='仅 resource 类型支持 target_path')
            FileService._validate_relative_path(target_path)
        if upload_type == UploadType.resource and target_path:
            return f'resource/{target_path}/{date_path}'

        path_map = {
            UploadType.file: f'file/{date_path}',
            UploadType.avatar: f'avatar/{date_path}',
            UploadType.resource: f'resource/{date_path}',
            UploadType.document: f'document/{date_path}',
            UploadType.image: f'image/{date_path}',
            UploadType.audio: f'audio/{date_path}',
            UploadType.video: f'video/{date_path}',
        }
        return path_map[upload_type]

    @staticmethod
    def _build_filename(original_name: str) -> str:
        """
        构建唯一文件名

        :param original_name: 原始文件名
        :return:
        """
        identifier = uuid4().hex
        file_ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
        base_name = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
        return f'{base_name[:120]}_{identifier}.{file_ext}' if file_ext else f'{base_name[:120]}_{identifier}'

    @staticmethod
    def _get_extension(filename: str) -> str:
        """获取文件扩展名"""
        if '.' not in filename:
            return ''
        return filename.rsplit('.', 1)[-1].lower()

    async def validate_upload(
        self,
        file: UploadFile,
        upload_type: UploadType,
    ) -> str:
        """
        验证上传文件

        :param file: 上传文件
        :param upload_type: 上传类型
        :return: 文件扩展名
        """
        return self.validate_metadata(file.filename, upload_type, file.size, file.content_type)

    def validate_metadata(
        self, filename: str | None, upload_type: UploadType, size: int | None, content_type: str | None
    ) -> str:
        """上传预检与单次上传共用的元信息校验"""
        if not filename:
            raise errors.RequestError(msg='文件名不能为空')
        self._validate_relative_path(filename)
        if '/' in filename or len(filename) > 240:
            raise errors.RequestError(msg='文件名不能包含目录且长度不能超过 240')

        ext = self._get_extension(filename)
        if not ext:
            raise errors.RequestError(msg='未知的文件类型')
        if len(ext) > 32:
            raise errors.RequestError(msg='文件扩展名过长')

        # 检查扩展名
        allowed_exts = UPLOAD_TYPE_EXTENSIONS.get(upload_type, [])
        if allowed_exts and ext not in allowed_exts:
            raise errors.RequestError(
                msg=f'上传类型 "{upload_type.value}" 不支持文件格式 ".{ext}"，支持的格式：{", ".join(allowed_exts)}'
            )
        allowed_mimes = settings.FILE_UPLOAD_ALLOWED_TYPES.get(ext, [])
        declared = (content_type or '').split(';', 1)[0].strip().lower()
        if not allowed_mimes or declared not in {'', 'application/octet-stream', *allowed_mimes}:
            raise errors.RequestError(msg='文件扩展名或 Content-Type 不在白名单中')

        # 检查文件大小
        size_limit = UPLOAD_TYPE_SIZE_LIMITS.get(upload_type, 0)
        if size is not None and (size <= 0 or size > size_limit):
            size_mb = size_limit / 1024 / 1024
            raise errors.RequestError(msg=f'文件超出大小限制（{size_mb:.0f} MB），请重新选择')

        return ext

    async def upload_destination(
        self,
        *,
        original_name: str,
        upload_type: UploadType,
        target_path: str | None,
        is_public: bool,
        name: str | None = None,
    ) -> Path:
        sub_dir = self._get_upload_sub_dir(upload_type, target_path)
        filename = name or self._build_filename(original_name)
        root = UPLOAD_DIR / 'public' if is_public and upload_type != UploadType.avatar else UPLOAD_DIR
        return await to_thread.run_sync(self._resolve_storage_path, root, f'{sub_dir}/{filename}')

    async def upload(
        self,
        db: AsyncSession,
        file: UploadFile,
        upload_type: UploadType = UploadType.file,
        target_path: str | None = None,
        user_id: int | None = None,
        *,
        is_public: bool | None = None,
        retention_policy: Literal['temporary', 'persistent'] = 'temporary',
    ) -> UploadFileDetail:
        """
        统一文件上传

        :param db: 数据库会话
        :param file: 上传文件
        :param upload_type: 上传类型
        :param target_path: 目标路径（仅 resource 类型使用）
        :param user_id: 上传用户 ID，同时作为下载归属校验依据
        :param is_public: 是否公开；不传时仅头像默认公开，所有类型均可显式设置
        :return:
        """
        if user_id is None:
            raise errors.RequestError(msg='上传文件必须指定归属用户')
        if is_public is None:
            is_public = upload_type == UploadType.avatar
        ext = await self.validate_upload(file, upload_type)

        # 2. 生成存储路径
        storage_path = await self.upload_destination(
            original_name=file.filename, upload_type=upload_type, target_path=target_path, is_public=is_public
        )
        filename = storage_path.name
        storage_dir = storage_path.parent

        # 使用独占创建，避免覆盖已有文件，并核验实际流大小
        size = 0
        try:
            await to_thread.run_sync(lambda: storage_dir.mkdir(parents=True, exist_ok=True))
            async with await open_file(storage_path, mode='xb') as fb:
                while True:
                    content = await file.read(settings.UPLOAD_READ_SIZE)
                    if not content:
                        break
                    size += len(content)
                    size_limit = UPLOAD_TYPE_SIZE_LIMITS.get(upload_type, 0)
                    if size > size_limit:
                        raise errors.RequestError(msg='文件超出大小限制，请重新选择')
                    await fb.write(content)
            if size == 0:
                raise errors.RequestError(msg='不允许上传空文件')
            mime_type = await to_thread.run_sync(validate_content, storage_path, ext, file.content_type)
        except BaseException as e:
            await to_thread.run_sync(lambda: storage_path.unlink(missing_ok=True))
            if isinstance(e, errors.RequestError) or not isinstance(e, Exception):
                raise
            log.error(f'上传文件 {filename} 失败：{e!s}')
            raise errors.RequestError(msg='上传文件失败') from None
        finally:
            await file.close()

        try:
            return await self.save_record(
                db=db,
                storage_path=storage_path,
                original_name=file.filename,
                upload_type=upload_type,
                user_id=user_id,
                is_public=is_public,
                size=size,
                mime_type=mime_type,
                retention_policy=retention_policy,
            )
        except BaseException:
            await to_thread.run_sync(lambda: storage_path.unlink(missing_ok=True))
            raise

    async def save_record(
        self,
        *,
        db: AsyncSession,
        storage_path: Path,
        original_name: str,
        upload_type: UploadType,
        user_id: int,
        is_public: bool,
        size: int,
        mime_type: str,
        retention_policy: Literal['temporary', 'persistent'] = 'temporary',
    ) -> UploadFileDetail:
        """单次上传和分片合并共用入库及头像处理"""
        static_public = is_public and upload_type in {UploadType.avatar, UploadType.image}
        root = UPLOAD_DIR / 'public' if is_public and upload_type != UploadType.avatar else UPLOAD_DIR
        sub_path = storage_path.relative_to(root).as_posix()
        prefix = (
            '/static/upload'
            if upload_type == UploadType.avatar and is_public
            else '/static/upload/public'
            if is_public
            else '/storage/files'
        )
        relative_url = f'{prefix}/{sub_path}'

        # 6. 保存文件记录（存相对路径，API 响应时拼完整 URL）
        record = FileRecord(
            name=storage_path.name,
            original_name=original_name,
            extension=self._get_extension(original_name),
            upload_type=upload_type.value,
            size=size,
            url_path=relative_url,
            mime_type=mime_type,
            user_id=user_id,
            retention_policy=retention_policy,
            unreferenced_at=timezone.now() if retention_policy == 'temporary' else None,
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)

        download_url = f'{settings.FASTAPI_API_V1_PATH}/files/download/{record.id}'
        # 7. 头像类型：更新用户头像字段（存相对路径，UserInfoSchemaBase.serialize_avatar 会拼完整 URL）
        if upload_type == UploadType.avatar and user_id is not None:
            from backend.app.admin.crud.crud_user import user_dao

            # 旧头像交给定时任务按所属用户回收，避免在上传事务提交前删除文件。
            await user_dao.update_avatar(db, user_id, relative_url if static_public else download_url)
            from backend.database.redis import redis_client

            await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{user_id}')

        return self.record_detail(record, is_public=is_public)

    @staticmethod
    def record_detail(record: FileRecord, *, is_public: bool) -> UploadFileDetail:
        download_url = f'{settings.FASTAPI_API_V1_PATH}/files/download/{record.id}'
        static_public = is_public and record.upload_type in {'avatar', 'image'}
        full_url = f'{settings.FASTAPI_SERVER_HOST}{record.url_path if static_public else download_url}'
        return UploadFileDetail(
            url=full_url,
            size=record.size,
            original_name=record.original_name,
            upload_type=record.upload_type,
            extension=record.extension,
            file_id=record.id,
            download_url=download_url,
            is_public=is_public,
            created_time=record.created_time,
        )


file_service: FileService = FileService()
