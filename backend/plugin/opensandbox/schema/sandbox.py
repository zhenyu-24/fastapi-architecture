from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class SandboxServiceStatus(SchemaBase):
    """OpenSandbox 服务状态"""

    configured: bool = Field(description='是否配置了 OpenSandbox')
    api_enabled: bool = Field(description='管理员是否启用了沙盒 API')
    server_available: bool = Field(description='OpenSandbox Server 进程是否可连通')
    available: bool = Field(description='沙盒 API 是否可用（API 已启用且 Server 可连通）')
    version: str | None = Field(None, description='服务端版本')
    url: str = Field(description='服务地址')
    api_key_configured: bool = Field(description='是否配置 API Key')
    start_command_configured: bool = Field(description='是否配置启动命令')
    stop_command_configured: bool = Field(description='是否配置停止命令')
    message: str = Field(description='状态说明')
    checked_time: datetime = Field(description='检查时间')


class SandboxOverview(SchemaBase):
    """用户工作台概览"""

    service: SandboxServiceStatus
    is_admin: bool = Field(description='是否管理员')
    max_sandboxes: int = Field(description='每个用户最大沙盒数')
    idle_timeout_seconds: int = Field(description='空闲暂停阈值')
    auto_pause_enabled: bool = Field(description='是否启用空闲自动暂停')
    default_image: str = Field(description='默认镜像')
    workspace_root: str = Field(description='工作区根目录')


class SandboxInfo(SchemaBase):
    """沙盒信息"""

    sandbox_id: str = Field(description='沙盒 ID')
    name: str = Field(description='沙盒名称')
    image: str = Field(description='镜像')
    state: str = Field(description='状态')
    reason: str | None = Field(None, description='状态原因')
    message: str | None = Field(None, description='状态说明')
    owner_id: int = Field(description='归属用户 ID')
    owner_username: str = Field(description='归属用户名')
    created_at: datetime | None = Field(None, description='创建时间')
    expires_at: datetime | None = Field(None, description='过期时间')
    last_activity_time: datetime | None = Field(None, description='最后活动时间')
    auto_paused: bool = Field(False, description='是否由空闲策略暂停')
    workspace_root: str = Field(description='工作区根目录')


class CreateSandboxParam(SchemaBase):
    """创建沙盒参数"""

    name: str = Field('', max_length=64, description='沙盒名称')
    image: str | None = Field(None, max_length=512, description='镜像，留空使用默认镜像')
    owner_id: int | None = Field(None, description='管理员为目标用户创建时的用户 ID')
    owner_username: str | None = Field(None, max_length=64, description='管理员为目标用户创建时的用户名')


class RenameSandboxParam(SchemaBase):
    """重命名沙盒参数"""

    name: str = Field(min_length=1, max_length=128, description='新的沙盒显示名称')


class SandboxRenewParam(SchemaBase):
    """沙盒续期参数"""

    minutes: int = Field(60, ge=1, le=10080, description='续期分钟数')


class RunCommandParam(SchemaBase):
    """执行命令参数"""

    command: str = Field(min_length=1, max_length=200000, description='命令')
    cwd: str | None = Field(None, max_length=512, description='工作目录')
    timeout_seconds: int = Field(60, ge=1, le=3600, description='执行超时秒数')
    source: Literal['terminal', 'code', 'file'] = Field('terminal', description='执行来源')
    session_id: str | None = Field(None, max_length=128, description='Bash 会话 ID')


class CommandResult(SchemaBase):
    """命令执行结果"""

    log_id: int | None = Field(None, description='审计日志 ID')
    command: str = Field(description='命令')
    cwd: str | None = Field(None, description='会话当前工作目录')
    stdout: str = Field(description='标准输出')
    stderr: str = Field(description='标准错误')
    exit_code: int | None = Field(None, description='退出码')
    status: str = Field(description='执行状态')
    duration_ms: int = Field(description='耗时毫秒')
    truncated: bool = Field(description='输出是否被截断')
    created_time: datetime = Field(description='执行时间')


class CreateSessionParam(SchemaBase):
    """创建终端会话参数"""

    cwd: str | None = Field(None, max_length=512, description='初始工作目录')


class TerminalSessionResult(SchemaBase):
    """终端会话"""

    session_id: str = Field(description='会话 ID')
    cwd: str = Field(description='初始工作目录')


