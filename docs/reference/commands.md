# 命令参考

本文列出项目部署和运维常用命令、参数和示例。

## 1. fba 全局命令

```powershell
.venv\Scripts\fba.exe --help
```

| 参数/子命令 | 说明 |
|---|---|
| `--sql PATH` | 在事务中执行 SQL 文件 |
| `-h, --help` | 显示帮助 |
| `-v, --version` | 显示版本 |
| `--completion generate` | 生成 shell 补全 |
| `init` | 初始化项目 |
| `run` | 启动 API |
| `add` | 安装插件 |
| `remove` | 移除插件 |
| `deps` | 同步依赖 |
| `format` | 格式化代码 |
| `celery` | 运行 Celery |
| `codegen` | 代码生成 |
| `alembic` | 数据库迁移 |

### 执行 SQL

```powershell
.venv\Scripts\fba.exe --sql .\backend\plugin\opensandbox\sql\postgresql\init.sql
```

| 参数 | 说明 |
|---|---|
| `--sql PATH` | SQL 文件路径；执行失败应回滚事务 |

## 2. `fba init`

```powershell
.venv\Scripts\fba.exe init
.venv\Scripts\fba.exe init --auto
```

| 参数 | 说明 |
|---|---|
| 无参数 | 交互式配置 `.env`、数据库和 Redis |
| `--auto` | 自动创建环境、安装依赖、创建数据库并初始化表 |

示例：测试环境快速初始化：

```powershell
.venv\Scripts\fba.exe init --auto
```

## 3. `fba run`

```powershell
.venv\Scripts\fba.exe run [--host HOST] [--port PORT] [--no-reload] [--workers N]
```

| 参数 | 默认值 | 说明 | 示例 |
|---|---:|---|---|
| `--host HOST` | `127.0.0.1` | 监听地址 | `--host 0.0.0.0` |
| `--port PORT` | `8000` | 监听端口 | `--port 8080` |
| `--no-reload` | false | 关闭热重载 | `--no-reload` |
| `--workers N` | `1` | 工作进程数，必须配合 `--no-reload` | `--workers 4` |

开发：

```powershell
.venv\Scripts\fba.exe run
```

生产：

```powershell
.venv\Scripts\fba.exe run --host 0.0.0.0 --port 8000 --no-reload --workers 4
```

## 4. `fba add`

```powershell
.venv\Scripts\fba.exe add --path .\plugin.zip
.venv\Scripts\fba.exe add --repo-url https://github.com/example/plugin.git
```

| 参数 | 说明 | 示例 |
|---|---|---|
| `--path PATH` | ZIP 插件路径 | `--path .\opensandbox.zip` |
| `--repo-url URL` | Git 仓库 | `--repo-url https://github.com/example/plugin.git` |
| `-f, --frontend` | 安装前端插件 | `--repo-url ... -f` |
| `--no-sql` | 不自动执行插件 SQL | `--no-sql` |
| `--db-type` | `mysql` 或 `postgresql` | `--db-type postgresql` |
| `--pk-type` | `autoincrement` 或 `snowflake` | `--pk-type snowflake` |

## 5. `fba remove`

```powershell
.venv\Scripts\fba.exe remove opensandbox
```

| 参数 | 说明 |
|---|---|
| `PLUGIN` | 要移除的插件名称；省略时交互选择 |
| `--no-sql` | 不执行 destroy SQL |

## 6. `fba deps`

```powershell
.venv\Scripts\fba.exe deps
.venv\Scripts\fba.exe deps --plugin opensandbox
```

| 参数 | 说明 |
|---|---|
| `--plugin PLUGIN` | 只同步指定插件 |
| `--no-project` | 跳过项目依赖 |
| `--no-plugin` | 跳过插件依赖 |

## 7. `fba format`

```powershell
.venv\Scripts\fba.exe format
```

无额外参数，执行项目代码格式化。

## 8. Celery

```powershell
.venv\Scripts\fba.exe celery worker -l info
.venv\Scripts\fba.exe celery beat -l info
.venv\Scripts\fba.exe celery flower --port 8555 --basic-auth admin:123456
```

### `celery worker`

| 参数 | 默认 | 说明 |
|---|---|---|
| `-l, --log-level` | `info` | `info` 或 `debug` |

### `celery beat`

| 参数 | 默认 | 说明 |
|---|---|---|
| `-l, --log-level` | `info` | `info` 或 `debug` |

### `celery flower`

| 参数 | 默认 | 说明 |
|---|---|---|
| `--port PORT` | `8555` | 监控页面端口 |
| `--basic-auth USER:PASS` | `admin:123456` | 登录凭据 |
| `--read-only` | true | 只读模式 |
| `--no-read-only` | false | 允许管理操作 |

## 9. Alembic

### 生成迁移

```powershell
.venv\Scripts\fba.exe alembic revision -m "add opensandbox tables"
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--autogenerate` | true | 自动比较模型 |
| `-m, --message` | 空 | 迁移说明 |

### 升级

```powershell
.venv\Scripts\fba.exe alembic upgrade
.venv\Scripts\fba.exe alembic upgrade --revision abc123
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--revision REV` | `head` | 目标版本 |

### 降级

