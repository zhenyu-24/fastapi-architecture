import asyncio

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import httpx

from opensandbox.config import ConnectionConfig
from opensandbox.manager import SandboxManager
from opensandbox.models.execd import Execution, RunCommandOpts
from opensandbox.models.filesystem import DirectoryListEntry, MoveEntry, WriteEntry
from opensandbox.models.sandboxes import SandboxFilter
from opensandbox.models.sandboxes import SandboxInfo as SdkSandboxInfo
from opensandbox.sandbox import Sandbox

from backend.core.conf import settings


class OpenSandboxError(Exception):
    """OpenSandbox 调用异常"""


class OpenSandboxClient:
    """OpenSandbox SDK 适配层"""

    @property
    def enabled(self) -> bool:
        return bool(settings.OPEN_SANDBOX_ENABLED and settings.OPEN_SANDBOX_URL.strip())

    @property
    def base_url(self) -> str:
        url = settings.OPEN_SANDBOX_URL.strip().rstrip('/')
        return url.removesuffix('/v1')

    def connection_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            domain=self.base_url,
            api_key=settings.OPEN_SANDBOX_API_KEY or None,
            use_server_proxy=True,
            request_timeout=timedelta(seconds=settings.OPEN_SANDBOX_REQUEST_TIMEOUT_SECONDS),
        )

    async def health(self) -> tuple[bool, str | None, str]:
        """检查服务健康状态"""

        if not self.enabled:
            return False, None, '未启用 OpenSandbox'
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                health = await client.get(f'{self.base_url}/health')
                if health.status_code != 200:
                    return False, None, f'健康检查失败：HTTP {health.status_code}'
                version = None
                try:
                    version_resp = await client.get(f'{self.base_url}/version')
                    if version_resp.status_code == 200:
                        version = str(version_resp.json().get('version') or '') or None
                except Exception:
                    version = None
                return True, version, '服务可用'
        except Exception as exc:
            return False, None, f'服务不可达：{exc}'

    async def _manager(self) -> SandboxManager:
        return await SandboxManager.create(connection_config=self.connection_config())

    async def list_sandboxes(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        states: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Any:
        """获取沙盒分页数据"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')
        try:
            async with await self._manager() as manager:
                return await manager.list_sandbox_infos(
                    SandboxFilter(page=page, page_size=page_size, states=states, metadata=metadata)
                )
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

    async def get_info(self, sandbox_id: str) -> SdkSandboxInfo:
        """获取沙盒详情"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')
        try:
            async with await self._manager() as manager:
                return await manager.get_sandbox_info(sandbox_id)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

    async def create_sandbox(
        self,
        *,
        image: str,
        name: str,
        user_id: int,
        username: str,
        resource: dict[str, str],
    ) -> str:
        """创建不自动过期的沙盒"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')
        try:
            sandbox = await Sandbox.create(
                image,
                connection_config=self.connection_config(),
                timeout=None,
                ready_timeout=timedelta(seconds=settings.OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS),
                resource=resource,
                metadata={
                    'fba_user_id': str(user_id),
                    'fba_username': username,
                    'fba_name': name,
                    'fba_managed': 'true',
                },
            )
            sandbox_id = sandbox.id
            await sandbox.close()
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        return sandbox_id

    async def kill_sandbox(self, sandbox_id: str) -> None:
        """删除沙盒"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')
        try:
            async with await self._manager() as manager:
                await manager.kill_sandbox(sandbox_id)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

    async def patch_metadata(self, sandbox_id: str, patch: dict[str, str | None]) -> None:
        """更新 OpenSandbox 沙盒元数据"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')
        try:
            async with await self._manager() as manager:
                await manager.patch_sandbox_metadata(sandbox_id, patch)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

    async def pause_sandbox(self, sandbox_id: str) -> None:
        """暂停沙盒，保留文件与进程状态"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')
        try:
            async with await self._manager() as manager:
                await manager.pause_sandbox(sandbox_id)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

    async def resume_sandbox(self, sandbox_id: str) -> None:
        """恢复已暂停沙盒"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')
        try:
            async with await self._manager() as manager:
                await manager.resume_sandbox(sandbox_id)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

    async def renew_sandbox(self, sandbox_id: str, minutes: int) -> None:
        """设置沙盒过期时间"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')
        try:
            async with await self._manager() as manager:
                await manager.renew_sandbox(sandbox_id, timedelta(minutes=minutes))
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

    async def open_sandbox(self, sandbox_id: str) -> Sandbox:  # ruff:ignore[complex-structure]
        """连接运行中的沙盒，必要时恢复暂停状态"""

        if not self.enabled:
            raise OpenSandboxError('OpenSandbox 未启用')

        state = None
        try:
            async with await self._manager() as manager:
                info = await manager.get_sandbox_info(sandbox_id)
                state = info.status.state
                if state == 'Paused':
                    return await Sandbox.resume(
                        sandbox_id,
                        connection_config=self.connection_config(),
                        resume_timeout=timedelta(seconds=settings.OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS),
                    )
                if state in {'Pending', 'Pausing', 'Resuming'}:
                    deadline = asyncio.get_running_loop().time() + settings.OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS
                    while asyncio.get_running_loop().time() < deadline:
                        info = await manager.get_sandbox_info(sandbox_id)
                        state = info.status.state
                        if state in {'Running', 'Paused'}:
                            break
                        await asyncio.sleep(0.5)
                if state == 'Paused':
                    return await Sandbox.resume(
                        sandbox_id,
                        connection_config=self.connection_config(),
                        resume_timeout=timedelta(seconds=settings.OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS),
                    )
                if state != 'Running':
                    raise OpenSandboxError(f'沙盒当前状态为 {state}，无法操作')
        except OpenSandboxError:
            raise
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

        try:
            return await Sandbox.connect(
                sandbox_id,
                connection_config=self.connection_config(),
                connect_timeout=timedelta(seconds=settings.OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS),
            )
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc

    async def run_command(
        self,
        sandbox_id: str,
        command: str,
        *,
        cwd: str | None,
        timeout_seconds: int,
        session_id: str | None = None,
    ) -> Execution:
        """执行命令并返回 SDK 执行结果"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            if session_id:
                return await sandbox.commands.run_in_session(
                    session_id,
                    command,
                    timeout=timedelta(seconds=timeout_seconds),
                )
            return await sandbox.commands.run(
                command,
                opts=RunCommandOpts(
                    working_directory=cwd,
                    timeout=timedelta(seconds=timeout_seconds),
                ),
            )
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def create_session(self, sandbox_id: str, cwd: str | None) -> str:
        """创建 Bash 会话"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            return await sandbox.commands.create_session(working_directory=cwd)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def delete_session(self, sandbox_id: str, session_id: str) -> None:
        """删除 Bash 会话"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            await sandbox.commands.delete_session(session_id)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def list_files(self, sandbox_id: str, path: str) -> list[Any]:
        """列出目录"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            return await sandbox.files.list_directory(DirectoryListEntry(path=path, depth=1))
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def file_info(self, sandbox_id: str, path: str) -> Any:
        """获取文件信息"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            info = await sandbox.files.get_file_info([path])
            return info.get(path)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def read_bytes(self, sandbox_id: str, path: str, limit: int) -> bytes:
        """读取文件字节"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            return await sandbox.files.read_bytes(path, limit=limit)
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def write_file(self, sandbox_id: str, path: str, data: str | bytes, mode: int = 644) -> None:
        """写入文件"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            await sandbox.files.write_files([WriteEntry(path=path, data=data, mode=mode)])
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def mkdir(self, sandbox_id: str, path: str) -> None:
        """创建目录"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            await sandbox.files.create_directories([WriteEntry(path=path, mode=755)])
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def move(self, sandbox_id: str, source: str, destination: str) -> None:
        """重命名或移动"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            await sandbox.files.move_files([MoveEntry(src=source, dest=destination)])
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    async def delete_path(self, sandbox_id: str, path: str, *, is_directory: bool) -> None:
        """删除文件或目录"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            if is_directory:
                await sandbox.files.delete_directories([path])
            else:
                await sandbox.files.delete_files([path])
        except Exception as exc:
            raise OpenSandboxError(str(exc)) from exc
        finally:
            await sandbox.close()

    @asynccontextmanager
    async def download_stream(self, sandbox_id: str, path: str) -> AsyncGenerator[AsyncIterator[bytes], None]:
        """下载文件流，保持 SDK 连接直到流结束"""

        sandbox = await self.open_sandbox(sandbox_id)
        try:
            yield await sandbox.files.read_bytes_stream(path)
        finally:
            await sandbox.close()


open_sandbox_client: OpenSandboxClient = OpenSandboxClient()
