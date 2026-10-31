# OpenSandbox 部署

本文以 Windows 11 + WSL2 Ubuntu 24.04 + Docker Desktop 为参考环境，目标是把 OpenSandbox Server、fba 后端和 Vue 前端完整连接起来。

## 1. 组件关系

```text
Windows Browser
    |
    v
Vue web-ele :5777 / Nginx
    |
    v
FastAPI fba :8000
    |  opensandbox Python SDK
    v
OpenSandbox Server :8080  （WSL2 或 Linux）
    |
    +-- execd 容器
    +-- code-interpreter 容器
```

浏览器不直接访问 OpenSandbox。所有沙盒创建、命令执行、文件传输都先经过 fba 后端鉴权。

## 2. 版本基线

| 组件 | 推荐版本 |
|---|---|
| OpenSandbox Server | 1.2.0 |
| OpenSandbox Python SDK | `>=1.2.0` |
| fba | 1.16.0 或当前仓库版本 |
| Docker | 24+ |
| WSL | 2.x |
| Ubuntu | 24.04 |

Python SDK 已在后端 `pyproject.toml` 和插件 `requirements.txt` 中声明为 `opensandbox>=1.2.0`。

## 3. 安装 WSL2 和 Docker

```powershell
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
wsl --update
wsl --status
```

安装 Docker Desktop 后，在 Docker Desktop 设置中启用 WSL integration，并勾选 `Ubuntu-24.04`。

在 WSL 中检查 Docker：

```bash
docker version
docker info --format '{{.ServerVersion}}'
```

| 命令/参数 | 说明 |
|---|---|
| `docker version` | 同时检查客户端和服务端 |
| `docker info --format` | 输出 Docker 服务端版本 |
| `wsl --update` | 更新 WSL 内核 |
| `wsl --status` | 查看 WSL 版本和默认发行版 |

## 4. 获取 OpenSandbox

