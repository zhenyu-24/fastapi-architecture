from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import FileRecord
from backend.app.admin.schema.file import CreateFileParam


class CRUDFile(CRUDPlus[FileRecord]):
    """文件记录数据库操作类"""

    async def get(self, db: AsyncSession, file_id: int) -> FileRecord | None:
        """
        获取文件记录

        :param db: 数据库会话
        :param file_id: 文件 ID
        :return:
        """
        return await self.select_model(db, file_id)

    async def create(self, db: AsyncSession, obj: CreateFileParam) -> FileRecord:
        """
        创建文件记录

        :param db: 数据库会话
        :param obj: 文件记录创建参数
        :return:
        """
        return await self.create_model(db, obj, commit=True)


file_dao: CRUDFile = CRUDFile(FileRecord)
