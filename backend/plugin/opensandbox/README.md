# OpenSandbox 沙盒工作台

基于 OpenSandbox 的 SSH 终端、SFTP 文件传输、在线代码运行、管理员沙盒管理与命令审计

- 普通用户操作自己的沙盒，管理员操作全部用户沙盒
- 我的沙盒支持搜索、状态筛选、排序、启动、停止、重启和删除
- 文件上传下载、重命名、删除与可持久化 Bash 会话
- 沙盒空闲自动暂停，保留文件与进程状态
- 命令执行记录与输出仅管理员可审计

## 插件类型

- 应用级插件

## 配置说明

在 `backend/.env` 中添加以下内容：

```env
OPEN_SANDBOX_ENABLED='false'
OPEN_SANDBOX_URL='http://127.0.0.1:8080'
OPEN_SANDBOX_API_KEY=''
```

插件目录下 `plugin.toml` 的 `[settings]` 中包含以下内容：

```toml
[settings]
OPEN_SANDBOX_IMAGE = 'sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.1.0'
OPEN_SANDBOX_WORKSPACE_ROOT = '/workspace'
OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS = 1800
OPEN_SANDBOX_AUTO_PAUSE_ENABLED = true
OPEN_SANDBOX_AUTO_PAUSE_SWEEP_SECONDS = 60
OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED = true
OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_SECONDS = 3600
OPEN_SANDBOX_LEGACY_EXPIRY_EXTEND_MINUTES = 525600
OPEN_SANDBOX_MAX_SANDBOXES_PER_USER = 2
OPEN_SANDBOX_MAX_OUTPUT_CHARS = 200000
OPEN_SANDBOX_REQUEST_TIMEOUT_SECONDS = 60
OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS = 120
OPEN_SANDBOX_RESOURCE_CPU = '1'
OPEN_SANDBOX_RESOURCE_MEMORY = '2Gi'
OPEN_SANDBOX_FILE_TEXT_LIMIT_BYTES = 2097152
OPEN_SANDBOX_UPLOAD_LIMIT_BYTES = 52428800
```

在 `backend/core/conf.py` 中添加以下内容：

```python
##################################################
# [ Plugin ] opensandbox
##################################################
# .env
OPEN_SANDBOX_ENABLED: bool
OPEN_SANDBOX_URL: str
OPEN_SANDBOX_API_KEY: str

# 基础配置（in plugin.toml）
OPEN_SANDBOX_IMAGE: str
OPEN_SANDBOX_WORKSPACE_ROOT: str
OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS: int
OPEN_SANDBOX_AUTO_PAUSE_ENABLED: bool
OPEN_SANDBOX_AUTO_PAUSE_SWEEP_SECONDS: int
OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED: bool
OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_SECONDS: int
OPEN_SANDBOX_LEGACY_EXPIRY_EXTEND_MINUTES: int
OPEN_SANDBOX_MAX_SANDBOXES_PER_USER: int
OPEN_SANDBOX_MAX_OUTPUT_CHARS: int
OPEN_SANDBOX_REQUEST_TIMEOUT_SECONDS: int
OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS: int
OPEN_SANDBOX_RESOURCE_CPU: str
OPEN_SANDBOX_RESOURCE_MEMORY: str
OPEN_SANDBOX_FILE_TEXT_LIMIT_BYTES: int
OPEN_SANDBOX_UPLOAD_LIMIT_BYTES: int
```

## 全局动态配置

管理员可在“系统管理 → 参数配置 → 沙盒配置”中修改默认镜像、全局用户配额、空闲暂停、资源限制和输出/文件限制。

配置类型为 `SANDBOX`，状态键为 `OPEN_SANDBOX_CONFIG_STATUS`。启用时覆盖 `plugin.toml` 默认值，关闭时自动回退。

API Key 仍只允许通过 `.env` 配置；OpenSandbox URL 可在参数配置中修改；沙盒 API 开关由管理员在“沙盒实例”页面控制。

## 使用方式

1. 在 OpenSandbox 服务端设置 `server.api_key`，或仅在可信网络中使用空 API Key
2. 启动 OpenSandbox lifecycle server 并确认服务健康检查可访问
3. 管理员在系统管理的“沙盒管理”创建或同步沙盒，普通用户在“我的沙盒”中创建自己的沙盒
4. 使用“SSH 终端”执行命令，使用“SFTP 文件传输”管理文件，使用“在线代码运行”编辑并运行代码
5. 管理员在“沙盒管理 → 命令审计”查看全部用户的命令、输出和退出码

沙盒默认以手动清理模式创建，空闲后由插件暂停并保留文件与进程，不会按生命周期 TTL 自动删除。旧版本创建的有限 TTL 沙盒会在到期前自动续期并纳入同一暂停策略。

## 沙盒 API 开关

“沙盒实例”页面的“启用 API/暂停 API”只修改 `sys_config` 中 `SANDBOX` 类型的 `OPEN_SANDBOX_API_STATUS`：

- `1`：启用平台 API；
- `0`：暂停所有沙盒操作 API。

该开关不会启动或停止 OpenSandbox Server 进程，也不会删除沙盒。暂停期间，概览、沙盒列表和命令审计仍可访问；创建、同步、终端、SFTP、代码运行和沙盒生命周期操作会返回 HTTP 503“沙盒 API 已被管理员暂停”。

服务状态对象包含 `api_enabled`、`server_available` 和 `available`：暂停时 `api_enabled=false`，Server 健康检查结果仍写入 `server_available`，只有两者都为 `true` 时 `available` 才为 `true`。`start_command_configured` / `stop_command_configured` 仅为旧配置兼容字段，当前版本不会执行对应命令。

## 卸载说明

- 停止并删除仍由本插件管理的沙盒
- 移除 OpenSandbox 环境变量与配置字段
- 删除沙盒记录和命令审计数据

## 联系方式

- 作者：`codex`
- 反馈方式：提交 Issue 或 PR
