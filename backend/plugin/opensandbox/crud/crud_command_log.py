from datetime import datetime

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.opensandbox.model import CommandLog
from backend.plugin.opensandbox.schema.sandbox import CommandLogCreate


class CRUDCommandLog(CRUDPlus[CommandLog]):
    """OpenSandbox 命令审计数据库操作"""

    async def get(self, db: AsyncSession, pk: int) -> CommandLog | None:
        """获取命令日志"""

        return await self.select_model(db, pk, deleted=0)

    async def get_select(
        self,
        *,
        user_id: int | None = None,
        username: str | None = None,
        sandbox_id: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Select:
        """获取命令日志列表查询"""

        filters = {'deleted': 0}
        if user_id is not None:
            filters['user_id'] = user_id
        if username is not None:
            filters['username__like'] = f'%{username}%'
        if sandbox_id is not None:
            filters['sandbox_id'] = sandbox_id
        if status is not None:
            filters['status'] = status
        if start_time is not None:
            filters['created_time__ge'] = start_time
        if end_time is not None:
            filters['created_time__le'] = end_time
        if keyword is not None:
            filters['command__like'] = f'%{keyword}%'
        return await self.select_order('created_time', 'desc', **filters)

    async def create(self, db: AsyncSession, obj: CommandLogCreate) -> CommandLog:
        """写入命令日志"""

        return await self.create_model(db, obj, flush=True)

    async def count_all(self, db: AsyncSession) -> int:
        """统计命令日志总数"""

        return await self.count(db, self.model.deleted == 0)


command_log_dao: CRUDCommandLog = CRUDCommandLog(CommandLog)
