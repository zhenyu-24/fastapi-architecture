from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.notice.schema.user_notice import GetUserNoticeStatusDetail
from backend.plugin.notice.service.user_notice_service import user_notice_service

router = APIRouter()


@router.get(
    '/status',
    summary='获取当前用户通知公告状态',
    dependencies=[DependsJwtAuth],
)
async def get_user_notice_status(
    db: CurrentSession,
    request: Request,
) -> ResponseSchemaModel[list[GetUserNoticeStatusDetail]]:
    data = await user_notice_service.get_user_status(db=db, user_id=request.user.id)
    return response_base.success(data=data)


@router.post(
    '/read/{pk}',
    summary='标记通知公告为已读',
    dependencies=[DependsJwtAuth],
)
async def read_notice(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='通知公告 ID')],
) -> ResponseModel:
    await user_notice_service.read(db=db, user_id=request.user.id, notice_id=pk)
    return response_base.success()


@router.post(
    '/read-all',
    summary='全部标记为已读',
    dependencies=[DependsJwtAuth],
)
async def read_all_notices(
    db: CurrentSessionTransaction,
    request: Request,
    notice_ids: Annotated[str, Query(description='通知公告 ID 列表，逗号分隔')],
) -> ResponseModel:
    ids = [int(x) for x in notice_ids.split(',') if x]
    await user_notice_service.read_all(db=db, user_id=request.user.id, notice_ids=ids)
    return response_base.success()


@router.delete(
    '/{pk}',
    summary='用户删除通知公告',
    dependencies=[DependsJwtAuth],
)
async def delete_user_notice(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='通知公告 ID')],
) -> ResponseModel:
    await user_notice_service.delete(db=db, user_id=request.user.id, notice_id=pk)
    return response_base.success()


@router.delete(
    '',
    summary='清空用户通知公告',
    dependencies=[DependsJwtAuth],
)
async def clear_user_notices(
    db: CurrentSessionTransaction,
    request: Request,
    notice_ids: Annotated[str, Query(description='通知公告 ID 列表，逗号分隔')],
) -> ResponseModel:
    ids = [int(x) for x in notice_ids.split(',') if x]
    await user_notice_service.clear(db=db, user_id=request.user.id, notice_ids=ids)
    return response_base.success()
