from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, id_key


class FileRecord(Base):
    """文件上传记录表"""

    __tablename__ = 'sys_file_record'
    __table_args__ = (
        sa.Index('idx_sys_file_record_upload_type', 'upload_type'),
        sa.Index('idx_sys_file_record_created_time', 'created_time'),
        {'comment': '文件上传记录表'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(256), comment='文件名')
    original_name: Mapped[str] = mapped_column(sa.String(256), comment='原始文件名')
    extension: Mapped[str] = mapped_column(sa.String(32), comment='文件扩展名')
    upload_type: Mapped[str] = mapped_column(
        sa.String(32), comment='上传类型（file/avatar/resource/document/image/audio/video）'
    )
    size: Mapped[int] = mapped_column(sa.BigInteger, comment='文件大小（字节）')
    url_path: Mapped[str] = mapped_column(sa.String(512), comment='URL 路径')
    mime_type: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='MIME 类型')
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey('sys_user.id', ondelete='SET NULL'), default=None, comment='上传用户 ID'
    )
    retention_policy: Mapped[str] = mapped_column(
        sa.String(16), default='persistent', server_default='persistent', comment='保留策略（temporary/persistent）'
    )
    unreferenced_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='最后失去引用的时间')
