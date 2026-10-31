from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer

from backend.plugin.files.enums import UploadType


class UploadFileDetail(BaseModel):
    """上传文件响应"""

    url: str
    size: int
    original_name: str
    upload_type: str
    extension: str
    file_id: int | None = None
    download_url: str
    is_public: bool
    created_time: datetime | None = None

    @field_serializer('file_id')
    def serialize_file_id(self, value: int | None) -> str | None:
        """避免浏览器处理雪花 ID 时丢失整数精度"""
        return str(value) if value is not None else None


class UploadPrecheckParam(BaseModel):
    filename: str = Field(min_length=1, max_length=240, description='原始文件名')
    size: int = Field(gt=0, le=2**53 - 1, description='文件字节数，不超过 JavaScript 安全整数上限')
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$', description='完整文件 SHA-256')
    content_type: str = Field(default='application/octet-stream', max_length=128)
    upload_type: UploadType = UploadType.file
    target_path: str | None = Field(default=None, max_length=200)
    is_public: bool | None = None
    retention_policy: Literal['temporary', 'persistent'] = 'temporary'


class UploadPrecheckDetail(BaseModel):
    upload_id: str
    chunk_size: int
    total_chunks: int
    uploaded_chunks: list[int]
    file: UploadFileDetail | None = None


class ManagedFileDetail(UploadFileDetail):
    """管理员文件信息，包含归属和实际存储状态"""

    name: str
    url_path: str
    mime_type: str | None
    user_id: str | None
    exists: bool
    owner_uses_avatar: bool
    username: str | None = None
    storage_path: str = ''
    retention_policy: str = 'persistent'
    unreferenced_at: datetime | None = None
    references: list[dict[str, str]] = Field(default_factory=list)


class FileFolder(BaseModel):
    name: str
    path: str
    count: int


class FileReplacementParam(BaseModel):
    source_file_id: int = Field(gt=0)


class FileVisibilityParam(BaseModel):
    is_public: bool


class FileBatchDeleteParam(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)


class FileBrowseDetail(BaseModel):
    path: str
    folders: list[FileFolder]
    files: dict
