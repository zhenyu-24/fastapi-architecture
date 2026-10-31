from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, File, Path, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from backend.common.exception import errors
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.core.conf import settings
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.opensandbox.schema.sandbox import (
    CommandResult,
    CreateSandboxParam,
    CreateSessionParam,
    FileDeleteParam,
    FileEntry,
    FileMkdirParam,
    FileRenameParam,
    FileWriteParam,
    RenameSandboxParam,
    RunCommandParam,
    SandboxInfo,
    SandboxOverview,
    SandboxRenewParam,
    TerminalSessionResult,
    TextFileResult,
)
from backend.plugin.opensandbox.service.command_service import command_service
from backend.plugin.opensandbox.service.file_service import file_service
from backend.plugin.opensandbox.service.sandbox_service import sandbox_service
from backend.plugin.opensandbox.utils.client import open_sandbox_client
from backend.plugin.opensandbox.utils.dynamic_config import load_sandbox_config

router = APIRouter(prefix='/opensandbox', tags=['沙盒工作台'])


def _identity(request: Request) -> tuple[int, str, bool]:
    return int(request.user.id), request.user.username, bool(request.user.is_superuser)


@router.get('/overview', summary='获取 OpenSandbox 概览', dependencies=[DependsJwtAuth])
async def get_overview(request: Request, db: CurrentSession) -> ResponseSchemaModel[SandboxOverview]:
    _, _, is_admin = _identity(request)
    return response_base.success(data=await sandbox_service.overview(db=db, is_admin=is_admin))


@router.get('/sandboxes', summary='获取当前用户沙盒', dependencies=[DependsJwtAuth])
async def get_sandboxes(request: Request, db: CurrentSession) -> ResponseSchemaModel[list[SandboxInfo]]:
    user_id, username, _ = _identity(request)
    return response_base.success(data=await sandbox_service.list_user(db=db, user_id=user_id, username=username))


