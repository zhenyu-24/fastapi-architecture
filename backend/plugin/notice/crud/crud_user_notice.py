from collections.abc import Sequence

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.notice.model import UserNotice
from backend.plugin.notice.schema.user_notice import CreateUserNoticeParam
from backend.utils.timezone import timezone


class CRUDUserNotice(CRUDPlus[UserNotice]):
    """用户通知公告关系数据库操作类"""

    async def get_by_user_and_notice(self, db: AsyncSession, user_id: int, notice_id: int) -> UserNotice | None:
        """
        获取用户与通知公告的关系记录

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_id: 通知公告 ID
        :return:
        """
        return await self.select_model_by_column(db, user_id=user_id, notice_id=notice_id)

    async def get_by_user(self, db: AsyncSession, user_id: int) -> Sequence[UserNotice]:
        """
        获取用户所有通知公告关系记录

        :param db: 数据库会话
        :param user_id: 用户 ID
        :return:
        """
        return await self.select_models(db, user_id=user_id)

    async def get_select_by_user(self, db: AsyncSession, user_id: int) -> Select:
        """
        获取用户通知公告关系查询表达式

        :param db: 数据库会话（未使用但保留接口一致性）
        :param user_id: 用户 ID
        :return:
        """
        return select(self.model).where(self.model.user_id == user_id)

    async def create(self, db: AsyncSession, user_id: int, notice_id: int) -> None:
        """
        创建用户通知公告关系记录

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_id: 通知公告 ID
        :return:
        """
        await self.create_model(db, CreateUserNoticeParam(user_id=user_id, notice_id=notice_id))

    async def upsert_read(self, db: AsyncSession, user_id: int, notice_id: int) -> int:
        """
        标记通知公告为已读（不存在则创建）

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_id: 通知公告 ID
        :return:
        """
        existing = await self.get_by_user_and_notice(db, user_id, notice_id)
        if existing:
            if not existing.is_read:
                stmt = (
                    update(self.model)
                    .where(self.model.user_id == user_id, self.model.notice_id == notice_id)
                    .values(is_read=True)
                )
                await db.execute(stmt)
                return 1
            return 0
        else:
            await self.create_model(db, CreateUserNoticeParam(user_id=user_id, notice_id=notice_id, is_read=True))
            return 1

    async def upsert_delete(self, db: AsyncSession, user_id: int, notice_id: int) -> int:
        """
        用户删除通知公告（不存在则创建并标记删除）

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_id: 通知公告 ID
        :return:
        """
        existing = await self.get_by_user_and_notice(db, user_id, notice_id)
        if existing:
            if existing.deleted != 0:
                return 0
            existing.deleted = existing.id
            existing.deleted_time = timezone.now()
            await db.flush()
            return 1
        else:
            model = self.model(user_id=user_id, notice_id=notice_id, is_read=False)
            db.add(model)
            await db.flush()
            model.deleted = model.id
            model.deleted_time = timezone.now()
            await db.flush()
            return 1

    async def mark_all_read(self, db: AsyncSession, user_id: int, notice_ids: list[int]) -> int:
        """
        批量标记通知公告为已读

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_ids: 通知公告 ID 列表
        :return:
        """
        count = 0
        for notice_id in notice_ids:
            count += await self.upsert_read(db, user_id, notice_id)
        return count

    async def clear_all(self, db: AsyncSession, user_id: int, notice_ids: list[int]) -> int:
        """
        批量删除用户通知公告

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_ids: 通知公告 ID 列表
        :return:
        """
        count = 0
        for notice_id in notice_ids:
            count += await self.upsert_delete(db, user_id, notice_id)
        return count


user_notice_dao: CRUDUserNotice = CRUDUserNotice(UserNotice)
