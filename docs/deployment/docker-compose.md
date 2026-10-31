# Docker Compose 部署

## 两个 Compose 文件

| 文件 | 定位 | 建议 |
|---|---|---|
| `docker-simply-compose.yml` | 简化单机部署，PostgreSQL + Redis + API + Celery | 当前项目推荐 |
| `docker-compose.yml` | 完整部署，包含 RabbitMQ、Flower、Grafana、Loki、Tempo 等 | 需要完整可观测性时使用 |

首次部署优先使用 `docker-simply-compose.yml`。

## 1. 配置根目录 `.env`

`docker-simply-compose.yml` 使用根目录 `.env` 同时做 Compose 变量替换和后端容器环境注入。关键配置：

```dotenv
TZ=Asia/Shanghai
SERVER_PORT=8000
SERVER_INTERNAL_PORT=8000
POSTGRES_PORT=5432
REDIS_HOST_PORT=6379
DATABASE_SCHEMA=fba
DATABASE_USER=postgres
DATABASE_PASSWORD=replace-with-a-strong-password
DATABASE_HOST=fba_postgres
DATABASE_PORT=5432
REDIS_HOST=fba_redis
REDIS_PORT=6379
REDIS_PASSWORD=''
TOKEN_SECRET_KEY=replace-with-a-random-secret
CELERY_BROKER_TYPE=redis
```

若启用 OpenSandbox，还必须补充：

```dotenv
OPEN_SANDBOX_ENABLED=true
OPEN_SANDBOX_URL=http://host.docker.internal:8080
OPEN_SANDBOX_API_KEY=your-api-key
OPEN_SANDBOX_AUTO_PAUSE_ENABLED=true
OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS=1800
OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED=true
```

> 管理员的“启用 API/暂停 API”只切换平台开关，不启动或停止 OpenSandbox Server。容器编排层应单独管理 Server 进程；`OPEN_SANDBOX_SERVICE_START_COMMAND` 和 `OPEN_SANDBOX_SERVICE_STOP_COMMAND` 已废弃，当前版本不会执行。

## 2. 启动

```powershell
docker compose -f docker-simply-compose.yml up -d --build
```

参数说明：

| 参数 | 说明 |
|---|---|
| `-f FILE` | 指定 Compose 文件 |
| `up` | 创建并启动服务 |
| `-d` | 后台运行 |
| `--build` | 启动前重新构建镜像 |

## 3. 查看状态与日志

```powershell
docker compose -f docker-simply-compose.yml ps
docker compose -f docker-simply-compose.yml logs -f fba_server
docker compose -f docker-simply-compose.yml logs -f fba_celery_worker
docker compose -f docker-simply-compose.yml logs -f fba_celery_beat
```

| 参数 | 说明 |
|---|---|
| `ps` | 查看容器状态 |
| `logs` | 查看日志 |
| `-f` | 持续跟踪日志 |
| `fba_server` | 只查看 API 容器 |

## 4. 健康检查

```powershell
curl.exe -fsS http://127.0.0.1:8000/health
```

容器内健康检查使用 `FBA_SERVER_PORT`，该值来自 `SERVER_INTERNAL_PORT`。宿主机端口和容器内部端口必须分别配置：

- `SERVER_PORT`：浏览器访问的端口。
- `SERVER_INTERNAL_PORT`：API 在容器内监听的端口。

## 5. 初始化行为

`fba_server` 容器首次启动时会检查 `sys_user` 表：

- 数据库未初始化：执行模型建表和插件 SQL。
- 数据库已初始化：跳过初始化，直接启动 API。

因此不要在没有备份的情况下删除 PostgreSQL 数据卷。

## 6. 常用维护命令

```powershell
# 停止但保留容器和数据卷
docker compose -f docker-simply-compose.yml stop

# 停止并删除容器，保留命名数据卷
docker compose -f docker-simply-compose.yml down

# 查看配置解析结果
docker compose -f docker-simply-compose.yml config

# 重启 API
docker compose -f docker-simply-compose.yml restart fba_server

# 只重建 API
docker compose -f docker-simply-compose.yml up -d --build fba_server
```

`down -v` 会删除数据卷，只能在确认不需要历史数据时使用。

## 7. Docker 内访问 OpenSandbox 的网络选择

| OpenSandbox 位置 | 推荐 `OPEN_SANDBOX_URL` |
|---|---|
| Windows 宿主机 | `http://host.docker.internal:8080` |
| WSL2 + Docker Desktop 端口转发 | `http://host.docker.internal:8080` |
| 同一 Compose 网络中的服务 | `http://opensandbox-server:8080` |
| 独立服务器 | `http://10.0.0.20:8080` |

若使用 `host.docker.internal`，确认 Docker Desktop 已启用对应主机映射；Linux 原生 Docker 可能需要在 Compose 中增加 `extra_hosts: ["host.docker.internal:host-gateway"]`。
