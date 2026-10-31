from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.plugin.core import check_plugin_installed

if TYPE_CHECKING:
    from collections.abc import Callable


CONFIG_TYPE = 'SANDBOX'
STATUS_KEY = 'OPEN_SANDBOX_CONFIG_STATUS'
API_STATUS_KEY = 'OPEN_SANDBOX_API_STATUS'


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise ValueError('必须为正整数')
    return number


def _bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {'1', 'on', 'true', 'yes'}:
        return True
    if normalized in {'0', 'off', 'false', 'no'}:
        return False
    raise ValueError('必须为布尔值')


def _text(value: str) -> str:
    result = value.strip()
    if not result:
        raise ValueError('不能为空')
    return result


def _url(value: str) -> str:
    result = value.strip().rstrip('/')
    if not result.startswith(('http://', 'https://')):
        raise ValueError('必须以 http:// 或 https:// 开头')
    return result


_FIELD_SPECS: dict[str, dict[str, Any]] = {
    'OPEN_SANDBOX_URL': {
        'converter': _url,
        'default': settings.OPEN_SANDBOX_URL,
        'name': '服务器地址',
        'remark': 'OpenSandbox 服务地址，例如 http://127.0.0.1:8080',
    },
    'OPEN_SANDBOX_IMAGE': {
        'converter': _text,
        'default': settings.OPEN_SANDBOX_IMAGE,
        'name': '默认沙盒镜像',
        'remark': '新建沙盒时默认使用的镜像',
    },
    'OPEN_SANDBOX_MAX_SANDBOXES_PER_USER': {
        'converter': _positive_int,
        'default': settings.OPEN_SANDBOX_MAX_SANDBOXES_PER_USER,
        'name': '每用户最大沙盒数',
        'remark': '所有用户统一使用该全局配额',
    },
    'OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS': {
        'converter': _positive_int,
        'default': settings.OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS,
        'name': '空闲暂停秒数',
        'remark': '超过该时间无活动后自动暂停',
    },
    'OPEN_SANDBOX_AUTO_PAUSE_ENABLED': {
        'converter': _bool,
        'default': settings.OPEN_SANDBOX_AUTO_PAUSE_ENABLED,
        'name': '空闲自动暂停',
        'remark': '关闭后不会自动暂停空闲沙盒',
    },
    'OPEN_SANDBOX_RESOURCE_CPU': {
        'converter': _text,
        'default': settings.OPEN_SANDBOX_RESOURCE_CPU,
        'name': 'CPU 限制',
        'remark': '例如 1 或 2',
    },
    'OPEN_SANDBOX_RESOURCE_MEMORY': {
        'converter': _text,
        'default': settings.OPEN_SANDBOX_RESOURCE_MEMORY,
        'name': '内存限制',
        'remark': '例如 2Gi 或 4Gi',
    },
    'OPEN_SANDBOX_MAX_OUTPUT_CHARS': {
        'converter': _positive_int,
        'default': settings.OPEN_SANDBOX_MAX_OUTPUT_CHARS,
        'name': '命令输出最大字符数',
        'remark': '超过后截断 stdout 和 stderr',
    },
    'OPEN_SANDBOX_UPLOAD_LIMIT_BYTES': {
        'converter': _positive_int,
        'default': settings.OPEN_SANDBOX_UPLOAD_LIMIT_BYTES,
        'name': '文件上传限制（字节）',
        'remark': '单文件上传最大字节数',
    },
    'OPEN_SANDBOX_FILE_TEXT_LIMIT_BYTES': {
        'converter': _positive_int,
        'default': settings.OPEN_SANDBOX_FILE_TEXT_LIMIT_BYTES,
        'name': '文本预览限制（字节）',
        'remark': '在线预览和编辑文本文件时读取的最大字节数',
    },
}
_DEFAULTS = {key: spec['default'] for key, spec in _FIELD_SPECS.items()}


def _serialize_default(value: Any) -> str:
    """将 Python 默认值转换为参数配置使用的字符串"""

    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


