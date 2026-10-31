from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.notice.crud.crud_notice import notice_dao
from backend.plugin.notice.crud.crud_user_notice import user_notice_dao
from backend.plugin.notice.model import UserNotice
from backend.plugin.notice.schema.user_notice import GetUserNoticeStatusDetail


class UserNoticeService:
    """用户通知公告关系服务类"""

    @staticmethod
    async def get_user_status(*, db: AsyncSession, user_id: int) -> list[GetUserNoticeStatusDetail]:
        """
        获取当前用户所有通知公告状态

        :param db: 数据库会话
        :param user_id: 用户 ID
        :return:
        """
        user_notices = await user_notice_dao.get_by_user(db, user_id)
        return [GetUserNoticeStatusDetail.model_validate(un) for un in user_notices]

    @staticmethod
    async def get_notices_with_status(*, db: AsyncSession, user_id: int) -> dict[str, Any]:
        """
        获取所有可见通知公告及其用户状态

        :param db: 数据库会话
        :param user_id: 用户 ID
        :return:
        """
        notices = await notice_dao.get_all(db, status=1)
        status_map = {}
        if user_id:
            user_notices = await user_notice_dao.get_by_user(db, user_id)
            status_map = {un.notice_id: un for un in user_notices}

        result = []
        for notice in notices:
            un = status_map.get(notice.id)
            result.append({
                'id': notice.id,
                'title': notice.title,
                'type': notice.type,
                'content': notice.content,
                'created_time': notice.created_time,
                'is_read': un.is_read if un else False,
                'deleted': un.deleted if un else 0,
            })

        return {'items': result}

    @staticmethod
    async def read(*, db: AsyncSession, user_id: int, notice_id: int) -> int:
        """
        标记通知公告为已读

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_id: 通知公告 ID
        :return:
        """
        return await user_notice_dao.upsert_read(db, user_id, notice_id)

    @staticmethod
    async def read_all(*, db: AsyncSession, user_id: int, notice_ids: list[int]) -> int:
        """
        全部标记为已读

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_ids: 通知公告 ID 列表
        :return:
        """
        return await user_notice_dao.mark_all_read(db, user_id, notice_ids)

    @staticmethod
    async def delete(*, db: AsyncSession, user_id: int, notice_id: int) -> int:
        """
        用户删除通知公告

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_id: 通知公告 ID
        :return:
        """
        return await user_notice_dao.upsert_delete(db, user_id, notice_id)

    @staticmethod
    async def clear(*, db: AsyncSession, user_id: int, notice_ids: list[int]) -> int:
        """
        清空用户通知公告

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param notice_ids: 通知公告 ID 列表
        :return:
        """
        return await user_notice_dao.clear_all(db, user_id, notice_ids)


user_notice_service: UserNoticeService = UserNoticeService()
