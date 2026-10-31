from backend.common.enums import StrEnum
from backend.core.conf import settings


class UploadType(StrEnum):
    """上传类型枚举"""

    file = 'file'
    avatar = 'avatar'
    resource = 'resource'
    document = 'document'
    image = 'image'
    audio = 'audio'
    video = 'video'


# 各上传类型允许的文件扩展名
UPLOAD_TYPE_EXTENSIONS: dict[UploadType, list[str]] = {
    UploadType.file: [],  # 使用全局白名单
    UploadType.avatar: ['jpg', 'jpeg', 'png', 'gif', 'webp'],
    UploadType.resource: [],  # 使用全局白名单
    UploadType.document: [
        'txt',
        'md',
        'markdown',
        'mdx',
        'pdf',
        'html',
        'xlsx',
        'xls',
        'vtt',
        'properties',
        'doc',
        'docx',
        'csv',
        'eml',
        'msg',
        'pptx',
        'ppt',
        'xml',
        'epub',
        'json',
        'yaml',
        'yml',
        'css',
        'js',
        'py',
        'java',
    ],
    UploadType.image: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico'],
    UploadType.audio: ['mp3', 'wav', 'ogg', 'flac', 'aac', 'wma', 'm4a'],
    UploadType.video: ['mp4', 'mov', 'avi', 'flv', 'wmv', 'mkv', 'webm', 'm4v'],
}

# 所有上传入口共用环境配置，禁止用 0 绕过限制
UPLOAD_TYPE_SIZE_LIMITS = settings.FILE_UPLOAD_SIZE_LIMITS
