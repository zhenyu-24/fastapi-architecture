from fastapi import APIRouter

from backend.core.conf import settings
from backend.plugin.opensandbox.api.v1.admin import router as admin_router
from backend.plugin.opensandbox.api.v1.sandbox import router as sandbox_router

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(sandbox_router)
v1.include_router(admin_router)
