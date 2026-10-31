import codecs

from pathlib import Path
from typing import BinaryIO
from zipfile import BadZipFile, ZipFile

import filetype

from backend.common.exception import errors
from backend.core.conf import settings

TEXT_EXTENSIONS = {'txt', 'md', 'csv', 'json', 'yaml', 'yml', 'xml', 'html', 'css', 'js', 'py', 'java'}
OFFICE_MEMBERS = {'docx': 'word/document.xml', 'xlsx': 'xl/workbook.xml', 'pptx': 'ppt/presentation.xml'}


def validate_text(source: BinaryIO) -> None:
    decoder = codecs.getincrementaldecoder('utf-8-sig')()
    try:
        while block := source.read(settings.UPLOAD_READ_SIZE):
            text = decoder.decode(block)
            if any(ord(char) < 32 and char not in '\t\n\r\f' for char in text):
                raise errors.RequestError(msg='文本文件包含二进制内容')
        decoder.decode(b'', final=True)
    except UnicodeDecodeError:
        raise errors.RequestError(msg='文本文件必须使用 UTF-8 编码') from None


def validate_content(path: Path, extension: str, declared_type: str | None) -> str:
    """对磁盘文件检查 magic number；文本及 Office 容器采用明确的补充校验"""
    allowed = settings.FILE_UPLOAD_ALLOWED_TYPES.get(extension, [])
    declared = (declared_type or '').split(';', 1)[0].strip().lower()
    if not allowed or declared not in {'', 'application/octet-stream', *allowed}:
        raise errors.RequestError(msg='文件 Content-Type 不在白名单中')
    with path.open('rb') as source:
        header = source.read(8192)
        detected = filetype.guess(header)
        if extension in OFFICE_MEMBERS:
            if detected is None or detected.mime not in {'application/zip', *allowed}:
                raise errors.RequestError(msg='Office 文件头与扩展名不匹配')
            try:
                with ZipFile(source) as archive:
                    members = set(archive.namelist())
                    if OFFICE_MEMBERS[extension] not in members or '[Content_Types].xml' not in members:
                        raise errors.RequestError(msg='Office 文件内容与扩展名不匹配')
                    if any(name.lower().endswith('vbaproject.bin') for name in members):
                        raise errors.RequestError(msg='不允许上传包含宏的 Office 文件')
            except BadZipFile:
                raise errors.RequestError(msg='无效的 Office 文件') from None
            return allowed[0]
        if extension in TEXT_EXTENSIONS and detected is None:
            source.seek(0)
            validate_text(source)
            return declared if declared in allowed else allowed[0]
    if detected is None or detected.mime not in allowed:
        raise errors.RequestError(msg='文件头检测结果与扩展名或 MIME 白名单不匹配')
    return detected.mime
