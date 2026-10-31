# 配置参考

## 配置优先级

后端配置来源：

```text
系统环境变量 -> backend/.env -> plugin.toml [settings] -> conf.py 默认值
```

`.env` 适用于部署环境；`plugin.toml` 只放非敏感插件默认值；`conf.py` 提供类型和 IDE 提示。

## 后端基础配置

| 配置 | 默认值 | 说明 |
|---|---:|---|
| `ENVIRONMENT` | `dev` | `dev` 或 `prod` |
| `DATABASE_TYPE` | `postgresql` | `postgresql` 或 `mysql` |
| `DATABASE_SCHEMA` | `fba` | 数据库名称 |
| `DATABASE_HOST` | `127.0.0.1` | 数据库主机 |
| `DATABASE_PORT` | `5432` | 数据库端口 |
| `DATABASE_USER` | `postgres` | 数据库用户 |
| `DATABASE_PASSWORD` | - | 数据库密码 |
| `DATABASE_PK_MODE` | `snowflake` | `snowflake` 或 `autoincrement` |
| `REDIS_HOST` | `127.0.0.1` | Redis 主机 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_PASSWORD` | 空 | Redis 密码 |
| `REDIS_DATABASE` | `0` | 业务 Redis 数据库 |
| `TOKEN_SECRET_KEY` | - | JWT 签名密钥 |
| `TOKEN_EXPIRE_SECONDS` | `86400` | Access Token 有效期 |
| `TOKEN_REFRESH_EXPIRE_SECONDS` | `604800` | Refresh Token 有效期 |
| `CORS_ALLOWED_ORIGINS` | - | 允许的前端来源 JSON 数组 |

示例：

```dotenv
ENVIRONMENT='dev'
DATABASE_TYPE='postgresql'
DATABASE_SCHEMA='fba'
DATABASE_HOST='127.0.0.1'
DATABASE_PORT=5432
DATABASE_USER='postgres'
DATABASE_PASSWORD='replace-me'
REDIS_HOST='127.0.0.1'
REDIS_PORT=6379
TOKEN_SECRET_KEY='replace-with-random-secret'
CORS_ALLOWED_ORIGINS='["http://localhost:5777","http://127.0.0.1:5777"]'
```

## OpenSandbox 环境变量

| 配置 | 默认值 | 必填 | 说明 |
|---|---:|---:|---|
| `OPEN_SANDBOX_ENABLED` | `false` | 是 | 是否启用插件 |
| `OPEN_SANDBOX_URL` | `http://127.0.0.1:8080` | 是 | Server API 地址，可由参数配置覆盖 |
| `OPEN_SANDBOX_API_KEY` | 空 | 推荐 | 与 `server.api_key` 一致 |
| `OPEN_SANDBOX_SERVICE_START_COMMAND` | 空 | 否 | 兼容保留；当前版本不再执行 |
| `OPEN_SANDBOX_SERVICE_STOP_COMMAND` | 空 | 否 | 兼容保留；当前版本不再执行 |

## OpenSandbox 插件默认值

| 配置 | 默认值 | 说明 |
|---|---:|---|
| `OPEN_SANDBOX_IMAGE` | code-interpreter v1.1.0 | 默认沙盒镜像 |
| `OPEN_SANDBOX_WORKSPACE_ROOT` | `/workspace` | 文件工作区 |
| `OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS` | `1800` | 空闲暂停阈值 |
| `OPEN_SANDBOX_AUTO_PAUSE_ENABLED` | `true` | 自动暂停 |
| `OPEN_SANDBOX_AUTO_PAUSE_SWEEP_SECONDS` | `60` | 巡检周期 |
| `OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED` | `true` | 旧有限 TTL 保护 |
| `OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_SECONDS` | `3600` | 距到期多久开始续期 |
| `OPEN_SANDBOX_LEGACY_EXPIRY_EXTEND_MINUTES` | `525600` | 续期 365 天 |
| `OPEN_SANDBOX_MAX_SANDBOXES_PER_USER` | `2` | 每用户上限 |
| `OPEN_SANDBOX_MAX_OUTPUT_CHARS` | `200000` | 输出上限 |
| `OPEN_SANDBOX_REQUEST_TIMEOUT_SECONDS` | `60` | SDK 请求超时 |
| `OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS` | `120` | 创建就绪超时 |
| `OPEN_SANDBOX_RESOURCE_CPU` | `1` | 单沙盒 CPU |
| `OPEN_SANDBOX_RESOURCE_MEMORY` | `2Gi` | 单沙盒内存 |
| `OPEN_SANDBOX_SERVICE_COMMAND_TIMEOUT_SECONDS` | `45` | 兼容保留；当前版本不再使用 |
| `OPEN_SANDBOX_FILE_TEXT_LIMIT_BYTES` | `2097152` | 文本读取上限 |
| `OPEN_SANDBOX_UPLOAD_LIMIT_BYTES` | `52428800` | 上传上限 |