async def ensure_sandbox_config_defaults(db: AsyncSession) -> None:
    """幂等创建沙盒参数配置默认记录"""

    if not check_plugin_installed('config'):
        return
    from backend.plugin.config.crud.crud_config import config_dao
    from backend.plugin.config.schema.config import CreateConfigParam

    keys = [STATUS_KEY, API_STATUS_KEY, *_FIELD_SPECS]
    existing = await config_dao.get_all_by_keys(db, keys)
    existing_map = {item.key: item for item in existing}
    existing_keys = set(existing_map)
    for key, spec in _FIELD_SPECS.items():
        config = existing_map.get(key)
        if config and isinstance(spec['default'], bool):
            normalized = config.value.strip().lower()
            if normalized in {'true', 'false'} and config.value != normalized:
                config.value = normalized
    await db.flush()
    if STATUS_KEY not in existing_keys:
        await config_dao.create(
            db,
            CreateConfigParam(
                name='启用沙盒动态配置',
                type=CONFIG_TYPE,
                key=STATUS_KEY,
                value='1',
                is_frontend=False,
                remark='启用后使用参数配置中的沙盒参数',
            ),
        )
    if API_STATUS_KEY not in existing_keys:
        await config_dao.create(
            db,
            CreateConfigParam(
                name='沙盒 API 开关',
                type=CONFIG_TYPE,
                key=API_STATUS_KEY,
                value='1',
                is_frontend=False,
                remark='1=开启，0=暂停；仅暂停平台 API，不停止 OpenSandbox Server 进程',
            ),
        )
    for key, spec in _FIELD_SPECS.items():
        if key in existing_keys:
            continue
        await config_dao.create(
            db,
            CreateConfigParam(
                name=spec['name'],
                type=CONFIG_TYPE,
                key=key,
                value=_serialize_default(spec['default']),
                is_frontend=False,
                remark=spec['remark'],
            ),
        )


async def load_sandbox_config(db: AsyncSession) -> None:
    """加载全局沙盒动态配置，未启用或无效时回退到 plugin.toml"""

    effective = dict(_DEFAULTS)
    if check_plugin_installed('config'):
        from backend.plugin.config.enums import ConfigType
        from backend.plugin.config.service.config_service import config_service

        configs = await config_service.get_all(db=db, type=ConfigType.sandbox)
        values = {
            getattr(config, 'key', ''): getattr(config, 'value', '')
            for config in configs or []
            if getattr(config, 'key', None)
        }
        if values.get(STATUS_KEY, '1') != '0':
            for key, spec in _FIELD_SPECS.items():
                raw = values.get(key)
                if raw is None:
                    continue
                converter: Callable[[str], Any] = spec['converter']
                try:
                    effective[key] = converter(raw)
                except (TypeError, ValueError) as exc:
                    log.warning(f'沙盒动态配置无效，已回退到默认值：{key}={raw!r}，原因：{exc}')
    for key, value in effective.items():
        setattr(settings, key, value)


async def is_sandbox_api_enabled(db: AsyncSession) -> bool:
    """判断管理员是否启用了沙盒 API"""

    if not check_plugin_installed('config'):
        return True
    from backend.plugin.config.crud.crud_config import config_dao

    config = await config_dao.get_by_key(db, API_STATUS_KEY)
    return config is None or config.value.strip() != '0'


async def ensure_sandbox_api_enabled(db: AsyncSession) -> None:
    """未启用沙盒 API 时拒绝沙盒操作"""

    if not await is_sandbox_api_enabled(db):
        raise errors.RequestError(
            code=503,
            msg='沙盒 API 已被管理员暂停，请在“沙盒实例”页面点击“启用 API”恢复',
        )


async def set_sandbox_api_enabled(db: AsyncSession, *, enabled: bool) -> bool:
    """保存沙盒 API 开关，不启动或停止 OpenSandbox Server 进程"""

    if not check_plugin_installed('config'):
        raise errors.RequestError(msg='参数配置插件未安装，无法保存沙盒 API 开关')
    from backend.plugin.config.crud.crud_config import config_dao
    from backend.plugin.config.schema.config import CreateConfigParam, UpdateConfigParam

    value = '1' if enabled else '0'
    config = await config_dao.get_by_key(db, API_STATUS_KEY)
    if config is None:
        await config_dao.create(
            db,
            CreateConfigParam(
                name='沙盒 API 开关',
                type=CONFIG_TYPE,
                key=API_STATUS_KEY,
                value=value,
                is_frontend=False,
                remark='1=开启，0=暂停；仅暂停平台 API，不停止 OpenSandbox Server 进程',
            ),
        )
    else:
        await config_dao.update(
            db,
            config.id,
            UpdateConfigParam(
                name=config.name,
                type=config.type,
                key=config.key,
                value=value,
                is_frontend=config.is_frontend,
                remark=config.remark,
            ),
        )
        config.value = value
    await db.flush()
    return enabled