@router.post('/sandboxes', summary='创建沙盒', dependencies=[DependsJwtAuth])
async def create_sandbox(
    request: Request, db: CurrentSessionTransaction, obj: CreateSandboxParam
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, is_admin = _identity(request)
    data = await sandbox_service.create(
        db=db,
        current_user_id=user_id,
        current_username=username,
        is_admin=is_admin,
        obj=obj,
    )
    return response_base.success(data=data)


@router.get('/sandboxes/{sandbox_id}', summary='获取沙盒状态', dependencies=[DependsJwtAuth])
async def get_sandbox(
    request: Request,
    db: CurrentSession,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, is_admin = _identity(request)
    data = await sandbox_service.get_info(
        db=db, sandbox_id=sandbox_id, user_id=user_id, is_admin=is_admin, username=username
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/pause', summary='暂停沙盒', dependencies=[DependsJwtAuth])
async def pause_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, is_admin = _identity(request)
    data = await sandbox_service.action(
        db=db, sandbox_id=sandbox_id, action='pause', user_id=user_id, is_admin=is_admin, username=username
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/resume', summary='恢复沙盒', dependencies=[DependsJwtAuth])
async def resume_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, is_admin = _identity(request)
    data = await sandbox_service.action(
        db=db, sandbox_id=sandbox_id, action='resume', user_id=user_id, is_admin=is_admin, username=username
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/rename', summary='重命名沙盒', dependencies=[DependsJwtAuth])
async def rename_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: RenameSandboxParam,
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, is_admin = _identity(request)
    data = await sandbox_service.rename(
        db=db,
        sandbox_id=sandbox_id,
        name=obj.name,
        user_id=user_id,
        is_admin=is_admin,
        username=username,
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/restart', summary='重启沙盒', dependencies=[DependsJwtAuth])
async def restart_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, is_admin = _identity(request)
    data = await sandbox_service.action(
        db=db,
        sandbox_id=sandbox_id,
        action='restart',
        user_id=user_id,
        is_admin=is_admin,
        username=username,
    )
    return response_base.success(data=data)


@router.delete('/sandboxes/{sandbox_id}', summary='删除沙盒', dependencies=[DependsJwtAuth])
async def delete_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseModel:
    user_id, username, is_admin = _identity(request)
    await sandbox_service.action(
        db=db, sandbox_id=sandbox_id, action='delete', user_id=user_id, is_admin=is_admin, username=username
    )
    return response_base.success()


@router.post('/sandboxes/{sandbox_id}/renew', summary='续期沙盒', dependencies=[DependsJwtAuth])
async def renew_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: SandboxRenewParam,
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, is_admin = _identity(request)
    data = await sandbox_service.renew(
        db=db, sandbox_id=sandbox_id, minutes=obj.minutes, user_id=user_id, is_admin=is_admin, username=username
    )
    return response_base.success(data=data)


@router.get('/sandboxes/{sandbox_id}/files', summary='列出目录', dependencies=[DependsJwtAuth])
async def list_files(
    request: Request,
    db: CurrentSession,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    path: Annotated[str | None, Query(description='目录路径')] = None,
) -> ResponseSchemaModel[list[FileEntry]]:
    user_id, username, is_admin = _identity(request)
    data = await file_service.list(
        db=db, sandbox_id=sandbox_id, path=path, user_id=user_id, username=username, is_admin=is_admin
    )
    return response_base.success(data=data)


@router.get('/sandboxes/{sandbox_id}/file', summary='读取文件', dependencies=[DependsJwtAuth])
async def read_file(
    request: Request,
    db: CurrentSession,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    path: Annotated[str, Query(description='文件路径')],
) -> ResponseSchemaModel[TextFileResult]:
    user_id, username, is_admin = _identity(request)
    data = await file_service.read(
        db=db, sandbox_id=sandbox_id, path=path, user_id=user_id, username=username, is_admin=is_admin
    )
    return response_base.success(data=data)


@router.put('/sandboxes/{sandbox_id}/file', summary='保存文件', dependencies=[DependsJwtAuth])
async def write_file(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: FileWriteParam,
) -> ResponseModel:
    user_id, username, is_admin = _identity(request)
    await file_service.write(
        db=db, sandbox_id=sandbox_id, obj=obj, user_id=user_id, username=username, is_admin=is_admin
    )
    return response_base.success()


@router.post('/sandboxes/{sandbox_id}/file/mkdir', summary='创建目录', dependencies=[DependsJwtAuth])
async def mkdir(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: FileMkdirParam,
) -> ResponseModel:
    user_id, username, is_admin = _identity(request)
    await file_service.mkdir(
        db=db, sandbox_id=sandbox_id, obj=obj, user_id=user_id, username=username, is_admin=is_admin
    )
    return response_base.success()


@router.post('/sandboxes/{sandbox_id}/file/rename', summary='重命名文件或目录', dependencies=[DependsJwtAuth])
async def rename_file(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: FileRenameParam,
) -> ResponseModel:
    user_id, username, is_admin = _identity(request)
    await file_service.rename(
        db=db, sandbox_id=sandbox_id, obj=obj, user_id=user_id, username=username, is_admin=is_admin
    )
    return response_base.success()


@router.post('/sandboxes/{sandbox_id}/file/delete', summary='删除文件或目录', dependencies=[DependsJwtAuth])
async def delete_file(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: FileDeleteParam,
) -> ResponseModel:
    user_id, username, is_admin = _identity(request)
    await file_service.delete(
        db=db, sandbox_id=sandbox_id, obj=obj, user_id=user_id, username=username, is_admin=is_admin
    )
    return response_base.success()


@router.post('/sandboxes/{sandbox_id}/file/upload', summary='上传文件', dependencies=[DependsJwtAuth])
async def upload_file(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    file: Annotated[UploadFile, File(description='文件')],
    path: Annotated[str | None, Query(description='目标目录')] = None,
) -> ResponseSchemaModel[str]:
    user_id, username, is_admin = _identity(request)
    await load_sandbox_config(db)
    limit = settings.OPEN_SANDBOX_UPLOAD_LIMIT_BYTES
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise errors.RequestError(msg='上传文件超过大小限制')
    target = await file_service.upload(
        db=db,
        sandbox_id=sandbox_id,
        path=path or settings.OPEN_SANDBOX_WORKSPACE_ROOT,
        filename=file.filename or 'upload.bin',
        data=data,
        user_id=user_id,
        username=username,
        is_admin=is_admin,
    )
    return response_base.success(data=target)


@router.get('/sandboxes/{sandbox_id}/file/download', summary='下载文件', dependencies=[DependsJwtAuth])
async def download_file(
    request: Request,
    db: CurrentSession,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    path: Annotated[str, Query(description='文件路径')],
) -> StreamingResponse:
    user_id, username, is_admin = _identity(request)
    target, filename = await file_service.download_name(
        db=db, sandbox_id=sandbox_id, path=path, user_id=user_id, username=username, is_admin=is_admin
    )

    async def iterator() -> AsyncIterator[bytes]:
        async with open_sandbox_client.download_stream(sandbox_id, target) as stream:
            async for chunk in stream:
                yield chunk

    return StreamingResponse(
        iterator(),
        media_type='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post('/sandboxes/{sandbox_id}/execute', summary='执行命令', dependencies=[DependsJwtAuth])
async def execute_command(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: RunCommandParam,
) -> ResponseSchemaModel[CommandResult]:
    user_id, username, is_admin = _identity(request)
    data = await command_service.execute(
        db=db, sandbox_id=sandbox_id, obj=obj, user_id=user_id, username=username, is_admin=is_admin
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/sessions', summary='创建终端会话', dependencies=[DependsJwtAuth])
async def create_session(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: CreateSessionParam,
) -> ResponseSchemaModel[TerminalSessionResult]:
    user_id, username, is_admin = _identity(request)
    data = await command_service.create_session(
        db=db, sandbox_id=sandbox_id, obj=obj, user_id=user_id, username=username, is_admin=is_admin
    )
    return response_base.success(data=data)


@router.delete('/sandboxes/{sandbox_id}/sessions/{session_id}', summary='关闭终端会话', dependencies=[DependsJwtAuth])
async def delete_session(
    request: Request,
    db: CurrentSession,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    session_id: Annotated[str, Path(description='会话 ID')],
) -> ResponseModel:
    user_id, username, is_admin = _identity(request)
    await sandbox_service.ensure_access(
        db=db, sandbox_id=sandbox_id, user_id=user_id, is_admin=is_admin, username=username
    )
    await command_service.delete_session(sandbox_id=sandbox_id, session_id=session_id)
    return response_base.success()
