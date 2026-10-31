from datetime import datetime

from pydantic import ConfigDict, Field, field_serializer

from backend.common.schema import SchemaBase


class UserNoticeSchemaBase(SchemaBase):
    """用户通知公告关系基础模型"""

    user_id: int = Field(description='用户ID')
    notice_id: int = Field(description='通知公告ID')
    is_read: bool = Field(False, description='是否已读')


class CreateUserNoticeParam(SchemaBase):
    """创建用户通知公告关系参数"""

    user_id: int = Field(description='用户ID')
    notice_id: int = Field(description='通知公告ID')
    is_read: bool = Field(False, description='是否已读')


class GetUserNoticeDetail(UserNoticeSchemaBase):
    """用户通知公告详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='用户通知公告关系 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class GetUserNoticeStatusDetail(SchemaBase):
    """用户通知公告状态详情（精简返回，仅用于通知栏）"""

    model_config = ConfigDict(from_attributes=True)

    notice_id: int = Field(description='通知公告ID')
    is_read: bool = Field(description='是否已读')
    deleted: int = Field(0, description='是否已删除（0：否；id：是）')

    @field_serializer('notice_id')
    def serialize_notice_id(self, value: int) -> str:
        """序列化时把雪花 ID 转成字符串，避免 JS 精度丢失"""
        return str(value)
