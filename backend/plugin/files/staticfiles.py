import os

from pathlib import Path

from anyio import to_thread
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.files.crud.crud_file import file_dao
from backend.plugin.files.service.file_service import file_service
from backend.utils.staticfiles import RestrictedStaticFiles


class UploadStaticFiles(RestrictedStaticFiles):
    """公开图片和视频可直接展示，共用目录的头像额外校验公开记录"""

    async def get_response(self, path: str, scope: Scope) -> Response:
        path = path.replace(os.sep, '/')
        root = await to_thread.run_sync(Path(self.directory).resolve)
        try:
            file_service._validate_relative_path(path)
        except errors.RequestError:
            raise HTTPException(status_code=404) from None
        if path.startswith('avatar/'):
            directory = root / 'avatar'
            relative = path[len('avatar/') :]
            async with async_db_session() as db:
                allowed = await file_dao.is_public_avatar(db, url_path=f'/static/upload/{path}')
            if not allowed:
                raise HTTPException(status_code=404)
        elif path.startswith(('image/', 'public/image/', 'video/', 'public/video/')):
            public_path = path.removeprefix('public/')
            media_type, relative = public_path.split('/', 1)
            directory = root / 'public' / media_type
        else:
            raise HTTPException(status_code=404)
        try:
            resolved = await to_thread.run_sync(file_service._resolve_storage_path, directory, relative)
        except errors.RequestError:
            raise HTTPException(status_code=404) from None
        return await super().get_response(resolved.relative_to(root).as_posix(), scope)
