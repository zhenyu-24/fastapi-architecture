import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class FileRecord(DataClassBase):
    """文件记录表"""

    __tablename__ = 'sys_file_record'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(256), comment='文件名')
    extension: Mapped[str] = mapped_column(sa.String(32), comment='文件扩展名')
    sub_dir: Mapped[str] = mapped_column(sa.String(32), comment='子目录（document/image/video）')
    size: Mapped[int] = mapped_column(comment='文件大小（字节）')
    url_path: Mapped[str] = mapped_column(sa.String(512), comment='URL 路径')
    user_id: Mapped[int | None] = mapped_column(sa.BigInteger, sa.ForeignKey('sys_user.id', ondelete='SET NULL'), comment='上传用户 ID')