```powershell
.venv\Scripts\fba.exe alembic downgrade
.venv\Scripts\fba.exe alembic downgrade --revision abc123
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--revision REV` | `-1` | 目标版本或回退步数 |

### 其他

```powershell
.venv\Scripts\fba.exe alembic current -v
.venv\Scripts\fba.exe alembic history
.venv\Scripts\fba.exe alembic heads
```

## 10. 代码生成

```powershell
.venv\Scripts\fba.exe codegen
.venv\Scripts\fba.exe codegen -p
.venv\Scripts\fba.exe codegen import --app admin --tn your_table
```

| 参数/子命令 | 说明 |
|---|---|
| `-p, --preview` | 只预览，不写文件 |
| `import` | 导入业务表和字段 |
| `--app` | 目标应用 |
| `--tn` | 表名 |

## 11. Docker Compose

```powershell
docker compose -f docker-simply-compose.yml up -d --build
```

| 参数 | 说明 |
|---|---|
| `-f FILE` | 指定 Compose 文件 |
| `up` | 创建并启动 |
| `-d` | 后台 |
| `--build` | 构建镜像 |
| `--force-recreate` | 强制重建容器 |
| `--remove-orphans` | 删除不属于当前 Compose 的旧容器 |

常用：

```powershell
docker compose -f docker-simply-compose.yml ps
docker compose -f docker-simply-compose.yml logs -f fba_server
docker compose -f docker-simply-compose.yml restart fba_server
docker compose -f docker-simply-compose.yml stop
docker compose -f docker-simply-compose.yml down
docker compose -f docker-simply-compose.yml config
```

`down -v` 会删除数据卷，仅在明确需要清空数据时执行。

## 12. Docker

```powershell
docker ps -a
docker images
docker logs -f <container>
docker inspect <container>
docker stats
```

| 命令 | 说明 |
|---|---|
| `docker ps -a` | 查看所有容器 |
| `docker images` | 查看镜像 |
| `docker logs -f` | 跟踪日志 |
| `docker inspect` | 查看完整配置和标签 |
| `docker stats` | 查看实时资源占用 |

沙盒检查：

```powershell
docker ps -a --filter "label=fba_managed=true" --format "table {{.Names}}	{{.Status}}"
docker inspect <container> --format "{{json .Config.Labels}}"
```

## 13. 前端 pnpm

```powershell
pnpm install --frozen-lockfile
pnpm dev:ele
pnpm build:ele
pnpm -F @vben/web-ele run typecheck
pnpm -F @vben/web-ele run preview
```

| 命令/参数 | 说明 |
|---|---|
| `--frozen-lockfile` | 不更新锁文件 |
| `dev:ele` | 启动 web-ele |
| `build:ele` | 构建 web-ele |
| `-F @vben/web-ele run` | 在指定 workspace 中执行脚本 |
| `preview` | 预览生产构建 |

## 14. OpenSandbox 与 uv

```bash
cd ~/projects/opensandbox/OpenSandbox
uv sync
OPENSANDBOX_INSECURE_SERVER=YES uv run opensandbox-server
OPENSANDBOX_SERVER_API_KEY='your-api-key' uv run opensandbox-server
```

| 命令/参数 | 说明 |
|---|---|
| `uv sync` | 安装 OpenSandbox 依赖 |
| `OPENSANDBOX_INSECURE_SERVER=YES` | 无 API Key 时确认风险 |
| `OPENSANDBOX_SERVER_API_KEY` | 覆盖 Server API Key |
| `uv run opensandbox-server` | 启动 Server |

### 拉取镜像

```bash
docker pull opensandbox/execd:v1.1.0
docker pull sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.1.0
```

### 验证

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/version
```

## 15. WSL

```powershell
wsl --status
wsl --list --verbose
wsl -d Ubuntu-24.04 -u xzy -- bash -lc "cd ~/projects/opensandbox/OpenSandbox && uv sync"
wsl -d Ubuntu-24.04 -u xzy -- bash -lc "tail -n 100 /tmp/opensandbox-server.log"
```

| 参数 | 说明 |
|---|---|
| `-d DISTRO` | 指定发行版 |
| `-u USER` | 指定 Linux 用户 |
| `-- bash -lc` | 登录 Bash 执行命令 |
| `--list --verbose` | 查看发行版和 WSL 版本 |
| `--status` | 查看 WSL 状态 |

## 16. 反向代理与健康检查

```powershell
curl.exe -fsS http://127.0.0.1:8000/health
curl.exe -fsS http://127.0.0.1:8080/health
curl.exe -fsS http://127.0.0.1:5777
```

| 参数 | 说明 |
|---|---|
| `-f` | HTTP 错误时返回非零 |
| `-sS` | 静默但显示错误 |
| `-v` | 输出请求和响应详情 |
| `-X METHOD` | 指定 HTTP 方法 |
| `-H` | 添加请求头 |
| `-d` | 请求体 |
| `-F` | multipart 文件字段 |

## 17. 诊断顺序

```powershell
Get-Date
docker ps -a
curl.exe -fsS http://127.0.0.1:8080/health
curl.exe -fsS http://127.0.0.1:8000/health
curl.exe -fsS http://127.0.0.1:5777
```

返回非 200 时，按 [故障排查](../deployment/troubleshooting.md) 继续。
