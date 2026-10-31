from fastapi import APIRouter

router = APIRouter()


# @router.post(
#     '/upload',
#     summary='本地文件上传',
#     dependencies=[
#         Depends(RequestPermission('sys:file:upload')),
#         DependsRBAC,
#     ],
# )
# async def upload_files(file: Annotated[UploadFile, File()]) -> ResponseSchemaModel[UploadUrl]:
#     upload_file_verify(file)
#     filename = await upload_file(file)
#     return response_base.success(data={'url': f'/static/upload/{filename}'})
