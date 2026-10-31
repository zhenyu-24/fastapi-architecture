import errno
import os
import time

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.model.user import User
from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.core.storage import UPLOAD_DIR
from backend.database.db import async_db_session
from backend.plugin.files.model import FileRecord
from backend.plugin.files.service.chunk_service import chunk_service
from backend.plugin.files.service.file_service import file_service
from backend.plugin.files.service.reference_service import reference_service
from backend.utils.timezone import timezone


@dataclass
class CleanupResult:
    deleted_records: int = 0
    expired_sessions: int = 0
    failed_files: int = 0
    untracked_files: int = 0
    deleted_files: int = 0
    deleted_directories: int = 0
    retained_known_files: int = 0
    retained_recent_files: int = 0


class CleanupService:
    """回收超过保留期的无引用临时文件，并提供年度磁盘清理。"""

    @staticmethod
    def storage_link(path: Path) -> bool:
        return path.is_symlink() or os.path.isjunction(path)

    @classmethod
    def purge_file(cls, path: Path, known_paths: set[Path], cutoff: float, result: CleanupResult) -> None:
        root = UPLOAD_DIR.resolve()
        try:
            if cls.storage_link(path) or any(cls.storage_link(part) for part in path.parents if part != root):
                return
            resolved = path.resolve()
            if not resolved.is_relative_to(root) or not path.is_file():
                return
            if resolved in known_paths:
                result.retained_known_files += 1
                return
            if path.stat().st_mtime >= cutoff:
                result.retained_recent_files += 1
                return
            path.unlink()
            result.deleted_files += 1
        except FileNotFoundError:
            pass
        except OSError as exc:
            result.failed_files += 1
            log.warning(f'清理无记录文件失败：{path}：{exc!s}')

    @classmethod
    def purge_directories(cls, directories: list[Path], result: CleanupResult) -> None:
        root = UPLOAD_DIR.resolve()
        for path in reversed(directories):
            try:
                if cls.storage_link(path) or not path.resolve().is_relative_to(root):
                    continue
                path.rmdir()
                result.deleted_directories += 1
            except FileNotFoundError:
                continue
            except OSError as exc:
                if exc.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                    result.failed_files += 1
                    log.warning(f'清理空目录失败：{path}：{exc!s}')

    @classmethod
    def purge_storage(cls, known_paths: set[Path], result: CleanupResult) -> None:
        """仅操作存储根目录内部，不跟随符号链接或 Windows 目录联接。"""
        root = UPLOAD_DIR.resolve()
        cutoff = time.time() - settings.FILE_UPLOAD_TTL_SECONDS
        directories: list[Path] = []

        def walk_error(exc: OSError) -> None:
            result.failed_files += 1
            log.warning(f'扫描存储目录失败：{exc!s}')

        for directory, subdirs, filenames in os.walk(root, followlinks=False, onerror=walk_error):
            parent = Path(directory)
            subdirs[:] = [name for name in subdirs if name != '.chunks' and not cls.storage_link(parent / name)]
            directories.extend(parent / name for name in subdirs)
            for filename in filenames:
                cls.purge_file(parent / filename, known_paths, cutoff, result)
        cls.purge_directories(directories, result)

    async def cleanup_storage(self) -> CleanupResult:
        if not await to_thread.run_sync(UPLOAD_DIR.is_dir):
            raise errors.RequestError(msg='文件存储目录不可用，已取消清理')
        result = CleanupResult()
        async with async_db_session.begin() as db:
            # 包含软删除记录；这些文件仍由文件记录清理流程负责。
            records = (await db.scalars(select(FileRecord))).all()
            resolved = await self.resolve_records(records=records, result=result)
            if result.failed_files:
                raise errors.RequestError(msg='存在无法解析的文件记录，已取消年度存储清理')
            await to_thread.run_sync(self.purge_storage, {path for _, path in resolved}, result)
        return result

    @staticmethod
    def avatar_references(avatars: list[str]) -> tuple[set[Path], set[int]]:
        paths: set[Path] = set()
        file_ids: set[int] = set()
        download_prefix = f'{settings.FASTAPI_API_V1_PATH}/files/download/'
        for avatar in avatars:
            try:
                url_path = urlsplit(avatar).path
                if url_path.startswith(download_prefix) and url_path[len(download_prefix) :].isdigit():
                    file_ids.add(int(url_path[len(download_prefix) :]))
                else:
                    paths.add(file_service.resolve_record_path(url_path))
            except (errors.RequestError, ValueError):
                continue
        return paths, file_ids

    @staticmethod
    def find_untracked_files(known_paths: set[Path]) -> list[Path]:
        """仅报告超过上传 TTL 的无记录文件，不删除可能尚未提交的上传。"""
        root = UPLOAD_DIR.resolve()
        cutoff = time.time() - settings.FILE_UPLOAD_TTL_SECONDS
        candidates: list[Path] = []
        for directory, subdirs, filenames in os.walk(root, followlinks=False):
            subdirs[:] = [name for name in subdirs if name != '.chunks' and not (Path(directory) / name).is_symlink()]
            for filename in filenames:
                path = Path(directory) / filename
                try:
                    if path.is_symlink():
                        continue
                    resolved = path.resolve()
                    if resolved.is_relative_to(root) and resolved not in known_paths and path.stat().st_mtime < cutoff:
                        candidates.append(path)
                except OSError as exc:
                    log.warning(f'检查无记录文件失败：{path}：{exc!s}')
        return candidates

    async def owner_uses_avatar(self, *, db: AsyncSession, record: FileRecord, path: Path) -> bool:
        if record.user_id is None:
            return False
        avatar = await db.scalar(select(User.avatar).where(User.id == record.user_id, User.deleted == 0))
        if not avatar:
            return False
        paths, file_ids = await to_thread.run_sync(self.avatar_references, [avatar])
        return path in paths or record.id in file_ids

    @staticmethod
    async def resolve_records(*, records: list[FileRecord], result: CleanupResult) -> list[tuple[FileRecord, Path]]:
        resolved: list[tuple[FileRecord, Path]] = []
        for record in records:
            try:
                path = await to_thread.run_sync(file_service.resolve_record_path, record.url_path)
            except errors.RequestError:
                log.warning(f'跳过无效文件路径，保留记录以便核查：id={record.id}，path={record.url_path}')
                result.failed_files += 1
                continue
            resolved.append((record, path))
        return resolved

    async def cleanup(self) -> CleanupResult:
        if not await to_thread.run_sync(UPLOAD_DIR.is_dir):
            raise errors.RequestError(msg='文件存储目录不可用，已取消清理')
        result = CleanupResult(expired_sessions=await to_thread.run_sync(chunk_service.cleanup))
        async with async_db_session.begin() as db:
            records = (await db.scalars(select(FileRecord).order_by(FileRecord.id).with_for_update())).all()
            resolved_records = await self.resolve_records(records=records, result=result)
            known_paths = {path for _, path in resolved_records}

            for record, path in resolved_records:
                try:
                    exists = await to_thread.run_sync(path.exists)
                    if await reference_service.is_referenced(db=db, file_id=record.id):
                        continue
                    if exists:
                        if record.retention_policy != 'temporary' or record.deleted:
                            continue
                        if record.unreferenced_at is None:
                            record.unreferenced_at = timezone.now()
                            continue
                        cutoff = timezone.now() - timedelta(seconds=settings.FILE_UPLOAD_TTL_SECONDS)
                        if record.unreferenced_at >= cutoff:
                            continue
                        # 删除失败时保留记录，下次调度可重试；文件已被其他清理者移除视为成功。
                        await to_thread.run_sync(lambda: path.unlink(missing_ok=True))
                    await db.delete(record)
                    result.deleted_records += 1
                except OSError as exc:
                    result.failed_files += 1
                    log.warning(f'清理文件失败，保留记录：id={record.id}，path={path}：{exc!s}')

            untracked = await to_thread.run_sync(self.find_untracked_files, known_paths)
            result.untracked_files = len(untracked)
            for path in untracked:
                log.warning(f'发现超过上传 TTL 的无记录文件，保留待核查：{path}')
        return result


cleanup_service = CleanupService()