class FileEntry(SchemaBase):
    """文件条目"""

    path: str = Field(description='完整路径')
    name: str = Field(description='文件名')
    type: Literal['file', 'directory'] = Field(description='类型')
    size: int = Field(0, description='字节数')
    mode: str | None = Field(None, description='权限')
    modified_at: datetime | None = Field(None, description='修改时间')


class TextFileResult(SchemaBase):
    """文本文件读取结果"""

    path: str = Field(description='文件路径')
    content: str = Field('', description='文本内容')
    size: int = Field(0, description='文件字节数')
    is_binary: bool = Field(False, description='是否二进制文件')
    truncated: bool = Field(False, description='是否截断')


class FileWriteParam(SchemaBase):
    """写入文本文件"""

    path: str = Field(min_length=1, max_length=1024, description='文件路径')
    content: str = Field('', description='文本内容')


class FileMkdirParam(SchemaBase):
    """创建目录"""

    path: str = Field(min_length=1, max_length=1024, description='目录路径')


class FileRenameParam(SchemaBase):
    """重命名或移动"""

    source: str = Field(min_length=1, max_length=1024, description='源路径')
    destination: str = Field(min_length=1, max_length=1024, description='目标路径')


class FileDeleteParam(SchemaBase):
    """删除文件或目录"""

    path: str = Field(min_length=1, max_length=1024, description='路径')


class CommandLogDetail(SchemaBase):
    """命令审计详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='日志 ID')
    sandbox_id: str = Field(description='沙盒 ID')
    sandbox_name: str = Field(description='沙盒名称')
    user_id: int = Field(description='用户 ID')
    username: str = Field(description='用户名')
    source: str = Field(description='来源')
    session_id: str | None = Field(None, description='Bash 会话 ID')
    command: str = Field(description='命令')
    cwd: str | None = Field(None, description='工作目录')
    stdout: str = Field(description='标准输出')
    stderr: str = Field(description='标准错误')
    exit_code: int | None = Field(None, description='退出码')
    status: str = Field(description='执行状态')
    duration_ms: int = Field(description='耗时毫秒')
    truncated: bool = Field(description='输出是否被截断')
    created_time: datetime = Field(description='执行时间')


class AdminOverview(SchemaBase):
    """管理员总览"""

    service: SandboxServiceStatus
    total_sandboxes: int = Field(description='沙盒总数')
    running_sandboxes: int = Field(description='运行中沙盒数')
    paused_sandboxes: int = Field(description='已暂停沙盒数')
    total_users: int = Field(description='有沙盒的用户数')
    total_commands: int = Field(description='命令日志总数')


class UserOption(SchemaBase):
    """用户选项"""

    id: int = Field(description='用户 ID')
    username: str = Field(description='用户名')
    nickname: str = Field(description='昵称')


class ServiceActionResult(SchemaBase):
    """服务控制结果"""

    success: bool = Field(description='操作是否成功')
    output: str = Field(description='操作说明或错误信息')
    status: SandboxServiceStatus = Field(description='执行后的服务状态')


class SandboxRecordCreate(SchemaBase):
    """同步沙盒记录参数"""

    sandbox_id: str = Field(description='沙盒 ID')
    name: str = Field(description='名称')
    image: str = Field(description='镜像')
    user_id: int = Field(description='用户 ID')
    username: str = Field(description='用户名')
    status: str = Field('Pending', description='状态')
    last_activity_time: datetime | None = Field(None, description='最后活动时间')
    expires_at: datetime | None = Field(None, description='过期时间')


class CommandLogCreate(SchemaBase):
    """写入命令审计参数"""

    sandbox_id: str = Field(description='沙盒 ID')
    sandbox_name: str = Field(description='沙盒名称')
    user_id: int = Field(description='用户 ID')
    username: str = Field(description='用户名')
    source: str = Field(description='来源')
    session_id: str | None = Field(None, description='会话 ID')
    command: str = Field(description='命令')
    cwd: str | None = Field(None, description='工作目录')
    stdout: str = Field('', description='标准输出')
    stderr: str = Field('', description='标准错误')
    exit_code: int | None = Field(None, description='退出码')
    status: str = Field('success', description='状态')
    duration_ms: int = Field(0, description='耗时毫秒')
    truncated: bool = Field(False, description='是否截断')
