# 环境准备

## 版本与组件

| 组件 | 最低要求 | 推荐 | 用途 |
|---|---:|---:|---|
| Python | 3.12 | 3.13 | 后端运行 |
| uv | 最新稳定版 | 最新稳定版 | Python 依赖与 fba CLI |
| PostgreSQL | 14 | 16 | 主数据库 |
| MySQL | 8.0 | 8.0 | 可选数据库 |
| Redis | 7 | 7 | 缓存、会话和 Celery |
| Node.js | 22.18 | 22.18 LTS | 前端构建 |
| pnpm | 11.0 | 11.7.0 | Monorepo 依赖管理 |
| Docker | 24 | 最新稳定版 | 后端依赖服务和沙盒容器 |
| WSL2 | 2.x | 最新 | Windows 下运行 OpenSandbox Server |
| OpenSandbox Server | 1.2.0 | 1.2.0 | 沙盒生命周期服务 |
| OpenSandbox Python SDK | 1.2.0 | 1.2.0+ | 后端 SDK |

## 端口规划

| 端口 | 服务 | 说明 |
|---:|---|---|
| 8000 | fba API | 后端默认端口 |
| 5777 | Vben 开发服务器 | `web-ele` 默认开发端口 |
| 5432 | PostgreSQL | Docker Compose 默认映射 |
| 6379 | Redis | Docker Compose 默认映射 |
| 8080 | OpenSandbox Server | 默认监听端口 |
| 40000-60000 | Docker 沙盒动态端口 | OpenSandbox Docker runtime 端口范围 |

正式部署时应通过防火墙阻止外部直接访问 PostgreSQL、Redis、OpenSandbox Server 和沙盒动态端口，只开放前端与后端入口。

## Windows PowerShell 检查

```powershell
python --version
uv --version
node --version
pnpm --version
docker version
wsl --status
```

| 命令 | 作用 | 示例 |
|---|---|---|
| `python --version` | 检查后端 Python 版本 | 输出应为 3.12 或 3.13 |
| `uv --version` | 检查 uv | `uv --version` |
| `node --version` | 检查前端 Node.js | `node --version` |
| `pnpm --version` | 检查 pnpm | `pnpm --version` |
| `docker version` | 检查 Docker 客户端与服务端 | 同时能连接 WSL 或 Docker Desktop |
| `wsl --status` | 检查 WSL 状态 | 默认版本应为 2 |

## 安装 WSL2 Ubuntu 24.04

```powershell
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
wsl -d Ubuntu-24.04 -- bash -lc "uname -a"
```

| 参数 | 说明 |
|---|---|
| `--install -d Ubuntu-24.04` | 安装指定发行版 |
| `--set-default-version 2` | 新发行版默认使用 WSL2 |
| `-d Ubuntu-24.04` | 指定目标发行版 |
| `-- bash -lc` | 在 WSL 中启动登录 Bash 并执行字符串命令 |

## Ubuntu 中安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
```

生产环境建议固定 uv 版本，并通过系统包管理器或受控安装脚本部署。

## 基础服务

### 使用简化 Compose 启动 PostgreSQL 和 Redis

```powershell
Set-Location D:\work\code\web_learning\template\fastapi-architecture
docker compose -f docker-simply-compose.yml up -d fba_postgres fba_redis
docker compose -f docker-simply-compose.yml ps
```

| 参数/命令 | 说明 |
|---|---|
| `-f docker-simply-compose.yml` | 指定简化 Compose 文件 |
| `up -d` | 后台启动 |
| `fba_postgres fba_redis` | 只启动指定服务 |
| `ps` | 查看容器状态 |

### 使用已有数据库

若使用已有 PostgreSQL 或 MySQL，跳过 Compose 中的数据库服务，并在 `backend/.env` 或根目录 `.env` 中填写真实连接信息。
