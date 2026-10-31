from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.files.model.file import FileRecord


class CRUDFile(CRUDPlus[FileRecord]):
    """文件记录数据库操作"""

    async def get_managed(self, db: AsyncSession, *, file_id: int, lock: bool = False) -> FileRecord | None:
        statement = select(self.model).where(self.model.id == file_id, self.model.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    @staticmethod
    def public_condition() -> ColumnElement[bool]:
        """与下载权限使用同一套历史路径规则"""
        return or_(
            and_(
                FileRecord.url_path.startswith('/static/upload/', autoescape=True),
                ~FileRecord.url_path.startswith('/static/upload/private/', autoescape=True),
            ),
            FileRecord.url_path.startswith('/storage/public/files/', autoescape=True),
        )

    async def get_manage_select(
        self,
        *,
        name: str | None,
        upload_type: str | None,
        is_public: bool | None,
        user_id: int | None,
        username: str | None = None,
    ) -> Select:
        statement = select(self.model).where(self.model.deleted == 0)
        if name:
            statement = statement.where(self.model.original_name.contains(name, autoescape=True))
        if upload_type:
            statement = statement.where(self.model.upload_type == upload_type)
        if is_public is not None:
            condition = self.public_condition()
            statement = statement.where(condition if is_public else ~condition)
        if user_id is not None:
            statement = statement.where(self.model.user_id == user_id)
        if username:
            from backend.app.admin.model.user import User

            statement = statement.where(
                self.model.user_id.in_(select(User.id).where(User.username.contains(username, autoescape=True)))
            )
        return statement.order_by(self.model.created_time.desc(), self.model.id.desc())

    async def get_uploaded(self, db: AsyncSession, *, name: str, user_id: int) -> FileRecord | None:
        return await db.scalar(
            select(self.model)
            .where(self.model.name == name, self.model.user_id == user_id, self.model.deleted == 0)
            .limit(1)
        )

    async def is_public_avatar(self, db: AsyncSession, *, url_path: str) -> bool:
        """同目录头像仅在存在公开记录或历史用户头像引用时允许静态展示"""
        from backend.app.admin.model.user import User
        from backend.core.conf import settings

        public_record = select(self.model.id).where(
            self.model.url_path == url_path,
            self.model.deleted == 0,
            self.model.upload_type == 'avatar',
        )
        if await db.scalar(public_record.limit(1)) is not None:
            return True
        return (
            await db.scalar(
                select(User.id)
                .where(
                    User.avatar.in_((url_path, f'{settings.FASTAPI_SERVER_HOST}{url_path}')),
                    User.deleted == 0,
                )
                .limit(1)
            )
            is not None
        )

    async def get_accessible(self, db: AsyncSession, *, file_id: int, user_id: int | None) -> FileRecord | None:
        """查询未删除的公开文件，或当前登录用户拥有的文件"""
        access = [self.public_condition()]
        if user_id is not None:
            access.append(self.model.user_id == user_id)
        return await db.scalar(
            select(self.model).where(
                self.model.id == file_id,
                self.model.deleted == 0,
                or_(*access),
            )
        )


file_dao = CRUDFile(FileRecord)