参考 [OpenSandbox Server 安装文档](https://open-sandbox.ai/getting-started/installation#server)。

在 Windows PowerShell 中进入 WSL：

```powershell
wsl -d Ubuntu-24.04 -u xzy
```

进入 WSL 后执行：

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/opensandbox-group/OpenSandbox.git opensandbox
cd ~/projects/opensandbox
```

如果目录结构是仓库根目录下的 `OpenSandbox` 子目录，请进入包含 `server`、`sdks` 和 `docs` 的目录：

```bash
find ~/projects/opensandbox -maxdepth 2 -name server -type d
```

安装 Python 依赖：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
cd ~/projects/opensandbox
uv sync
```

| 命令 | 参数 | 说明 |
|---|---|---|
| `curl -LsSf URL` | `-L` 跟随跳转，`-s` 静默，`-S` 显示错误，`-f` HTTP 错误失败 | 下载 uv 安装脚本 |
| `uv sync` | 无 | 按锁文件安装 Python 依赖 |
| `source ~/.bashrc` | 无 | 使 uv 进入当前 shell PATH |

## 5. 拉取运行时镜像

```bash
docker pull opensandbox/execd:v1.1.0
docker pull sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.1.0
docker images | grep -E 'execd|code-interpreter'
```

| 镜像 | 配置键 | 用途 |
|---|---|---|
| `opensandbox/execd:v1.1.0` | `runtime.execd_image` | 命令、文件和会话执行代理 |
| `sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.1.0` | `OPEN_SANDBOX_IMAGE` | 默认代码解释器沙盒镜像 |

如果本地镜像没有标签，可先执行 `docker images` 确认实际标签，再同步修改配置。

## 6. 创建 `~/.sandbox.toml`

推荐使用仓库中的参考配置：

- [OpenSandbox 完整参考配置](../reference/opensandbox.sandbox.toml.example)
- [OpenSandbox 官方配置文档](https://github.com/opensandbox-group/OpenSandbox/blob/main/server/configuration.md)

最小可用配置如下：

```toml
[server]
host = "127.0.0.1"
port = 8080
api_key = "replace-with-a-long-random-api-key"

[proxy]
# WSL2 下推荐 false，避免 Server 无法解析 Docker bridge 容器地址。
resolve_internal = false

[log]
level = "INFO"

[runtime]
type = "docker"
execd_image = "opensandbox/execd:v1.1.0"

[docker]
network_mode = "bridge"
port_range_min = 40000
port_range_max = 60000

[ingress]
mode = "direct"

[store]
type = "sqlite"
path = "~/.opensandbox/opensandbox.db"
```

将文件放到 WSL 用户主目录：

```bash
nano ~/.sandbox.toml
chmod 600 ~/.sandbox.toml
```

### 配置项说明

| 配置 | 说明 | 建议 |
|---|---|---|
| `server.host` | API 监听地址 | WSL 与 Windows 联调可用 `127.0.0.1` |
| `server.port` | API 端口 | 默认 8080 |
| `server.api_key` | 客户端请求头 `OPEN-SANDBOX-API-KEY` 的值 | 必须使用强随机值 |
| `proxy.resolve_internal` | 是否直接解析容器 bridge IP | WSL2 推荐 `false` |
| `runtime.type` | 运行时类型 | Docker 环境使用 `docker` |
| `runtime.execd_image` | execd 镜像 | `opensandbox/execd:v1.1.0` |
| `docker.port_range_min/max` | 沙盒动态端口范围 | 确保防火墙和端口范围足够 |
| `ingress.mode` | 访问入口模式 | Docker runtime 使用 `direct` |
| `store.type` | Server 自身状态存储 | 单机用 SQLite，生产可换 PostgreSQL |

## 7. 启动 OpenSandbox Server

### 方式 A：推荐，使用 API Key

```bash
cd ~/projects/opensandbox/OpenSandbox
export OPENSANDBOX_SERVER_API_KEY='replace-with-a-long-random-api-key'
uv run opensandbox-server
```

### 方式 B：仅本机可信环境，无 API Key

```bash
cd ~/projects/opensandbox/OpenSandbox
OPENSANDBOX_INSECURE_SERVER=YES uv run opensandbox-server
```

OpenSandbox 在空 API Key 时会要求确认；非交互环境必须显式设置 `OPENSANDBOX_INSECURE_SERVER=YES`。

### 后台运行

```bash
cd ~/projects/opensandbox/OpenSandbox
setsid -f env OPENSANDBOX_SERVER_API_KEY='replace-with-a-long-random-api-key'   .venv/bin/opensandbox-server </dev/null >/tmp/opensandbox-server.log 2>&1
```

| 参数 | 说明 |
|---|---|
| `setsid -f` | 创建独立会话并后台运行，避免 WSL 命令退出时结束服务 |
| `env KEY=VALUE` | 为服务进程注入环境变量 |
| `.venv/bin/opensandbox-server` | 使用 uv 环境中的 Server 可执行文件 |
| `</dev/null` | 禁止后台服务等待终端输入 |
| `>/tmp/opensandbox-server.log 2>&1` | 合并标准输出和错误日志 |

## 8. 验证 OpenSandbox

在 WSL 中：

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/version
```

预期：

```json
{"status":"healthy"}
{"version":"1.2.0"}
```

在 Windows PowerShell 中：

```powershell
curl.exe -fsS http://127.0.0.1:8080/health
curl.exe -fsS http://127.0.0.1:8080/version
```

如果 Windows 无法访问 WSL 端口，先在 WSL 获取地址并测试：

```bash
hostname -I
curl -fsS http://$(hostname -I | awk '{print $1}'):8080/health
```

## 9. 配置 fba 后端

### 本机直接运行后端

编辑 `backend/.env`：

```dotenv
OPEN_SANDBOX_ENABLED='true'
OPEN_SANDBOX_URL='http://127.0.0.1:8080'
OPEN_SANDBOX_API_KEY='replace-with-a-long-random-api-key'
OPEN_SANDBOX_AUTO_PAUSE_ENABLED=true
OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS=1800
OPEN_SANDBOX_AUTO_PAUSE_SWEEP_SECONDS=60
OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED=true
OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_SECONDS=3600
OPEN_SANDBOX_LEGACY_EXPIRY_EXTEND_MINUTES=525600
```

### Docker Compose 运行后端

编辑根目录 `.env`，并注意容器内访问 Windows/WSL 服务的主机名：

```dotenv
OPEN_SANDBOX_ENABLED=true
OPEN_SANDBOX_URL=http://host.docker.internal:8080
OPEN_SANDBOX_API_KEY=replace-with-a-long-random-api-key
OPEN_SANDBOX_AUTO_PAUSE_ENABLED=true
OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS=1800
```

重启 API 容器：

```powershell
docker compose -f docker-simply-compose.yml up -d --force-recreate fba_server
```

### 配置项说明

| 配置 | 默认值 | 说明 |
|---|---:|---|
| `OPEN_SANDBOX_ENABLED` | `false` | 是否启用插件 |
| `OPEN_SANDBOX_URL` | `http://127.0.0.1:8080` | Server 地址 |
| `OPEN_SANDBOX_API_KEY` | 空 | 与 `server.api_key` 一致 |
| `OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS` | `1800` | 空闲暂停阈值 |
| `OPEN_SANDBOX_AUTO_PAUSE_ENABLED` | `true` | 自动暂停开关 |
| `OPEN_SANDBOX_AUTO_PAUSE_SWEEP_SECONDS` | `60` | 巡检间隔 |
| `OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED` | `true` | 旧有限 TTL 沙盒续期保护 |
| `OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_SECONDS` | `3600` | 距离到期多久开始续期 |
| `OPEN_SANDBOX_LEGACY_EXPIRY_EXTEND_MINUTES` | `525600` | 续期时长，默认 365 天 |
| `OPEN_SANDBOX_MAX_SANDBOXES_PER_USER` | `2` | 每用户最大沙盒数 |
| `OPEN_SANDBOX_MAX_OUTPUT_CHARS` | `200000` | 单次命令输出上限 |
| `OPEN_SANDBOX_REQUEST_TIMEOUT_SECONDS` | `60` | SDK 请求超时 |
| `OPEN_SANDBOX_CREATE_READY_TIMEOUT_SECONDS` | `120` | 等待沙盒就绪 |
| `OPEN_SANDBOX_RESOURCE_CPU` | `1` | 每个沙盒 CPU |
| `OPEN_SANDBOX_RESOURCE_MEMORY` | `2Gi` | 每个沙盒内存 |
| `OPEN_SANDBOX_UPLOAD_LIMIT_BYTES` | `52428800` | 上传上限，默认 50 MiB |
| `OPEN_SANDBOX_FILE_TEXT_LIMIT_BYTES` | `2097152` | 在线文本读取上限，默认 2 MiB |

## 10. 管理员 API 开关与手工进程管理

管理员页面的“启用 API/暂停 API”只修改 `sys_config` 中的 `OPEN_SANDBOX_API_STATUS`，不会启动或停止 OpenSandbox Server。

暂停后：

- 平台不再调用 OpenSandbox 的创建、命令、文件等 API；
- 概览、沙盒列表和命令审计仍可访问；
- Server 进程、Docker 容器和沙盒文件保持不变；
- 暂停期间概览接口仍执行健康检查，因此可以区分“已暂停”和“进程不可达”。

如果需要真正启停 WSL2 中的 Server，请手工执行：

```bash
# 启动（无 API Key 的本地开发）
cd ~/projects/opensandbox
setsid -f env OPENSANDBOX_INSECURE_SERVER=YES uv run opensandbox-server </dev/null >/tmp/opensandbox-server.log 2>&1

# 启动（使用 API Key）
cd ~/projects/opensandbox
setsid -f env OPENSANDBOX_SERVER_API_KEY=replace-with-a-long-random-api-key uv run opensandbox-server </dev/null >/tmp/opensandbox-server.log 2>&1

# 停止
pkill -f opensandbox-server || true
```

注意：

- `setsid -f` 让进程脱离当前 shell，避免命令一直阻塞。
- `pkill -f opensandbox-server` 会终止匹配进程，只应在该主机专用于 OpenSandbox 时使用。
- `OPEN_SANDBOX_SERVICE_START_COMMAND` 和 `OPEN_SANDBOX_SERVICE_STOP_COMMAND` 已废弃，当前版本不会执行。

## 11. 沙盒生命周期

```text
create(timeout=None)
  -> Running
  -> 空闲 1800 秒
  -> Paused（docker pause，保留文件与进程）
  -> 用户访问或管理员恢复
  -> Running
  -> 管理员显式删除
  -> Terminated
```

关键规则：

- 新沙盒调用 `Sandbox.create(..., timeout=None)`，OpenSandbox 标签为 `opensandbox.io/manual-cleanup=true`。
- 不使用 TTL 自动删除。
- 空闲巡检调用 OpenSandbox pause，不删除容器。
- 旧版本创建的有限 TTL 沙盒在到期前会自动续期，并纳入空闲暂停策略。
- 只有管理员显式删除或宕机后的外部清理会移除容器。

验证新建沙盒：

```powershell
docker ps -a --filter "label=fba_managed=true" --format "table {{.Names}}	{{.Status}}"
docker inspect <sandbox-container> --format "{{json .Config.Labels}}"
```

应看到：

```json
{
  "opensandbox.io/manual-cleanup": "true",
  "fba_managed": "true"
}
```

## 12. API Key 校验

后端 SDK 使用请求头 `OPEN-SANDBOX-API-KEY`。不要自行在浏览器请求中添加该头。

手动验证：

```powershell
$headers = @{ 'OPEN-SANDBOX-API-KEY' = 'replace-with-a-long-random-api-key' }
Invoke-RestMethod -Headers $headers -Uri 'http://127.0.0.1:8080/version'
```

若返回 401，检查后端 `.env` 与 `~/.sandbox.toml` 或 `OPENSANDBOX_SERVER_API_KEY` 是否完全一致。

## 13. 升级步骤

1. 备份 OpenSandbox store 和 fba 数据库。
2. 记录当前镜像标签。
3. 在“沙盒实例”页面点击“暂停 API”，或停止 fba API 的空闲巡检，避免升级期间继续调用旧 Server。
4. 拉取新镜像并执行 `uv sync`。
5. 检查 `.sandbox.toml` 配置键是否变化。
6. 启动 Server，验证 `/health`、`/version`。
7. 创建临时沙盒，验证执行命令、文件读写、暂停和恢复。
8. 删除临时沙盒。
9. 在“沙盒实例”页面点击“启用 API”，确认状态恢复为“可用”。

## 14. 参考资料

- [OpenSandbox Server 安装](https://open-sandbox.ai/getting-started/installation#server)
- [OpenSandbox Python SDK](https://open-sandbox.ai/sdks/python)
- [OpenSandbox API](https://open-sandbox.ai/api/)
- [OpenSandbox Examples](https://open-sandbox.ai/examples/)
- [OpenSandbox configuration.md](https://github.com/opensandbox-group/OpenSandbox/blob/main/server/configuration.md)
- [OpenSandbox issue #750：空 API Key 安全提示](https://github.com/opensandbox-group/OpenSandbox/issues/750)
