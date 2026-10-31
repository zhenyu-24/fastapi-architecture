from fastapi import APIRouter

from backend.plugin.files.api.v1.files import router as files_router
from backend.plugin.files.api.v1.manage import router as manage_router
from backend.plugin.files.api.v1.user_avatar import router as user_avatar_router

v1 = APIRouter(prefix='/api/v1')

v1.include_router(files_router, prefix='/files', tags=['文件上下传'])
v1.include_router(manage_router, prefix='/files/manage', tags=['文件中心'])
v1.include_router(user_avatar_router, prefix='/user', tags=['用户头像'])
