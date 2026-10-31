from typing import Annotated, Literal

from fastapi import APIRouter, Header, Path, Query, Request, UploadFile
from fastapi.responses import FileResponse

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.files.enums import UploadType
from backend.plugin.files.schema.file import UploadFileDetail, UploadPrecheckDetail, UploadPrecheckParam
from backend.plugin.files.service.chunk_service import chunk_service
from backend.plugin.files.service.file_service import file_service

router = APIRouter()


@router.post('/upload/precheck', summary='分片上传预检与恢复', dependencies=[DependsJwtAuth])
async def precheck_upload(request: Request, param: UploadPrecheckParam) -> ResponseSchemaModel[UploadPrecheckDetail]:
    return response_base.success(data=await chunk_service.precheck(param=param, user_id=request.user.id))


@router.put('/upload/{upload_id}/chunks/{index}', summary='流式上传一个分片', dependencies=[DependsJwtAuth])
async def upload_chunk(
    request: Request,
    upload_id: Annotated[str, Path(pattern=r'^[a-f0-9]{64}$')],
    index: Annotated[int, Path(ge=0)],
    chunk_sha256: Annotated[str, Header(alias='X-Chunk-SHA256', pattern=r'^[a-f0-9]{64}$')],
) -> ResponseSchemaModel[None]:
    await chunk_service.upload_chunk(
        upload_id=upload_id, index=index, user_id=request.user.id, request=request, sha256=chunk_sha256
    )
    return response_base.success()


@router.post('/upload/{upload_id}/merge', summary='合并并校验文件', dependencies=[DependsJwtAuth])
async def merge_upload(
    request: Request, upload_id: Annotated[str, Path(pattern=r'^[a-f0-9]{64}$')]
) -> ResponseSchemaModel[UploadFileDetail]:
    return response_base.success(data=await chunk_service.merge(upload_id=upload_id, user_id=request.user.id))


@router.delete('/upload/{upload_id}', summary='取消上传并清理分片', dependencies=[DependsJwtAuth])
async def cancel_upload(
    request: Request, upload_id: Annotated[str, Path(pattern=r'^[a-f0-9]{64}$')]
) -> ResponseSchemaModel[None]:
    await chunk_service.cancel(upload_id=upload_id, user_id=request.user.id)
    return response_base.success()


@router.post(
    '/upload',
    summary='统一文件上传',
    dependencies=[DependsJwtAuth],
)
async def upload_file(
    db: CurrentSessionTransaction,
    request: Request,
    file: UploadFile,
    upload_type: UploadType = UploadType.file,
    target_path: Annotated[str | None, Query(max_length=200, description='resource 类型的安全相对子目录')] = None,
    *,
    is_public: Annotated[
        bool | None, Query(description='是否公开；不传时头像默认 true，其他类型默认 false，所有类型均支持显式设置')
    ] = None,
    retention_policy: Literal['temporary', 'persistent'] = 'temporary',
) -> ResponseSchemaModel[UploadFileDetail]:
    """
    统一文件上传接口

    - **file**: 上传文件
    - **upload_type**: 上传类型（file/avatar/resource/document/image/audio/video），默认 file
    - **target_path**: 仅 resource 使用的相对子目录；拒绝绝对路径、..、反斜杠和编码路径
    - **is_public**: 不传时仅头像默认公开，其他类型默认私有；所有类型均可显式设为 true 或 false
    - 返回 **file_id** 和 **download_url**；公开文件任何人均可下载，私有文件仅登录后的上传者可下载
    - 公开头像和图片额外提供静态展示地址，其他类型通过下载接口获取
    """
    data = await file_service.upload(
        db=db,
        file=file,
        upload_type=upload_type,
        target_path=target_path,
        user_id=request.user.id,
        is_public=is_public,
        retention_policy=retention_policy,
    )
    return response_base.success(data=data)


@router.head('/download/{file_id}', response_class=FileResponse, include_in_schema=False)
@router.get(
    '/download/{file_id}',
    summary='统一文件下载',
    response_class=FileResponse,
    responses={
        206: {'description': 'Range 部分内容'},
        416: {'description': 'Range 超出文件范围'},
        404: {'description': '文件不存在或无权访问'},
    },
)
async def download_file(
    db: CurrentSession,
    request: Request,
    file_id: Annotated[int, Path(gt=0, description='上传响应中的文件 ID')],
) -> FileResponse:
    """公开文件允许匿名下载；私有文件仅上传者可下载，无权访问和文件不存在统一返回 404"""
    user_id = getattr(request.scope.get('user'), 'id', None)
    return await file_service.download(db=db, file_id=file_id, user_id=user_id)
