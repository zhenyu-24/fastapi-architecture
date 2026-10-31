import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class UserNotice(Base):
    """用户通知公告关系表"""

    __tablename__ = 'sys_user_notice'
    __table_args__ = (
        sa.UniqueConstraint('user_id', 'notice_id', 'deleted', name='uk_sys_user_notice_user_id_notice_id_deleted'),
        {'comment': '用户通知公告关系表'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('sys_user.id', ondelete='CASCADE'), index=True, comment='用户ID')
    notice_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('sys_notice.id', ondelete='CASCADE'), index=True, comment='通知公告ID')
    is_read: Mapped[bool] = mapped_column(default=False, comment='是否已读')
    # deleted / deleted_time 继承自 Base → LogicalDeleteMixin
