from fastapi import APIRouter, Depends, Request

from backend.common.exception import errors
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.external_links.schema.external_link import ExternalLinkParam, GetExternalLinkDetail
from backend.plugin.external_links.service.external_link_service import external_link_service

router = APIRouter()


def require_manager(request: Request, _token: str = DependsJwtAuth) -> None:
    """与前端系统管理入口保持一致，只允许超级管理员配置"""
    if not request.user.is_superuser:
        raise errors.AuthorizationError(msg='仅超级管理员可以配置外部页面')


@router.get('', summary='获取已发布的外部页面', dependencies=[DependsJwtAuth])
async def get_external_pages(db: CurrentSession) -> ResponseSchemaModel[list[GetExternalLinkDetail]]:
    rows = await external_link_service.get_all(db=db, published=True)
    return response_base.success(data=rows)


@router.get('/manage', summary='获取全部外部页面配置', dependencies=[Depends(require_manager)])
async def get_external_page_settings(db: CurrentSession) -> ResponseSchemaModel[list[GetExternalLinkDetail]]:
    rows = await external_link_service.get_all(db=db)
    return response_base.success(data=rows)


@router.post('', summary='新增外部页面或分类', dependencies=[Depends(require_manager)])
async def create_external_page(
    db: CurrentSessionTransaction, obj: ExternalLinkParam
) -> ResponseSchemaModel[GetExternalLinkDetail]:
    row = await external_link_service.save(db=db, obj=obj)
    return response_base.success(data=row)


@router.put('/{pk}', summary='修改外部页面或分类', dependencies=[Depends(require_manager)])
async def update_external_page(
    db: CurrentSessionTransaction, pk: int, obj: ExternalLinkParam
) -> ResponseSchemaModel[GetExternalLinkDetail]:
    row = await external_link_service.save(db=db, obj=obj, pk=pk)
    return response_base.success(data=row)


@router.delete('/{pk}', summary='删除外部页面或空分类', dependencies=[Depends(require_manager)])
async def delete_external_page(db: CurrentSessionTransaction, pk: int) -> ResponseModel:
    await external_link_service.delete(db=db, pk=pk)
    return response_base.success()
