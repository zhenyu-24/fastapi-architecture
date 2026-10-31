from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, id_key
from backend.utils.timezone import timezone


class SandboxRecord(Base):
    """OpenSandbox 沙盒归属与活动记录"""

    __tablename__ = 'sys_opensandbox'
    __table_args__ = (
        sa.UniqueConstraint('sandbox_id', name='uk_sys_opensandbox_sandbox_id'),
        {'comment': 'OpenSandbox 沙盒归属与活动记录'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    sandbox_id: Mapped[str] = mapped_column(sa.String(64), index=True, comment='OpenSandbox 沙盒 ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='沙盒名称')
    image: Mapped[str] = mapped_column(sa.String(512), comment='沙盒镜像')
    user_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='归属用户 ID')
    username: Mapped[str] = mapped_column(sa.String(64), comment='归属用户名')
    status: Mapped[str] = mapped_column(sa.String(16), default='Pending', index=True, comment='最近状态')
    last_activity_time: Mapped[datetime] = mapped_column(
        TimeZone, default_factory=timezone.now, index=True, comment='最后活动时间'
    )
    paused_time: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='暂停时间')
    expires_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='过期时间，空表示不自动删除')
