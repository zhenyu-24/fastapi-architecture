from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsSuperUser
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.opensandbox.schema.sandbox import (
    AdminOverview,
    CommandLogDetail,
    CreateSandboxParam,
    RenameSandboxParam,
    SandboxInfo,
    SandboxRenewParam,
    ServiceActionResult,
    UserOption,
)
from backend.plugin.opensandbox.service.command_service import command_service
from backend.plugin.opensandbox.service.control_service import service_control_service
from backend.plugin.opensandbox.service.sandbox_service import sandbox_service

router = APIRouter(prefix='/opensandbox/admin', tags=['OpenSandbox 管理'], dependencies=[DependsSuperUser])


def _identity(request: Request) -> tuple[int, str, bool]:
    return int(request.user.id), request.user.username, True


@router.get('/overview', summary='OpenSandbox 管理概览')
async def get_admin_overview(db: CurrentSession) -> ResponseSchemaModel[AdminOverview]:
    return response_base.success(data=await sandbox_service.admin_overview(db=db))


@router.get('/sandboxes', summary='分页获取全部沙盒', dependencies=[DependsPagination])
async def get_admin_sandboxes(
    db: CurrentSession,
    user_id: Annotated[int | None, Query(description='归属用户 ID')] = None,
    username: Annotated[str | None, Query(description='归属用户名')] = None,
    status: Annotated[str | None, Query(description='状态')] = None,
    keyword: Annotated[str | None, Query(description='沙盒名称关键词')] = None,
) -> ResponseSchemaModel[PageData[SandboxInfo]]:
    data = await sandbox_service.list_admin(db=db, user_id=user_id, username=username, status=status, keyword=keyword)
    return response_base.success(data=data)


@router.post('/sandboxes', summary='管理员为指定用户创建沙盒')
async def create_admin_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    obj: CreateSandboxParam,
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, _ = _identity(request)
    data = await sandbox_service.create(
        db=db,
        current_user_id=user_id,
        current_username=username,
        is_admin=True,
        obj=obj,
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/pause', summary='管理员暂停沙盒')
async def pause_admin_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, _ = _identity(request)
    data = await sandbox_service.action(
        db=db, sandbox_id=sandbox_id, action='pause', user_id=user_id, is_admin=True, username=username
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/resume', summary='管理员恢复沙盒')
async def resume_admin_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, _ = _identity(request)
    data = await sandbox_service.action(
        db=db, sandbox_id=sandbox_id, action='resume', user_id=user_id, is_admin=True, username=username
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/rename', summary='管理员重命名沙盒')
async def rename_admin_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: RenameSandboxParam,
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, _ = _identity(request)
    data = await sandbox_service.rename(
        db=db,
        sandbox_id=sandbox_id,
        name=obj.name,
        user_id=user_id,
        is_admin=True,
        username=username,
    )
    return response_base.success(data=data)


@router.post('/sandboxes/{sandbox_id}/restart', summary='管理员重启沙盒')
async def restart_admin_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, _ = _identity(request)
    data = await sandbox_service.action(
        db=db,
        sandbox_id=sandbox_id,
        action='restart',
        user_id=user_id,
        is_admin=True,
        username=username,
    )
    return response_base.success(data=data)


@router.delete('/sandboxes/{sandbox_id}', summary='管理员删除沙盒')
async def delete_admin_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
) -> ResponseModel:
    user_id, username, _ = _identity(request)
    await sandbox_service.action(
        db=db, sandbox_id=sandbox_id, action='delete', user_id=user_id, is_admin=True, username=username
    )
    return response_base.success()


@router.post('/sandboxes/{sandbox_id}/renew', summary='管理员续期沙盒')
async def renew_admin_sandbox(
    request: Request,
    db: CurrentSessionTransaction,
    sandbox_id: Annotated[str, Path(description='沙盒 ID')],
    obj: SandboxRenewParam,
) -> ResponseSchemaModel[SandboxInfo]:
    user_id, username, _ = _identity(request)
    data = await sandbox_service.renew(
        db=db, sandbox_id=sandbox_id, minutes=obj.minutes, user_id=user_id, is_admin=True, username=username
    )
    return response_base.success(data=data)


@router.post('/sync', summary='同步 OpenSandbox 沙盒到本地')
async def sync_admin_sandboxes(db: CurrentSessionTransaction) -> ResponseSchemaModel[int]:
    count = await sandbox_service.sync_remote(db)
    return response_base.success(data=count)


@router.get('/users', summary='获取用户选项')
async def get_admin_users(db: CurrentSession) -> ResponseSchemaModel[list[UserOption]]:
    return response_base.success(data=await sandbox_service.list_users(db=db))


@router.get('/commands', summary='分页查询全部命令审计', dependencies=[DependsPagination])
async def get_admin_commands(
    db: CurrentSession,
    user_id: Annotated[int | None, Query(description='用户 ID')] = None,
    username: Annotated[str | None, Query(description='用户名')] = None,
    sandbox_id: Annotated[str | None, Query(description='沙盒 ID')] = None,
    keyword: Annotated[str | None, Query(description='命令关键词')] = None,
    status: Annotated[str | None, Query(description='执行状态')] = None,
    start_time: Annotated[datetime | None, Query(description='开始时间')] = None,
    end_time: Annotated[datetime | None, Query(description='结束时间')] = None,
) -> ResponseSchemaModel[PageData[CommandLogDetail]]:
    data = await command_service.list_logs(
        db=db,
        user_id=user_id,
        username=username,
        sandbox_id=sandbox_id,
        keyword=keyword,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    return response_base.success(data=data)


@router.get('/commands/{pk}', summary='获取命令审计详情')
async def get_admin_command(
    db: CurrentSession,
    pk: Annotated[int, Path(description='日志 ID')],
) -> ResponseSchemaModel[CommandLogDetail]:
    return response_base.success(data=await command_service.get_log(db=db, pk=pk))


@router.post('/service/start', summary='启用沙盒 API')
async def start_service(db: CurrentSessionTransaction) -> ResponseSchemaModel[ServiceActionResult]:
    return response_base.success(data=await service_control_service.start(db))


@router.post('/service/stop', summary='暂停沙盒 API')
async def stop_service(db: CurrentSessionTransaction) -> ResponseSchemaModel[ServiceActionResult]:
    return response_base.success(data=await service_control_service.stop(db))
