import hashlib
import json
import math
import re
import shutil
import time

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from anyio import open_file, to_thread
from fastapi import Request
from filelock import FileLock, Timeout

from backend.common.exception import errors
from backend.core.conf import settings
from backend.database.db import async_db_session
from backend.plugin.files.crud.crud_file import file_dao
from backend.plugin.files.schema.file import UploadFileDetail, UploadPrecheckDetail, UploadPrecheckParam
from backend.plugin.files.service.file_service import file_service
from backend.plugin.files.service.validation import validate_content


class ChunkService:
    """本地共享存储上的可恢复上传；锁覆盖请求及数据库提交"""

    @property
    def root(self) -> Path:
        from backend.plugin.files.service import file_service as module

        return module.UPLOAD_DIR / '.chunks'

    def lock_path(self, key: str) -> Path:
        """固定数量锁文件，防止会话过期后仍持续积累锁文件"""
        category = 'user' if key.startswith('user-') else 'upload'
        bucket = hashlib.sha256(key.encode()).hexdigest()[:2]
        return self.root / f'{category}-{bucket}.lock'

    @asynccontextmanager
    async def lock(self, key: str) -> AsyncGenerator[None, None]:
        root = self.root
        await to_thread.run_sync(lambda: root.mkdir(parents=True, exist_ok=True))
        lock = FileLock(self.lock_path(key), thread_local=False)
        try:
            await to_thread.run_sync(lambda: lock.acquire(timeout=0))
        except Timeout:
            raise errors.ConflictError(msg='上传正在处理，请稍后重试') from None
        try:
            yield
        finally:
            await to_thread.run_sync(lock.release)

    def load(self, upload_id: str, user_id: int) -> tuple[Path, dict]:
        if re.fullmatch(r'[a-f0-9]{64}', upload_id) is None:
            raise errors.NotFoundError(msg='上传会话不存在')
        directory = self.root / str(user_id) / upload_id
        try:
            metadata = json.loads((directory / 'meta.json').read_text(encoding='utf-8'))
        except FileNotFoundError:
            raise errors.NotFoundError(msg='上传会话不存在') from None
        if time.time() - (directory / 'meta.json').stat().st_mtime > settings.FILE_UPLOAD_TTL_SECONDS:
            raise errors.NotFoundError(msg='上传会话已过期，请重新预检')
        return directory, metadata

    @staticmethod
    def write_metadata(directory: Path, metadata: dict) -> None:
        temporary = directory / f'{uuid4().hex}.tmp'
        try:
            temporary.write_text(json.dumps(metadata), encoding='utf-8')
            temporary.replace(directory / 'meta.json')
        finally:
            temporary.unlink(missing_ok=True)

    async def completed(self, metadata: dict, user_id: int) -> UploadFileDetail | None:
        async with async_db_session() as db:
            record = await file_dao.get_uploaded(db, name=metadata['name'], user_id=user_id)
            if record is None:
                return None
            path = await to_thread.run_sync(file_service.resolve_record_path, record.url_path)
            if not await to_thread.run_sync(path.is_file):
                return None
            return file_service.record_detail(record, is_public=metadata['params']['is_public'])

    async def precheck(self, *, param: UploadPrecheckParam, user_id: int) -> UploadPrecheckDetail:
        file_service.validate_metadata(param.filename, param.upload_type, param.size, param.content_type)
        file_service._get_upload_sub_dir(param.upload_type, param.target_path)
        values = param.model_dump(mode='json')
        values['is_public'] = param.upload_type == 'avatar' if param.is_public is None else param.is_public
        upload_id = hashlib.sha256(f'{user_id}:{json.dumps(values, sort_keys=True)}'.encode()).hexdigest()
        async with self.lock(f'user-{user_id}'):
            await to_thread.run_sync(self.cleanup, user_id)
            async with self.lock(upload_id):
                directory = self.root / str(user_id) / upload_id
                if not await to_thread.run_sync((directory / 'meta.json').is_file):
                    active = await to_thread.run_sync(
                        lambda: sum(
                            not json.loads(path.read_text(encoding='utf-8')).get('completed', False)
                            for path in directory.parent.glob('*/meta.json')
                        )
                    )
                    if active >= settings.FILE_UPLOAD_MAX_SESSIONS:
                        raise errors.RequestError(msg='未完成的上传过多，请取消旧上传或等待过期')
                    destination = await file_service.upload_destination(
                        original_name=param.filename,
                        upload_type=param.upload_type,
                        target_path=param.target_path,
                        is_public=values['is_public'],
                    )
                    metadata = {
                        'params': values,
                        'chunk_size': settings.FILE_UPLOAD_CHUNK_SIZE,
                        'name': destination.name,
                        'destination': str(destination),
                    }
                    await to_thread.run_sync(lambda: directory.mkdir(parents=True, exist_ok=True))
                    await to_thread.run_sync(self.write_metadata, directory, metadata)
                directory, metadata = await to_thread.run_sync(self.load, upload_id, user_id)
                result = await self.completed(metadata, user_id)
                if result is not None and not metadata.get('completed'):
                    await to_thread.run_sync(self.finish, directory, metadata)
                chunks = await to_thread.run_sync(
                    lambda: sorted(int(path.stem) for path in directory.glob('*.part') if path.stem.isdigit())
                )
                return UploadPrecheckDetail(
                    upload_id=upload_id,
                    chunk_size=metadata['chunk_size'],
                    total_chunks=math.ceil(param.size / metadata['chunk_size']),
                    uploaded_chunks=chunks,
                    file=result,
                )

    async def upload_chunk(self, *, upload_id: str, index: int, user_id: int, request: Request, sha256: str) -> None:
        async with self.lock(upload_id):
            directory, metadata = await to_thread.run_sync(self.load, upload_id, user_id)
            size = metadata['params']['size']
            chunk_size = metadata['chunk_size']
            count = math.ceil(size / chunk_size)
            if index < 0 or index >= count:
                raise errors.RequestError(msg='分片序号无效')
            expected = min(chunk_size, size - index * chunk_size)
            content_length = request.headers.get('content-length')
            if content_length is not None and content_length != str(expected):
                raise errors.RequestError(msg='分片长度不匹配')
            temporary = directory / f'{uuid4().hex}.tmp'
            digest = hashlib.sha256()
            received = 0
            try:
                async with await open_file(temporary, 'xb') as output:
                    async for block in request.stream():
                        received += len(block)
                        if received > expected:
                            raise errors.RequestError(msg='分片超出大小限制')
                        digest.update(block)
                        await output.write(block)
                if received != expected or digest.hexdigest() != sha256:
                    raise errors.RequestError(msg='分片长度或 SHA-256 校验失败')
                await to_thread.run_sync(temporary.replace, directory / f'{index}.part')
                await to_thread.run_sync((directory / 'meta.json').touch)
            finally:
                await to_thread.run_sync(lambda: temporary.unlink(missing_ok=True))

    @staticmethod
    def assemble(directory: Path, metadata: dict, destination: Path) -> str:
        param = UploadPrecheckParam(**metadata['params'])
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = directory / 'merged.tmp'
        digest = hashlib.sha256()
        received = 0
        try:
            with temporary.open('wb') as output:
                count = math.ceil(param.size / metadata['chunk_size'])
                for index in range(count):
                    part = directory / f'{index}.part'
                    expected = min(metadata['chunk_size'], param.size - index * metadata['chunk_size'])
                    if not part.is_file() or part.stat().st_size != expected:
                        raise errors.RequestError(msg=f'分片 {index} 缺失或长度错误')
                    with part.open('rb') as source:
                        while block := source.read(settings.UPLOAD_READ_SIZE):
                            received += len(block)
                            if received > param.size:
                                raise errors.RequestError(msg='合并文件超出大小限制')
                            digest.update(block)
                            output.write(block)
            if received != param.size or digest.hexdigest() != param.sha256:
                raise errors.RequestError(msg='完整文件 SHA-256 校验失败，请重新上传')
            mime = validate_content(temporary, Path(param.filename).suffix[1:].lower(), param.content_type)
            temporary.replace(destination)
            return mime
        finally:
            temporary.unlink(missing_ok=True)

    async def merge(self, *, upload_id: str, user_id: int) -> UploadFileDetail:
        async with self.lock(upload_id):
            directory, metadata = await to_thread.run_sync(self.load, upload_id, user_id)
            existing = await self.completed(metadata, user_id)
            if existing is not None:
                await to_thread.run_sync(self.finish, directory, metadata)
                return existing
            param = UploadPrecheckParam(**metadata['params'])
            file_service.validate_metadata(param.filename, param.upload_type, param.size, param.content_type)
            # 元数据仅由服务端生成，但每次合并仍重新检查路径边界。
            from backend.plugin.files.service import file_service as module

            destination = Path(metadata['destination'])
            relative = destination.relative_to(module.UPLOAD_DIR).as_posix()
            destination = await to_thread.run_sync(file_service._resolve_storage_path, module.UPLOAD_DIR, relative)
            mime = await to_thread.run_sync(self.assemble, directory, metadata, destination)
            try:
                async with async_db_session.begin() as db:
                    detail = await file_service.save_record(
                        db=db,
                        storage_path=destination,
                        original_name=param.filename,
                        upload_type=param.upload_type,
                        user_id=user_id,
                        is_public=param.is_public,
                        size=param.size,
                        mime_type=mime,
                        retention_policy=param.retention_policy,
                    )
            except BaseException:
                await to_thread.run_sync(lambda: destination.unlink(missing_ok=True))
                raise
            await to_thread.run_sync(self.finish, directory, metadata)
            return detail

    @staticmethod
    def finish(directory: Path, metadata: dict) -> None:
        metadata['completed'] = True
        ChunkService.write_metadata(directory, metadata)
        for part in directory.glob('*.part'):
            part.unlink(missing_ok=True)

    async def cancel(self, *, upload_id: str, user_id: int) -> None:
        async with self.lock(upload_id):
            directory, _ = await to_thread.run_sync(self.load, upload_id, user_id)
            await to_thread.run_sync(self.remove_session, directory)

    def remove_session(self, directory: Path) -> None:
        root = self.root.resolve()
        resolved = directory.resolve()
        if resolved == root or not resolved.is_relative_to(root):
            raise errors.RequestError(msg='上传会话路径超出存储目录')
        shutil.rmtree(resolved)

    def cleanup(self, user_id: int | None = None) -> int:
        """跳过正被使用的会话；完成回执也随 TTL 清除"""
        root = self.root
        directories = (root / str(user_id)).glob('*') if user_id is not None else root.glob('*/*')
        removed = 0
        for directory in directories:
            if not directory.is_dir():
                continue
            try:
                with FileLock(self.lock_path(directory.name), timeout=0):
                    metadata = directory / 'meta.json'
                    if time.time() - metadata.stat().st_mtime <= settings.FILE_UPLOAD_TTL_SECONDS:
                        continue
                    self.remove_session(directory)
                    removed += 1
            except (Timeout, FileNotFoundError):
                continue
        return removed


chunk_service = ChunkService()
