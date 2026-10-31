from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.core.conf import settings
from backend.plugin.files.model import FileRecord, FileReference
from backend.utils.timezone import timezone


class FileReferenceService:
    """所有引用写入与回收都先锁定文件记录，锁持有到业务事务提交。"""

    @staticmethod
    async def resolve(*, db: AsyncSession, value: str, strict: bool = True) -> FileRecord | None:
        parsed = urlsplit(value)
        if parsed.netloc and parsed.netloc != urlsplit(settings.FASTAPI_SERVER_HOST).netloc:
            return None
        prefix = f'{settings.FASTAPI_API_V1_PATH}/files/download/'
        condition = FileRecord.url_path == parsed.path
        if parsed.path.startswith(prefix) and parsed.path[len(prefix) :].isdigit():
            condition = FileRecord.id == int(parsed.path[len(prefix) :])
        record = await db.scalar(select(FileRecord).where(condition, FileRecord.deleted == 0))
        if strict and record is None and parsed.path.startswith(('/static/upload/', '/storage/', prefix)):
            raise errors.RequestError(msg='本地文件不存在，请重新上传')
        return record

    async def sync(self, *, db: AsyncSession, business_type: str, business_id: int, field: str, value: str) -> None:
        target = await self.resolve(db=db, value=value) if value else None
        old = list(
            (
                await db.scalars(
                    select(FileReference).where(
                        FileReference.business_type == business_type,
                        FileReference.business_id == business_id,
                        FileReference.field == field,
                    )
                )
            ).all()
        )
        ids = {ref.file_id for ref in old}
        if target:
            ids.add(target.id)
        records = list(
            (
                await db.scalars(
                    select(FileRecord)
                    .where(FileRecord.id.in_(ids))
                    .order_by(FileRecord.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).all()
        )
        by_id = {record.id: record for record in records}
        if target and (target.id not in by_id or by_id[target.id].deleted):
            raise errors.ConflictError(msg='文件已被清理，请重新上传')
        for ref in old:
            if target is None or ref.file_id != target.id:
                await db.delete(ref)
        if target and not any(ref.file_id == target.id for ref in old):
            db.add(FileReference(file_id=target.id, business_type=business_type, business_id=business_id, field=field))
        await db.flush()
        for record in records:
            used = await self.is_referenced(db=db, file_id=record.id)
            if used:
                record.unreferenced_at = None
            elif record.unreferenced_at is None:
                record.unreferenced_at = timezone.now()
        await db.flush()

    @staticmethod
    async def is_referenced(*, db: AsyncSession, file_id: int) -> bool:
        return (
            await db.scalar(select(FileReference.id).where(FileReference.file_id == file_id).limit(1).with_for_update())
            is not None
        )

    async def require_unused(self, *, db: AsyncSession, file_id: int) -> None:
        if await self.is_referenced(db=db, file_id=file_id):
            raise errors.ConflictError(msg='该文件正在被业务使用，请先解除引用')


reference_service = FileReferenceService()
