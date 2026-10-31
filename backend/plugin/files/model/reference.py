import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, DateTimeMixin, id_key


class FileReference(DataClassBase, DateTimeMixin):
    """文件业务引用，不参与软删除。"""

    __tablename__ = 'sys_file_reference'
    __table_args__ = (
        sa.UniqueConstraint('file_id', 'business_type', 'business_id', 'field', name='uk_file_reference'),
        sa.Index('idx_file_reference_business', 'business_type', 'business_id', 'field'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    file_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey('sys_file_record.id', ondelete='CASCADE'), index=True
    )
    business_type: Mapped[str] = mapped_column(sa.String(64))
    business_id: Mapped[int] = mapped_column(sa.BigInteger)
    field: Mapped[str] = mapped_column(sa.String(64))
