from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.opensandbox.model import SandboxRecord
from backend.plugin.opensandbox.schema.sandbox import SandboxRecordCreate
from backend.utils.timezone import timezone


class CRUDSandbox(CRUDPlus[SandboxRecord]):
    """OpenSandbox 沙盒记录数据库操作"""

    async def get_by_sandbox_id(
        self, db: AsyncSession, sandbox_id: str, *, include_deleted: bool = False
    ) -> SandboxRecord | None:
        """按沙盒 ID 获取记录"""

        filters = {'sandbox_id': sandbox_id}
        if not include_deleted:
            filters['deleted'] = 0
        return await self.select_model_by_column(db, **filters)

    async def get_select(
        self,
        *,
        user_id: int | None = None,
        username: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> Select:
        """获取沙盒列表查询"""

        filters = {'deleted': 0}
        if user_id is not None:
            filters['user_id'] = user_id
        if username is not None:
            filters['username__like'] = f'%{username}%'
        if status is not None:
            filters['status'] = status
        if keyword is not None:
            filters['name__like'] = f'%{keyword}%'
        return await self.select_order('last_activity_time', 'desc', **filters)

    async def get_idle(self, db: AsyncSession, cutoff: datetime) -> list[SandboxRecord]:
        """获取空闲但未删除的沙盒"""

        stmt = (
            select(self.model)
            .where(
                self.model.deleted == 0,
                self.model.last_activity_time < cutoff,
                self.model.status.in_(['Running', 'Pending']),
            )
            .order_by(self.model.last_activity_time.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_user(self, db: AsyncSession, user_id: int) -> list[SandboxRecord]:
        """获取用户未删除沙盒"""

        stmt = select(self.model).where(
            self.model.deleted == 0,
            self.model.user_id == user_id,
            self.model.status.notin_(['Terminated', 'Failed']),
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_active(self, db: AsyncSession) -> list[SandboxRecord]:
        """获取全部未删除且仍可恢复的沙盒"""

        stmt = select(self.model).where(
            self.model.deleted == 0,
            self.model.status.notin_(['Terminated', 'Failed']),
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_record(self, db: AsyncSession, obj: SandboxRecordCreate) -> SandboxRecord:
        """创建记录"""

        return await self.create_model(db, obj, flush=True)

    async def update_by_sandbox_id(self, db: AsyncSession, sandbox_id: str, data: dict) -> int:
        """按沙盒 ID 更新记录"""

        return await self.update_model_by_column(db, data, sandbox_id=sandbox_id, deleted=0)

    async def soft_delete(self, db: AsyncSession, sandbox_id: str) -> int:
        """逻辑删除记录"""

        return await self.update_model_by_column(
            db,
            {'deleted': 1, 'deleted_time': timezone.now(), 'status': 'Terminated'},
            sandbox_id=sandbox_id,
            deleted=0,
        )

    async def revive(self, db: AsyncSession, sandbox_id: str) -> int:
        """恢复已删除记录"""

        stmt = select(self.model).where(self.model.sandbox_id == sandbox_id).order_by(self.model.id.desc()).limit(1)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return 0
        record.deleted = 0
        record.deleted_time = None
        await db.flush()
        return 1

    async def count_all(self, db: AsyncSession) -> int:
        """统计未删除沙盒"""

        return await self.count(db, self.model.deleted == 0)

    async def count_state(self, db: AsyncSession, state: str) -> int:
        """统计指定状态沙盒"""

        return await self.count(db, self.model.deleted == 0, self.model.status == state)

    async def count_users(self, db: AsyncSession) -> int:
        """统计有沙盒的用户数"""

        stmt = select(func.count(func.distinct(self.model.user_id))).where(self.model.deleted == 0)
        return int((await db.execute(stmt)).scalar_one())


sandbox_dao: CRUDSandbox = CRUDSandbox(SandboxRecord)
