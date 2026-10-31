import asyncio

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from backend.common.log import log
from backend.core.conf import settings
from backend.database.db import async_db_session
from backend.plugin.opensandbox.model import CommandLog, SandboxRecord  # ruff: ignore[unused-import]
from backend.plugin.opensandbox.service.sandbox_service import sandbox_service
from backend.plugin.opensandbox.utils.dynamic_config import ensure_sandbox_config_defaults


async def _auto_pause_loop() -> None:
    while True:
        try:
            await sandbox_service.protect_legacy_expirations()
            await sandbox_service.auto_pause_idle()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(max(10, settings.OPEN_SANDBOX_AUTO_PAUSE_SWEEP_SECONDS))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """插件生命周期：初始化动态配置并启动空闲暂停巡检"""

    try:
        async with async_db_session.begin() as db:
            await ensure_sandbox_config_defaults(db)
    except Exception:
        log.exception('初始化 OpenSandbox 动态配置失败')

    task = None
    if settings.OPEN_SANDBOX_ENABLED and (
        settings.OPEN_SANDBOX_AUTO_PAUSE_ENABLED or settings.OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED
    ):
        task = asyncio.create_task(_auto_pause_loop(), name='opensandbox-auto-pause')
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
