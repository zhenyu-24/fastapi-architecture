import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key


class CommandLog(Base):
    """OpenSandbox 命令执行审计日志"""

    __tablename__ = 'sys_opensandbox_command'
    __table_args__ = {'comment': 'OpenSandbox 命令执行审计日志'}

    id: Mapped[id_key] = mapped_column(init=False)
    sandbox_id: Mapped[str] = mapped_column(sa.String(64), index=True, comment='沙盒 ID')
    sandbox_name: Mapped[str] = mapped_column(sa.String(128), comment='沙盒名称')
    user_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='执行用户 ID')
    username: Mapped[str] = mapped_column(sa.String(64), index=True, comment='执行用户名')
    source: Mapped[str] = mapped_column(sa.String(16), index=True, comment='来源：terminal/code/file')
    command: Mapped[str] = mapped_column(UniversalText, comment='执行的命令')
    session_id: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='Bash 会话 ID')
    cwd: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='工作目录')
    stdout: Mapped[str] = mapped_column(UniversalText, default='', comment='标准输出')
    stderr: Mapped[str] = mapped_column(UniversalText, default='', comment='标准错误')
    exit_code: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='退出码')
    status: Mapped[str] = mapped_column(sa.String(16), default='success', index=True, comment='执行状态')
    duration_ms: Mapped[int] = mapped_column(sa.Integer, default=0, comment='耗时毫秒')
    truncated: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='输出是否被截断')
