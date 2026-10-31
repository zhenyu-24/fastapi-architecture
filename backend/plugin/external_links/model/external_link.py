import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ExternalLink(Base):
    """外部页面分类和链接"""

    __tablename__ = 'sys_external_link'

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(sa.String(100))
    kind: Mapped[str] = mapped_column(sa.String(16))
    parent_id: Mapped[int | None] = mapped_column(sa.BigInteger, index=True)
    url: Mapped[str] = mapped_column(sa.String(2048))
    open_mode: Mapped[str] = mapped_column(sa.String(16))
    display_mode: Mapped[str] = mapped_column(sa.String(16))
    icon: Mapped[str] = mapped_column(sa.String(100))
    description: Mapped[str] = mapped_column(sa.String(500))
    sort: Mapped[int] = mapped_column()
    enabled: Mapped[bool] = mapped_column()