## 前端配置

`apps/web-ele/.env.development`：

```dotenv
VITE_PORT=5777
VITE_GLOB_API_URL=http://localhost:8000/api
VITE_NITRO_MOCK=false
```

`apps/web-ele/.env.production`：

```dotenv
VITE_GLOB_API_URL=https://example.com/api
VITE_BASE=/
VITE_ROUTER_HISTORY=hash
VITE_COMPRESS=none
VITE_PWA=false
```

`VITE_GLOB_API_URL` 必须包含 `/api`，版本号 `/v1` 由前端 API 模块管理。

## Docker Compose 配置

简化部署使用根目录 `.env`：

```dotenv
TZ=Asia/Shanghai
SERVER_PORT=8000
SERVER_INTERNAL_PORT=8000
POSTGRES_PORT=5432
REDIS_HOST_PORT=6379
DATABASE_SCHEMA=fba
DATABASE_USER=postgres
DATABASE_PASSWORD=replace-me
DATABASE_HOST=fba_postgres
DATABASE_PORT=5432
REDIS_HOST=fba_redis
REDIS_PORT=6379
CELERY_BROKER_TYPE=redis
```

容器访问 OpenSandbox 时注意：

- `OPEN_SANDBOX_URL` 是容器内部可达地址。
- Windows 本机服务通常使用 `host.docker.internal`。
- 同一 Docker 网络可直接使用服务名。

## 沙盒 API 开关

管理员在“系统管理 → 沙盒管理 → 沙盒实例”中点击“启用 API/暂停 API”时，后端只修改参数配置表 `sys_config` 中的一条记录：

```text
type = SANDBOX
key  = OPEN_SANDBOX_API_STATUS
value = 1 或 0
```

含义：

- `1`：启用平台 API；
- `0`：暂停平台 API。

该开关：

- 不会启动或停止 OpenSandbox Server 进程；
- 不会删除 Docker 容器或沙盒文件；
- 暂停期间仍可访问概览、沙盒列表和命令审计；
- 创建、同步、终端、SFTP、代码运行、暂停/恢复/重启/删除等操作会返回 HTTP 503：“沙盒 API 已被管理员暂停，请在‘沙盒实例’页面点击‘启用 API’恢复”。
- 暂停期间自动暂停和旧有限 TTL 续期巡检会跳过，避免后台继续调用 Server。

服务状态接口（`/api/v1/opensandbox/overview`、`/api/v1/opensandbox/admin/overview`）中的 `service` 对象包含：

| 字段 | 含义 |
|---|---|
| `api_enabled` | 管理员平台开关是否启用 |
| `server_available` | OpenSandbox Server 健康检查是否通过；暂停时仍会检查 |
| `available` | 仅当 `api_enabled && server_available` 时为 `true` |
| `message` | 当前状态的说明文字 |

如果需要真正启动或停止 OpenSandbox Server，请在 WSL2、systemd 或 Docker 编排层单独操作，例如：

```bash
# WSL2 手工启动
cd ~/projects/opensandbox
setsid -f uv run opensandbox-server </dev/null >/tmp/opensandbox-server.log 2>&1

# WSL2 手工停止
pkill -f opensandbox-server || true
```

旧版本使用的 `OPEN_SANDBOX_SERVICE_START_COMMAND` 和 `OPEN_SANDBOX_SERVICE_STOP_COMMAND` 仍保留在配置类中以避免破坏已有 `.env`，但当前版本不会执行它们。

## 沙盒全局动态配置

管理员可在“系统管理 → 参数配置 → 沙盒配置”中修改以下全局参数，无需重启：

- OpenSandbox 服务器地址
- 默认沙盒镜像
- 每用户最大沙盒数
- 空闲暂停时间
- 空闲自动暂停开关
- 默认 CPU 和内存限制
- 命令输出最大字符数
- 文件上传限制
- 文本预览限制

动态配置保存在 `sys_config`，类型为 `SANDBOX`。只有 `OPEN_SANDBOX_CONFIG_STATUS=1` 时才会覆盖 `plugin.toml` 默认值；关闭或配置值无效时自动回退到 `plugin.toml`。

`OPEN_SANDBOX_URL` 的环境变量值作为默认值与回退值；在参数配置中保存后立即生效。`OPEN_SANDBOX_API_KEY` 仍只从后端 `.env` 读取，不会出现在参数配置页面；沙盒 API 开关由管理员页面写入 `sys_config`。

## 安全建议

- `TOKEN_SECRET_KEY` 至少 32 字节随机值。
- `DATABASE_PASSWORD`、`REDIS_PASSWORD` 不复用。
- `OPEN_SANDBOX_API_KEY` 只放后端 `.env`。
- OpenSandbox Server 端口不暴露公网。
- CORS 只允许实际前端域名。
- 定期轮换密钥。
