from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.opensandbox.schema.sandbox import ServiceActionResult
from backend.plugin.opensandbox.service.sandbox_service import sandbox_service
from backend.plugin.opensandbox.utils.dynamic_config import load_sandbox_config, set_sandbox_api_enabled


class ServiceControlService:
    """OpenSandbox 平台 API 开关，不启动或停止 Server 进程"""

    @staticmethod
    async def start(db: AsyncSession) -> ServiceActionResult:
        """启用沙盒 API"""

        await load_sandbox_config(db)
        await set_sandbox_api_enabled(db, enabled=True)
        status = await sandbox_service.service_status(db=db)
        output = (
            '沙盒 API 已启用。'
            if status.server_available
            else '沙盒 API 已启用，但 OpenSandbox Server 当前不可达，请检查服务进程和服务器地址。'
        )
        return ServiceActionResult(success=status.api_enabled, output=output, status=status)

    @staticmethod
    async def stop(db: AsyncSession) -> ServiceActionResult:
        """暂停沙盒 API"""

        await load_sandbox_config(db)
        await set_sandbox_api_enabled(db, enabled=False)
        status = await sandbox_service.service_status(db=db)
        return ServiceActionResult(
            success=not status.api_enabled,
            output='沙盒 API 已暂停；OpenSandbox Server 进程未被停止。',
            status=status,
        )


service_control_service: ServiceControlService = ServiceControlService()
