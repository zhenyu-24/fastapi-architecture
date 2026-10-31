import posixpath

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.core.conf import settings
from backend.plugin.opensandbox.model import SandboxRecord
from backend.plugin.opensandbox.schema.sandbox import (
    FileDeleteParam,
    FileEntry,
    FileMkdirParam,
    FileRenameParam,
    FileWriteParam,
    TextFileResult,
)
from backend.plugin.opensandbox.service.command_service import normalize_workspace_path
from backend.plugin.opensandbox.service.sandbox_service import sandbox_service
from backend.plugin.opensandbox.utils.client import OpenSandboxError, open_sandbox_client
from backend.plugin.opensandbox.utils.dynamic_config import load_sandbox_config


class FileService:
    """沙盒文件服务"""

    @staticmethod
    def _to_entry(entry: Any) -> FileEntry:
        return FileEntry(
            path=entry.path,
            name=posixpath.basename(entry.path.rstrip('/')) or entry.path,
            type='directory' if entry.entry_type in {'directory', 'dir'} else 'file',
            size=entry.size or 0,
            mode=str(entry.mode) if entry.mode is not None else None,
            modified_at=entry.modified_at,
        )

    async def _record(
        self, *, db: AsyncSession, sandbox_id: str, user_id: int, username: str, is_admin: bool
    ) -> SandboxRecord:
        return await sandbox_service.ensure_access(
            db=db, sandbox_id=sandbox_id, user_id=user_id, is_admin=is_admin, username=username
        )

    async def list(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        path: str | None,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> list[FileEntry]:
        """列出目录"""

        await self._record(db=db, sandbox_id=sandbox_id, user_id=user_id, username=username, is_admin=is_admin)
        target = normalize_workspace_path(path)
        try:
            entries = await open_sandbox_client.list_files(sandbox_id, target)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'读取目录失败：{exc}') from exc
        await sandbox_service.touch(db, sandbox_id=sandbox_id)
        result = [self._to_entry(entry) for entry in entries]
        return sorted(result, key=lambda item: (item.type != 'directory', item.name.lower()))

    async def read(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        path: str,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> TextFileResult:
        """读取文本文件"""

        await load_sandbox_config(db)
        await self._record(db=db, sandbox_id=sandbox_id, user_id=user_id, username=username, is_admin=is_admin)
        target = normalize_workspace_path(path, allow_root=False)
        try:
            info = await open_sandbox_client.file_info(sandbox_id, target)
            if not info:
                raise errors.NotFoundError(msg='文件不存在')
            if info.entry_type in {'directory', 'dir'}:
                raise errors.RequestError(msg='不能以文本方式读取目录')
            limit = min(int(info.size or 0), settings.OPEN_SANDBOX_FILE_TEXT_LIMIT_BYTES)
            data = await open_sandbox_client.read_bytes(sandbox_id, target, max(limit, 1))
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'读取文件失败：{exc}') from exc
        await sandbox_service.touch(db, sandbox_id=sandbox_id)
        is_binary = b'\x00' in data
        try:
            content = data.decode('utf-8')
        except UnicodeDecodeError:
            is_binary = True
            content = ''
        return TextFileResult(
            path=target,
            content=content,
            size=info.size or 0,
            is_binary=is_binary,
            truncated=(info.size or 0) > len(data),
        )

    async def write(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        obj: FileWriteParam,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> str:
        """写入文本文件"""

        await self._record(db=db, sandbox_id=sandbox_id, user_id=user_id, username=username, is_admin=is_admin)
        target = normalize_workspace_path(obj.path, allow_root=False)
        try:
            await open_sandbox_client.write_file(sandbox_id, target, obj.content)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'保存文件失败：{exc}') from exc
        await sandbox_service.touch(db, sandbox_id=sandbox_id)
        return target

    async def mkdir(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        obj: FileMkdirParam,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> str:
        """创建目录"""

        await self._record(db=db, sandbox_id=sandbox_id, user_id=user_id, username=username, is_admin=is_admin)
        target = normalize_workspace_path(obj.path, allow_root=False)
        try:
            await open_sandbox_client.mkdir(sandbox_id, target)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'创建目录失败：{exc}') from exc
        await sandbox_service.touch(db, sandbox_id=sandbox_id)
        return target

    async def rename(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        obj: FileRenameParam,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> str:
        """重命名或移动"""

        await self._record(db=db, sandbox_id=sandbox_id, user_id=user_id, username=username, is_admin=is_admin)
        source = normalize_workspace_path(obj.source, allow_root=False)
        destination = normalize_workspace_path(obj.destination, allow_root=False)
        try:
            await open_sandbox_client.move(sandbox_id, source, destination)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'重命名失败：{exc}') from exc
        await sandbox_service.touch(db, sandbox_id=sandbox_id)
        return destination

    async def delete(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        obj: FileDeleteParam,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> None:
        """删除文件或目录"""

        await self._record(db=db, sandbox_id=sandbox_id, user_id=user_id, username=username, is_admin=is_admin)
        target = normalize_workspace_path(obj.path, allow_root=False)
        try:
            info = await open_sandbox_client.file_info(sandbox_id, target)
            if not info:
                raise errors.NotFoundError(msg='文件或目录不存在')
            await open_sandbox_client.delete_path(
                sandbox_id,
                target,
                is_directory=info.entry_type in {'directory', 'dir'},
            )
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'删除失败：{exc}') from exc
        await sandbox_service.touch(db, sandbox_id=sandbox_id)

    async def upload(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        path: str,
        filename: str,
        data: bytes,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> str:
        """上传文件"""

        await load_sandbox_config(db)
        if len(data) > settings.OPEN_SANDBOX_UPLOAD_LIMIT_BYTES:
            raise errors.RequestError(msg='上传文件超过大小限制')
        await self._record(db=db, sandbox_id=sandbox_id, user_id=user_id, username=username, is_admin=is_admin)
        directory = normalize_workspace_path(path)
        target = posixpath.join(directory, posixpath.basename(filename))
        target = normalize_workspace_path(target, allow_root=False)
        sandbox_service.mark_active(sandbox_id)
        try:
            await open_sandbox_client.write_file(sandbox_id, target, data)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'上传文件失败：{exc}') from exc
        finally:
            sandbox_service.unmark_active(sandbox_id)
        await sandbox_service.touch(db, sandbox_id=sandbox_id)
        return target

    async def download_name(
        self,
        *,
        db: AsyncSession,
        sandbox_id: str,
        path: str,
        user_id: int,
        username: str,
        is_admin: bool,
    ) -> tuple[str, str]:
        """校验下载文件并返回路径和文件名"""

        await self._record(db=db, sandbox_id=sandbox_id, user_id=user_id, username=username, is_admin=is_admin)
        target = normalize_workspace_path(path, allow_root=False)
        try:
            info = await open_sandbox_client.file_info(sandbox_id, target)
        except OpenSandboxError as exc:
            raise errors.GatewayError(msg=f'获取文件信息失败：{exc}') from exc
        if not info:
            raise errors.NotFoundError(msg='文件不存在')
        if info.entry_type in {'directory', 'dir'}:
            raise errors.RequestError(msg='不能直接下载目录')
        await sandbox_service.touch(db, sandbox_id=sandbox_id)
        return target, posixpath.basename(target)


file_service: FileService = FileService()
