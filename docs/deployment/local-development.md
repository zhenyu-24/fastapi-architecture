# 本地开发

本文描述在 Windows 宿主机运行 FastAPI 后端和 Vben 前端，在 WSL2 中运行 OpenSandbox 的推荐方式。

## 1. 后端依赖与配置

```powershell
Set-Location D:\work\code\web_learning\template\fastapi-architecture
uv sync
Copy-Item backend\.env.example backend\.env -ErrorAction SilentlyContinue
```

| 命令/参数 | 说明 | 示例 |
|---|---|---|
| `uv sync` | 按 `pyproject.toml` 和 `uv.lock` 安装依赖 | `uv sync` |
| `Copy-Item A B` | 复制环境变量模板 | 已存在时不要覆盖生产配置 |

编辑 `backend/.env`，至少确认：

```dotenv
DATABASE_TYPE='postgresql'
DATABASE_HOST='127.0.0.1'
DATABASE_PORT=5432
DATABASE_USER='postgres'
DATABASE_PASSWORD='123456'
DATABASE_SCHEMA='fba'
REDIS_HOST='127.0.0.1'
REDIS_PORT=6379
OPEN_SANDBOX_ENABLED='true'
OPEN_SANDBOX_URL='http://127.0.0.1:8080'
OPEN_SANDBOX_API_KEY=''
```

## 2. 启动数据库与 Redis

```powershell
docker compose -f docker-simply-compose.yml up -d fba_postgres fba_redis
```

## 3. 初始化数据库

```powershell
.venv\Scripts\fba.exe init
```

参数说明：

| 参数 | 说明 | 示例 |
|---|---|---|
| 无参数 | 交互式初始化数据库、Redis 和基础数据 | `fba init` |
| `--auto` | 自动创建 `.env`、安装依赖、创建数据库和初始化表 | `fba init --auto` |

插件 SQL 会在初始化阶段执行。OpenSandbox 需要创建 `sys_opensandbox` 和 `sys_opensandbox_command` 两张表。

## 4. 启动后端

```powershell
.venv\Scripts\fba.exe run
```

参数说明：

| 参数 | 默认值 | 说明 | 示例 |
|---|---:|---|---|
| `--host HOST` | `127.0.0.1` | 监听地址；局域网访问改为 `0.0.0.0` | `fba run --host 0.0.0.0` |
| `--port PORT` | `8000` | 监听端口 | `fba run --port 8080` |
| `--no-reload` | 关闭 | 禁用代码变更热重载 | `fba run --no-reload` |
| `--workers N` | `1` | 多工作进程，必须配合 `--no-reload` | `fba run --no-reload --workers 4` |

验证：

```powershell
curl.exe -fsS http://127.0.0.1:8000/health
```

## 5. 启动前端

```powershell
Set-Location D:\work\code\web_learning\template\vue-vben-admin
pnpm install --frozen-lockfile
pnpm dev:ele
```

| 命令/参数 | 说明 | 示例 |
|---|---|---|
| `pnpm install --frozen-lockfile` | 严格按锁文件安装依赖 | CI 或干净环境推荐 |
| `pnpm dev:ele` | 启动 Element Plus 应用 | 默认地址 `http://localhost:5777` |
| `pnpm build:ele` | 构建生产包 | 输出 `apps/web-ele/dist` |

前端开发接口地址位于 `apps/web-ele/.env.development`：

```dotenv
VITE_PORT=5777
VITE_GLOB_API_URL=http://localhost:8000/api
```

修改端口或后端地址后必须重启 Vite。

## 6. 启动 OpenSandbox

完整步骤见 [OpenSandbox 部署](opensandbox.md)。

管理员页面的“启用 API/暂停 API”只切换平台开关，不会启动或停止 OpenSandbox Server。需要手工启停 WSL2 中的进程时执行：

```bash
# 启动
cd ~/projects/opensandbox
setsid -f uv run opensandbox-server </dev/null >/tmp/opensandbox-server.log 2>&1

# 停止
pkill -f opensandbox-server || true
```

`OPEN_SANDBOX_SERVICE_START_COMMAND` 和 `OPEN_SANDBOX_SERVICE_STOP_COMMAND` 已废弃，当前版本不会执行。

## 7. 联调检查清单

- 后端 `/health` 返回 200。
- OpenSandbox `/health` 返回 `status=healthy`。
- 前端登录成功，沙盒工作台页面显示“沙盒服务可用”。
- 创建沙盒后状态从 `Pending` 进入 `Running`。
- 终端可执行 `pwd`、`cd`、`ls`、`clear`。
- SFTP 可上传、下载、重命名、删除文件。
- 在线代码运行可保存并执行 Python 示例。
- 管理员暂停 API 后，概览、列表和审计仍可读，其他操作返回 503；点击“启用 API”后恢复。
