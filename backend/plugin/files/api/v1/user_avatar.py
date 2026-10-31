from fastapi import APIRouter, Request, UploadFile

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSessionTransaction
from backend.plugin.files.enums import UploadType
from backend.plugin.files.schema.file import UploadFileDetail
from backend.plugin.files.service.file_service import file_service

router = APIRouter()


@router.post(
    '/me/avatar',
    summary='上传当前用户头像',
    dependencies=[DependsJwtAuth],
)
async def upload_my_avatar(
    db: CurrentSessionTransaction,
    request: Request,
    file: UploadFile,
) -> ResponseSchemaModel[UploadFileDetail]:
    """
    上传当前用户头像

    - **file**: 头像文件（支持 jpg/jpeg/png/gif/webp）
    """
    data = await file_service.upload(
        db=db,
        file=file,
        upload_type=UploadType.avatar,
        target_path=None,
        user_id=request.user.id,
    )
    return response_base.success(data=data)
