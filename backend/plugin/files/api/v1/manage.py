from typing import Annotated

from fastapi import APIRouter, Path, Query, Request
from fastapi.responses import FileResponse

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsSuperUser
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.files.enums import UploadType
from backend.plugin.files.schema.file import (
    FileBatchDeleteParam,
    FileBrowseDetail,
    FileReplacementParam,
    FileVisibilityParam,
    ManagedFileDetail,
)
from backend.plugin.files.service.file_service import file_service
from backend.plugin.files.service.manage_service import file_manage_service

router = APIRouter(dependencies=[DependsSuperUser])


@router.get('', summary='管理员文件列表', dependencies=[DependsPagination])
async def get_files(
    db: CurrentSession,
    *,
    name: Annotated[str | None, Query(max_length=256)] = None,
    upload_type: UploadType | None = None,
    is_public: bool | None = None,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    username: Annotated[str | None, Query(max_length=64)] = None,
) -> ResponseSchemaModel[PageData[ManagedFileDetail]]:
    data = await file_manage_service.get_list(
        db=db, name=name, upload_type=upload_type, is_public=is_public, user_id=user_id, username=username
    )
    return response_base.success(data=data)


@router.get('/resource-folders', summary='资源上传可选目录')
async def resource_folders(db: CurrentSession, *, is_public: bool = False) -> ResponseSchemaModel[list[str]]:
    return response_base.success(data=await file_manage_service.resource_folders(db=db, is_public=is_public))


@router.get('/browse', summary='浏览文件目录', dependencies=[DependsPagination])
async def browse_files(
    db: CurrentSession,
    *,
    path: Annotated[str, Query(max_length=240)] = '',
    name: Annotated[str | None, Query(max_length=256)] = None,
    username: Annotated[str | None, Query(max_length=64)] = None,
    upload_type: UploadType | None = None,
    is_public: bool | None = None,
    recursive: bool = False,
) -> ResponseSchemaModel[FileBrowseDetail]:
    return response_base.success(
        data=await file_manage_service.browse(
            db=db,
            path=path,
            name=name,
            username=username,
            upload_type=upload_type,
            is_public=is_public,
            recursive=recursive,
        )
    )


@router.post('/batch-delete', summary='批量删除文件并返回逐项结果')
async def delete_files(db: CurrentSessionTransaction, obj: FileBatchDeleteParam) -> ResponseSchemaModel[dict]:
    return response_base.success(data=await file_manage_service.delete_batch(db=db, ids=obj.ids))


@router.patch('/{file_id}/visibility', summary='修改文件可见性')
async def update_visibility(
    db: CurrentSessionTransaction, file_id: Annotated[int, Path(gt=0)], obj: FileVisibilityParam
) -> ResponseSchemaModel[ManagedFileDetail]:
    return response_base.success(
        data=await file_manage_service.set_visibility(db=db, file_id=file_id, is_public=obj.is_public)
    )


@router.put('/{file_id}/content', summary='替换文件内容并保留访问地址')
async def replace_file(
    request: Request,
    db: CurrentSessionTransaction,
    file_id: Annotated[int, Path(gt=0)],
    obj: FileReplacementParam,
) -> ResponseSchemaModel[ManagedFileDetail]:
    return response_base.success(
        data=await file_manage_service.replace(
            db=db,
            file_id=file_id,
            source_file_id=obj.source_file_id,
            user_id=request.user.id,
        )
    )


@router.get('/{file_id}', summary='管理员文件详情')
async def get_file(db: CurrentSession, file_id: Annotated[int, Path(gt=0)]) -> ResponseSchemaModel[ManagedFileDetail]:
    return response_base.success(data=await file_manage_service.get(db=db, file_id=file_id))


@router.head('/{file_id}/download', response_class=FileResponse, include_in_schema=False)
@router.get('/{file_id}/download', summary='管理员下载文件', response_class=FileResponse)
async def download_file(db: CurrentSession, file_id: Annotated[int, Path(gt=0)]) -> FileResponse:
    return await file_service.download(db=db, file_id=file_id, managed=True)


@router.delete('/{file_id}', summary='管理员永久删除文件及记录')
async def delete_file(db: CurrentSessionTransaction, file_id: Annotated[int, Path(gt=0)]) -> ResponseModel:
    await file_manage_service.delete(db=db, file_id=file_id)
    return response_base.success()
