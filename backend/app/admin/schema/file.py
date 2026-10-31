from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class CreateFileParam(SchemaBase):
    """创建文件记录参数"""

    name: str = Field(description='文件名')
    extension: str = Field(description='文件扩展名')
    sub_dir: str = Field(description='子目录')
    size: int = Field(description='文件大小（字节）')
    url_path: str = Field(description='URL 路径')


class GetFileRecord(SchemaBase):
    """文件记录详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='文件 ID')
    name: str = Field(description='文件名')
    extension: str = Field(description='文件扩展名')
    sub_dir: str = Field(description='子目录')
    size: int = Field(description='文件大小（字节）')
    url_path: str = Field(description='URL 路径')
    created_time: datetime = Field(description='创建时间')
