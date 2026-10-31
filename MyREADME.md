# FastAPI Best Architecture (fba) 项目手册

本项目二次开发自 GitHub 的
[FastAPI Best Architecture](https://github.com/fastapi-practices/fastapi_best_architecture)，
维护者为 [XiangZhenyu（GitHub @zhenyu-24）](https://github.com/zhenyu-24)。
配套前端仓库为 [vue-vben-admin](https://github.com/zhenyu-24/vue-vben-admin)，
前端 `apps/web-ele` 通过 `VITE_GLOB_API_URL` 访问本项目提供的 `/api/v1` 接口。
主要扩展包括统一文件管理、任务调度优化和 OpenSandbox 沙盒工作台；部分官方插件功能已放弃，
配套前端不再提供相应入口。原项目的 GitHub 链接和原有说明保持不变。

> 完整文档位于 [docs/README.md](docs/README.md)。部署、使用、API、架构和运维说明均已拆分到独立文档。

## 文档入口

| 文档 | 内容 |
|---|---|
| [部署指南](docs/deployment/README.md) | 环境准备、本地开发、Docker Compose、生产部署 |
| [OpenSandbox 部署](docs/deployment/opensandbox.md) | WSL2、Docker、API Key、参考配置和故障排查 |
| [用户指南](docs/user-guides/README.md) | 终端、SFTP、在线代码运行和管理员操作 |
| [API 文档](docs/api/README.md) | 认证、沙盒工作台用户接口、管理员接口 |
| [架构设计](docs/architecture/README.md) | 系统总览、后端插件、前端和沙盒生命周期 |
| [配置参考](docs/reference/configuration.md) | 环境变量、插件参数和前端配置 |
| [命令参考](docs/reference/commands.md) | fba、Docker、pnpm、WSL 和 OpenSandbox 命令 |
| [运维手册](docs/operations/README.md) | 巡检、日志、备份恢复和事件处理 |

## 快速开始

### 环境要求
- Python >= 3.12
- PostgreSQL 或 MySQL
- Redis 7+
- [uv](https://docs.astral.sh/uv/) 包管理器
- Docker Desktop（使用简化 Docker 部署或 OpenSandbox 时）
- WSL2 + Ubuntu 24.04（在 Windows 上运行 OpenSandbox Server 时）
- Node.js ^22.18 或 ^24、pnpm 11.7（前端构建时）

### 当前项目的简化 Docker 部署

项目根目录的 `.env` 同时用于 Docker Compose 变量替换和后端容器环境变量注入。默认配置为：

| 配置 | 默认值 | 说明 |
|---|---:|---|
| `SERVER_PORT` | `8000` | API 对外访问端口 |
| `SERVER_INTERNAL_PORT` | `8000` | API 容器内部监听端口 |
| `POSTGRES_PORT` | `5432` | PostgreSQL 对外映射端口 |
| `REDIS_HOST_PORT` | `6379` | Redis 对外映射端口 |
| `DATABASE_HOST` | `fba_postgres` | Compose 网络中的数据库服务名 |
| `REDIS_HOST` | `fba_redis` | Compose 网络中的 Redis 服务名 |
| `CELERY_BROKER_TYPE` | `redis` | Celery 使用 Redis 作为消息代理 |

首次启动或修改后端代码后，在本目录执行：

```powershell
docker compose -f docker-simply-compose.yml up -d --build
```

查看容器状态和日志：

```powershell
docker compose -f docker-simply-compose.yml ps
docker compose -f docker-simply-compose.yml logs -f fba_server
docker compose -f docker-simply-compose.yml logs -f fba_celery_worker
docker compose -f docker-simply-compose.yml logs -f fba_celery_beat
```

停止服务：

```powershell
docker compose -f docker-simply-compose.yml down
```

验证 API 和健康检查：

```powershell
curl.exe -fsS http://127.0.0.1:8000/health
```

健康检查使用容器内的 `FBA_SERVER_PORT`，不是写死的 `8001`。如果修改端口，只需同步修改根目录 `.env` 中的 `SERVER_PORT` 和 `SERVER_INTERNAL_PORT`，然后重新执行：

```powershell
docker compose -f docker-simply-compose.yml up -d --build
```

API、Celery Worker 和 Celery Beat 共用根目录 `.env`。不要在容器环境中设置 `CELERY_BROKER=redis`，该变量可能被 Celery 命令行解释为完整 Broker URL；本项目使用 `CELERY_BROKER_TYPE=redis`，由应用转换为 Redis Broker 地址。

### 前后端联调

前端开发服务默认运行在 `http://localhost:5777`，后端 API 默认运行在 `http://localhost:8000`。前端应用的 `VITE_GLOB_API_URL` 应设置为：

```dotenv
VITE_GLOB_API_URL=http://localhost:8000/api
```

如果修改了后端对外端口，前端环境文件中的端口也必须同步修改。前端使用 `/api` 作为接口根路径，版本路径由 API 模块统一管理。

### 初始化项目

```bash
# 1. 交互式初始化（配置 .env、创建数据库、初始化表结构和数据）
uv run fba init

# 2. 自动化初始化（一步到位）
uv run fba init --auto
```

初始化过程中会：
- 交互式配置数据库和 Redis 连接
- 自动生成 Token 密钥
- 创建/重建数据库
- 执行所有 SQL 初始化脚本（含插件）
- 清理 Redis 缓存

### 启动服务

```bash
# 开发模式（默认热重载）
fba run

# 生产模式
fba run --host 0.0.0.0 --port 8080 --no-reload --workers 4
```

### 访问文档

| 文档 | 地址 |
|---|---|
| 健康检查 | http://127.0.0.1:8000/health |
| Swagger | http://127.0.0.1:8000/docs |
| Redoc | http://127.0.0.1:8000/redoc |
| OpenAPI JSON | http://127.0.0.1:8000/openapi |

### 默认登录账号

| 账号 | 密码 |
|---|---|
| admin | 123456 |

---

## CLI 命令大全

项目基于 `cappa` 框架提供丰富的命令行工具，入口为 `fba`：

### 项目管理

| 命令 | 说明 | 示例 |
|---|---|---|
| `fba init` | 初始化项目（db + 数据） | `fba init` / `fba init --auto` |
| `fba run` | 启动 API 服务 | `fba run --port 8080 --no-reload --workers 4` |
| `fba deps` | 同步依赖 | `fba deps` / `fba deps --no-project` |
| `fba format` | 格式化代码 | `fba format` |

### Alembic 数据库迁移

| 命令 | 说明 | 示例 |
|---|---|---|
| `fba alembic revision` | 生成迁移文件 | `fba alembic revision -m "add_user_table"` |
| `fba alembic upgrade` | 升级数据库 | `fba alembic upgrade` / `fba alembic upgrade abc123` |
| `fba alembic downgrade` | 降级数据库 | `fba alembic downgrade` / `fba alembic downgrade -1` |
| `fba alembic current` | 当前迁移版本 | `fba alembic current -v` |
| `fba alembic history` | 迁移历史 | `fba alembic history` |
| `fba alembic heads` | 所有头版本 | `fba alembic heads` |

### 插件管理

| 命令 | 说明 | 示例 |
|---|---|---|
| `fba add` | 安装插件（zip/git） | `fba add --path ./plugin.zip` / `fba add --repo-url https://...` |
| `fba remove` | 卸载插件 | `fba remove`（交互选择）/ `fba remove dict` |
| `fba deps` | 同步插件依赖 | `fba deps` / `fba deps --plugin dict` |

### Celery 任务

| 命令 | 说明 | 示例 |
|---|---|---|
| `fba celery worker` | 启动 Worker | `fba celery worker -l debug` |
| `fba celery beat` | 启动定时调度 | `fba celery beat` |
| `fba celery flower` | 启动监控面板 | `fba celery flower --port 8555` |

### 代码生成

```bash
# 从已有数据库表导入业务
fba codegen import --app admin --tn your_table_name

# 交互式代码生成（CRUD API 全链路）
fba codegen
# 预览模式
fba codegen -p
```

### 其他

| 命令 | 说明 | 示例 |
|---|---|---|
| `fba <sql_file>` | 在事务中执行 SQL | `fba ./init.sql` |

---

## 项目结构

```
backend/
├── app/                          # 业务应用
│   ├── admin/                    # 管理后台
│   │   ├── api/v1/               # 路由层（API endpoints）
│   │   │   ├── auth/             #   认证（登录/登出/注册/token刷新）
│   │   │   ├── sys/              #   系统管理（用户/角色/菜单/部门/文件）
│   │   │   ├── log/              #   日志（操作日志/登录日志）
│   │   │   └── monitor/          #   监控（Redis/服务/在线用户）
│   │   ├── service/              # 业务逻辑层（Service）
│   │   ├── crud/                 # 数据访问层（CRUD）
│   │   ├── model/                # SQLAlchemy ORM 模型
│   │   ├── schema/               # Pydantic 请求/响应模型
│   │   ├── tests/                # 单元测试
│   │   └── utils/                # 业务工具（密码加密等）
│   └── task/                     # Celery 异步任务
│       ├── tasks/                #   任务定义
│       ├── service/              #   任务业务逻辑
│       ├── crud/                 #   任务数据访问
│       ├── model/                #   任务模型
│       ├── schema/               #   任务数据契约
│       └── api/v1/               #   任务 API（scheduler/result/control）
│
├── common/                       # 公共模块
│   ├── cache/                    # 缓存（本地缓存 + Redis + 发布订阅）
│   ├── exception/                # 异常定义与全局异常处理器
│   ├── response/                 # 统一响应契约与状态码
│   ├── security/                 # 安全认证（JWT / RBAC / 权限）
│   ├── socketio/                 # WebSocket (Socket.IO)
│   ├── observability/            # 可观测性（OpenTelemetry）
│   ├── context.py                # Request 上下文（ContextVar）
│   ├── dataclasses.py            # 通用数据类
│   ├── enums.py                  # 项目枚举定义
│   ├── i18n.py                   # 国际化（zh-CN / en-US）
│   ├── lifecycle.py              # 生命周期管理
│   ├── log.py                    # 日志配置
│   ├── model.py                  # SQLAlchemy 基类（MappedBase）
│   ├── pagination.py             # 分页参数与模型
│   ├── queue.py                  # 队列实现
│   └── schema.py                 # 公共 Schema
│
├── core/                         # 核心配置
│   ├── conf.py                   # 全局设置（Settings）
│   ├── path_conf.py              # 目录路径常量
│   └── registrar.py              # 应用组件注册（中间件/路由/异常处理/插件）
│
├── database/                     # 数据库
│   ├── db.py                     # SQLAlchemy 异步引擎与会话
│   └── redis.py                  # Redis 客户端封装
│
├── middleware/                   # Starlette 中间件
│   ├── access_middleware.py      # 访问日志
│   ├── i18n_middleware.py        # 国际化语言检测
│   ├── jwt_auth_middleware.py    # JWT 认证（Bearer Token）
│   ├── opera_log_middleware.py   # 操作日志记录（异步队列）
│   └── state_middleware.py       # 启动状态
│
├── plugin/                       # 插件系统
│   ├── code_generator/           # 代码生成插件（从数据库表生成 CRUD）
│   ├── config/                   # 配置管理插件
│   ├── dict/                     # 字典管理（必需插件）
│   ├── email/                    # 邮件服务插件
│   ├── notice/                   # 通知公告插件
│   ├── oauth2/                   # OAuth2 登录（GitHub/Google）
│   ├── core.py                   # 插件核心（加载/排序/钩子）
│   ├── hooks.py                  # 插件钩子
│   ├── installer.py              # 插件安装器（zip/git/frontend）
│   ├── requirements.py           # 插件依赖管理
│   ├── router.py                 # 插件路由构建
│   ├── sql.py                    # 插件 SQL 脚本管理
│   ├── validator.py              # 插件配置校验
│   └── ...
│
├── utils/                        # 工具层
│   ├── console.py                # Rich 控制台输出
│   ├── serializers.py            # MsgSpec JSON 序列化
│   ├── timezone.py               # 时区处理
│   ├── snowflake.py              # Snowflake ID 生成器
│   ├── limiter.py                # 请求频率限制
│   ├── locks.py                  # 分布式锁
│   ├── encrypt.py                # 加密工具
│   ├── openapi.py                # OpenAPI schema 定制
│   ├── sql_parser.py             # SQL 脚本解析
│   ├── build_tree.py             # 树结构构建
│   ├── demo_mode.py              # 演示模式
│   ├── trace_id.py               # Trace ID 生成
│   └── ...
│
├── locale/                       # 国际化语言文件
│   ├── zh-CN.yml                 # 中文
│   └── en-US.json                # 英文
│
├── sql/                          # 数据库初始化 SQL 脚本
├── static/                       # 静态资源
├── log/                          # 日志文件输出目录
├── tests/                        # 全局测试工具
│
├── main.py                       # 应用入口（插件准备 + 注册）
├── cli.py                        # CLI 命令定义（cappa）
├── conftest.py                   # pytest 配置
├── run.py                        # uvicorn 兼容启动入口
└── .env                          # 环境变量配置（自动生成）
```

---

## 架构分层

```
┌─────────────────────────────────────────────────┐
│                   API (Router)                   │
│   参数校验、路由分发、统一响应返回                     │
├─────────────────────────────────────────────────┤
│                 Schema (DTO)                     │
│   请求/响应数据结构定义（Pydantic）                  │
├─────────────────────────────────────────────────┤
│                Service (业务逻辑)                  │
│   业务编排、数据校验、异常处理、缓存操作               │
├─────────────────────────────────────────────────┤
│              CRUD (数据访问)                       │
│   数据库操作（继承 CRUDPlus）                       │
├─────────────────────────────────────────────────┤
│               Model (ORM 模型)                    │
│   数据库表映射（SQLAlchemy）                        │
└─────────────────────────────────────────────────┘
```

### 分层职责

| 层 | 职责 | 位置 |
|---|---|---|
| **API** | 路由注册、参数校验、调用 service 并返回响应 | `app/*/api/v1/` |
| **Schema** | Pydantic 模型，定义请求体和响应体结构 | `app/*/schema/` |
| **Service** | 业务逻辑编排，调用 crud 操作，抛出业务异常 | `app/*/service/` |
| **CRUD** | 数据库增删改查，继承 `CRUDPlus` 基类 | `app/*/crud/` |
| **Model** | SQLAlchemy ORM 模型，映射数据库表 | `app/*/model/` |

### 开发流程

```
1. 定义 Model（数据库模型）
       ↓
2. 定义 Schema（请求/响应 DTO）
       ↓
3. 定义 Router（API 路由）
       ↓
4. 编写 Service（业务逻辑）
       ↓
5. 编写 CRUD（数据库操作）
```

### 详细细节





---

## 认证与授权

### JWT Bearer Token

项目默认使用 JWT Bearer Token 认证：

```python
from backend.common.security.jwt import DependsJwtAuth

@router.get('/users', dependencies=[DependsJwtAuth])
async def get_users():
    ...
```

认证流程：
1. `POST /api/v1/auth/login` 登录获取 `access_token`
2. 请求头携带 `Authorization: Bearer <token>`
3. `JwtAuthMiddleware` 解析并验证 Token
4. `DependsJwtAuth` 依赖守卫保护路由

### Swagger 调试

1. 调 `POST /api/v1/auth/login/swagger`（Basic Auth）获取 Token
2. 点 Swagger 右上角 **Authorize** → 输入 `Bearer <token>`
3. 即可调试所有受保护接口

### 权限控制

| 机制 | 说明 | 位置 |
|---|---|---|
| **RBAC** | 基于角色的菜单/按钮权限 | `common/security/rbac.py` |
| **数据权限** | 基于角色部门/自定义规则的数据级权限 | `common/security/permission.py` |
| **超级管理员** | `DependsSuperUser` 依赖 | `common/security/jwt.py` |

---

## 统一响应格式

所有 API 响应统一格式：

```json
{
  "code": 200,
  "msg": "请求成功",
  "data": null
}
```

带业务数据时，`data` 为对应对象、数组或分页结构；失败响应仍使用相同的 `code`、`msg`、`data` 外层结构。异常处理和日志内部仍会使用 Trace ID，但成功响应契约不应默认依赖 `trace_id` 字段。

使用方法：

```python
from backend.common.response.response_schema import response_base

# 成功响应（无数据）
return response_base.success()

# 成功响应（带数据）
return response_base.success(data=GetUserDetail(...))

# 失败响应
return response_base.fail()

# 高性能响应（跳过 Pydantic 校验）
return response_base.fast_success(data=large_data)
```

---

## 数据库

### 支持类型
- PostgreSQL（推荐）
- MySQL

### 主键模式
- Snowflake ID（默认，分布式友好）
- Auto Increment

### 迁移

```bash
# 在 backend 目录下
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

或通过 CLI：
```bash
fba alembic revision -m "描述"
fba alembic upgrade
```

---

## Redis 使用

| 用途 | 前缀 | 说明 |
|---|---|---|
| Token 存储 | `fba:token:*` | JWT Token 会话管理 |
| 用户缓存 | `fba:user:*` | 已认证用户信息缓存 |
| 刷新 Token | `fba:refresh_token:*` | Refresh Token 存储 |
| 登录验证码 | `fba:login:captcha:*` | 登录验证码 |
| 用户锁定 | `fba:user:lock:*` | 登录失败锁定 |
| IP 定位 | `fba:ip:location:*` | IP 地理定位 |
| 请求限流 | `fba:limiter:*` | 请求频率限制 |
| 插件配置 | `fba:plugin:*` | 插件配置缓存 |
| 分布式锁 | `fba:lock:*` | 分布式锁 |
| 缓存失效 | `fba:cache:*` | 缓存发布订阅 |

---

## 中间件执行顺序

```
请求 → CORS → ContextVar → AccessLog → I18n → JWT Auth → State → OperaLog → 路由
```

| 中间件 | 说明 | 执行顺序（从上到下） |
|---|---|---|
| CORSMiddleware | 跨域 | 最外（最先执行） |
| ContextMiddleware | 请求上下文（request_id/ip/os/browser） | ↑ |
| AccessMiddleware | 请求访问日志 | ↑ |
| I18nMiddleware | 国际语言检测（Accept-Language） | ↑ |
| AuthenticationMiddleware | JWT Token 认证 | ↑ |
| StateMiddleware | 服务启动状态 | ↑ |
| OperaLogMiddleware | 操作日志记录（异步队列消费） | 最内（最后执行） |

---

## 插件系统

### 内置插件

| 插件 | 必需 | 说明 |
|---|---|---|
| `dict` | ✅ | 字典管理（基础数据） |
| `config` | ❌ | 配置管理 |
| `notice` | ❌ | 通知公告 |
| `code_generator` | ❌ | 代码生成器（从数据库表生成完整 CRUD） |
| `oauth2` | ❌ | OAuth2 登录（GitHub / Google） |
| `email` | ❌ | 邮件服务（验证码发送等） |
| `opensandbox` | ❌ | OpenSandbox 沙盒工作台、沙盒管理、命令审计 |

### 插件安装方式

```bash
# 从 ZIP 文件安装
fba add --path /path/to/plugin.zip

# 从 Git 仓库安装
fba add --repo-url https://github.com/xxx/plugin.git

# 安装前端插件
fba add --repo-url https://github.com/xxx/frontend-plugin.git -f
```

### 插件开发

- 插件遵循 `plugin.toml` 配置规范
- 提供 `requirements.txt` 管理依赖
- 支持 `init.sql` / `destroy.sql` 数据库脚本
- 钩子系统支持自定义启动逻辑

---

## Celery 异步任务

项目内置 Celery 集成，支持 Redis 和 RabbitMQ 作为 Broker：

```bash
# 启动 Worker
fba celery worker -l info

# 启动定时调度（需启用）
fba celery beat

# 启动监控面板
fba celery flower --port 8555 --basic-auth admin:123456
```

简化 Docker 部署默认使用 Redis：

```dotenv
CELERY_BROKER_TYPE=redis
CELERY_BROKER_REDIS_DATABASE=1
```

Worker 和 Beat 的连通性检查：

```powershell
docker compose -f docker-simply-compose.yml exec -T -w /fba/backend fba_celery_worker `
  celery -A app.task.celery inspect ping --timeout 10
```

如果日志出现 `amqp://guest@redis:5672`，说明 Celery 未读取项目配置而回退到了 AMQP；检查根目录 `.env` 是否包含 `CELERY_BROKER_TYPE=redis`，并重新构建或重启容器。

### 软删除数据清理

任务 `backend.app.task.tasks.soft_delete.tasks.delete_soft_deleted_records` 默认每天
03:30 按 `DATETIME_TIMEZONE` 时区执行，由 Beat 调度、Worker 异步运行。

- `SOFT_DELETE_RETENTION_DAYS=30`：仅物理删除软删除满 30 天的数据，最小值为 1。
- `SOFT_DELETE_CLEANUP_BATCH_SIZE=500`：每批最多处理 500 条，逐批提交。
- 自动发现已加载模型中以 `id` 为单列主键且具有 `deleted`、`deleted_time` 字段的表，
  新增符合约定的系统或插件模型无需登记清理白名单；需按项目约定导出模型供模型加载器发现。
  正常数据和未记录 `deleted_time` 的历史数据保留。
- 部门、菜单、字典类型、用户仍存在相关业务记录时先保留，关联记录清理后可在后续调度回收。
- 用户角色等关联关系、密码历史、通知接收记录、代码生成字段随所属记录一起清理。
- 文件记录及磁盘文件继续由孤立文件清理任务处理；普通文件不会因用户删除而自动删除。
- 真实外键自动参与子表优先排序及引用检查；`SET NULL` 由数据库处理。
  其他外键引用默认阻止父记录清理，明确声明的附属数据随父记录删除。
  新增逻辑外键或特殊附属数据仍需补充 Service 中的关联规则；环形引用保留待处理。
- 物理删除不可恢复。任务失败时已提交批次保留，未提交批次回滚，下次执行继续处理。

更新部署后需重启 Worker 和 Beat；任务管理中可调整执行时间或停用任务。

### 任务目录

```
backend/app/task/
├── tasks/          # 异步任务定义
├── service/        # 任务业务逻辑
├── crud/           # 任务数据访问
├── model/          # 任务 ORM 模型
├── schema/         # 任务 Schema
├── celery.py       # Celery 应用实例
├── database.py     # Celery 数据库会话管理
└── session.py      # Celery 请求会话
```

---

## 可观测性

### Prometheus + Grafana

```python
# backend/core/conf.py
GRAFANA_METRICS_ENABLE: bool = True  # 启用指标
```

- 内置 Prometheus 指标
- OpenTelemetry 链路追踪
- 指标端点：`/metrics`

### 日志

- 基于 `loguru`，异步非阻塞
- 请求访问日志（`fba_access.log`）
- 错误日志（`fba_error.log`）
- 支持自定义日志格式（含 Trace ID）

### 操作日志

- 异步队列消费，不影响请求性能
- 记录请求路径、方法、参数、耗时、IP
- 支持敏感字段脱敏（密码等）

---

## 安全特性

| 特性 | 说明 |
|---|---|
| JWT Token | 双 Token 机制（access + refresh） |
| 密码加密 | bcrypt 哈希存储 |
| 登录失败锁定 | 阈值可配，Redis 记录 |
| 密码有效期 | 可配置过期天数，到期提醒 |
| 密码历史检查 | 禁止使用最近 N 次旧密码 |
| 请求频率限制 | 基于 Redis 的滑动窗口限流 |
| 验证码 | 登录验证码（开/关可配） |
| CORS | 可配置跨域白名单 |
| 演示模式 | 限制写操作，防误删 |
| 数据权限 | 基于部门/自定义规则的行级权限 |
| SQL 注入防护 | SQLAlchemy ORM 参数化查询 |

---

## 配置参考

主要配置项（`backend/core/conf.py`），可通过 `.env` 文件覆盖：

```ini
# 环境
ENVIRONMENT='dev'                  # dev / prod

# 数据库
DATABASE_TYPE='postgresql'         # mysql / postgresql
DATABASE_HOST='127.0.0.1'
DATABASE_PORT=5432
DATABASE_USER='postgres'
DATABASE_PASSWORD='123456'

# Redis
REDIS_HOST='127.0.0.1'
REDIS_PORT=6379
REDIS_PASSWORD=''
REDIS_DATABASE=0

# Token
TOKEN_SECRET_KEY='your-secret-key'  # 初始化时自动生成
TOKEN_EXPIRE_SECONDS=86400          # access token 有效期 1 天
TOKEN_REFRESH_EXPIRE_SECONDS=604800 # refresh token 有效期 7 天

# Celery
CELERY_BROKER_TYPE='redis'         # redis / rabbitmq；容器部署使用此变量
CELERY_BROKER_REDIS_DATABASE=1
```

生产环境会自动禁用 `openapi` 和静态文件。

### Docker 配置注意事项

- 根目录 `.env` 是简化 Compose 部署的主配置文件；`deploy/backend/docker-compose/.env.server` 仅保留给原版 `docker-compose.yml` 使用。
- PostgreSQL 初始化使用 `DATABASE_SCHEMA`、`DATABASE_USER` 和 `DATABASE_PASSWORD`。已有数据卷中的数据库账号不会因修改 `.env` 自动更新。
- `SERVER_PORT` 是宿主机映射端口，`SERVER_INTERNAL_PORT` 是容器内 API 监听端口；Nginx 代理和健康检查使用后者。
- 生产环境必须替换 `TOKEN_SECRET_KEY`，并避免把真实密钥、OAuth 密钥和邮件密码提交到版本库。

---

## 常见问题

### 1. 如何新建一个业务模块？

```
backend/app/admin/
├── model/user.py              # 1. 定义 ORM 模型
├── schema/user.py             # 2. 定义 Schema
├── api/v1/sys/user.py         # 3. 定义路由
├── service/user_service.py    # 4. 编写业务逻辑
└── crud/crud_user.py          # 5. 编写 CRUD
```

### 2. 如何添加新的 API 端点？

```python
from fastapi import APIRouter, Depends
from backend.common.security.jwt import DependsJwtAuth
from backend.common.response.response_schema import response_base

router = APIRouter()

@router.get('/items', summary='获取列表', dependencies=[DependsJwtAuth])
async def get_items():
    return response_base.success(data=[...])
```

然后在 `app/admin/api/router.py` 中注册路由。

### 3. 如何获取当前登录用户？

```python
from fastapi import Request

@router.get('/profile', dependencies=[DependsJwtAuth])
async def get_profile(request: Request):
    user = request.user  # GetUserInfoWithRelationDetail
    return response_base.success(data=user)
```

### 4. 如何用代码生成器加速开发？

```bash
# 1. 从数据库表导入
fba codegen import --app admin --tn your_table

# 2. 交互式生成完整 CRUD
fba codegen
```

生成内容包括：Model、Schema、Service、CRUD、Router。

---

## 注册密码策略

- 公开接口 `GET /api/v1/auth/password-policy` 返回当前生效的密码最小长度、最大长度和特殊字符要求，无需登录。
- 接口通过现有动态配置加载器读取参数配置插件的用户安全配置，注册页面无需重建即可获取保存后的规则。
- 注册接口和修改密码复用密码复杂度校验；注册没有历史密码，因此跳过历史检查，已有用户修改密码仍执行历史检查。
- 长度和特殊字符要求分别由 `USER_PASSWORD_MIN_LENGTH`、`USER_PASSWORD_MAX_LENGTH`、`USER_PASSWORD_REQUIRE_SPECIAL_CHAR` 控制，不额外强制包含数字或英文字母。
- 参数配置插件未安装、没有配置或用户安全配置组停用时，沿用现有动态配置加载器的行为，使用进程内当前生效设置。

## 文件中心

文件插件提供超级管理员管理接口 `/api/v1/files/manage`，支持分页筛选、详情、
目录浏览、公开和私有文件下载（含 HEAD/Range）、文件内容替换、永久删除文件及数据库记录。
接口同时要求 `is_superuser`、`is_staff`，普通用户不能使用管理接口。

前端入口为系统管理 → 文件中心，路由 `/admin/files`。支持文件名、类型、
可见性和上传者用户名筛选，展示物理文件缺失及头像使用状态，上传使用原分片接口。
前端与用户、部门管理统一使用查询表单、VXE 表格及工具栏；外部链接页面同步统一。
目录浏览接口 `GET /api/v1/files/manage/browse` 按存储路径返回当前目录的子目录和分页文件，支持面包屑导航。
目录由有效文件记录生成，不列出空目录。资源上传支持选择或输入相对目录；
`GET /api/v1/files/manage/resource-folders?is_public=false` 返回已有私有资源目录，公开目录单独查询。
预检传入 `target_path`，最终按 `resource/{target_path}/YYYY/MM/DD` 存储，公开资源增加 `public/` 前缀。
`recursive=true` 返回指定目录及其子目录的匹配文件；前端有筛选条件时从根目录递归搜索，
通过 `storage_path` 展示所在路径。普通属性及时间列通过通用分页参数 `sort_by`、`sort_order`
在数据库分页前排序，字段只解析映射列及显式派生列，不拼接客户端 SQL。
`POST /api/v1/files/manage/batch-delete` 接收 `ids`，返回成功 ID 和逐项失败原因。
`PATCH /api/v1/files/manage/{file_id}/visibility` 接收 `is_public`，同步迁移公开/私有存储路径；
所属用户正在使用的头像同步更新用户地址及缓存。访问路径改变时需同步业务引用。
替换接口 `PUT /api/v1/files/manage/{file_id}/content` 接收当前管理员上传的 `source_file_id`，
保留目标文件 ID、名称、地址、可见性和上传者，重新检查同扩展名、类型、内容及大小，成功后移除来源记录。
管理范围为已入库且未软删除的文件。每周孤立文件任务报告无记录磁盘文件，
年度任务 `backend.app.task.tasks.cleanup.tasks.delete_untracked_storage` 真正删除超过
`FILE_UPLOAD_TTL_SECONDS` 的无记录文件及所有空目录，保留全部数据库记录对应文件（含软删除记录）。
空目录不受保护期限制；文件默认保护 24 小时，避免误删尚未入库的上传。
任务结果区分已删除数量、数据库记录对应的保留文件数和保护期内的保留文件数。
默认每年 1 月 1 日 04:00 按后端配置时区执行（`0 4 1 1 *`），任务调度页面可调整周期及启停。
重启 Celery Worker 和 Beat 后注册新任务及默认计划；未对真实 storage 立即执行清理。
年度任务跳过 `.chunks`、符号链接和目录联接，不删除 storage 根目录；
存储目录不可用或数据库记录路径无法解析时中止，删除失败记录日志并返回失败数。

删除会真正移除文件和记录，不经过软删除保留期。所属用户当前头像禁止删除，
磁盘删除失败保留记录；统一引用机制保护已登记的业务文件。
文件记录增加 `retention_policy`、`unreferenced_at`，`sys_file_reference` 保存业务引用关系。
新增上传默认临时文件，文件中心上传长期保留；头像和外部链接保存、替换、删除时在业务事务中同步引用。
每周任务仅回收超过上传保护期、没有引用的临时文件；最后一次引用解除后重新计算保护期。
文件详情展示保留策略、引用明细和无引用时间，不维护冗余引用次数字段。
已有数据库运行 `uv run python -m backend.plugin.files.migrate_references` 后重启 API/Worker；
迁移保留未知用途的历史文件，不会自动删除以前替换后遗留的普通图片。
详见 [文件插件说明](backend/plugin/files/README.md)。

## 沙盒工作台（OpenSandbox）

沙盒工作台由“我的沙盒”和三个工作子页面组成：

| 页面 | 路径 | 能力 |
|---|---|---|
| 我的沙盒 | `/online/my-sandbox` | 创建、启动、停止、重启、重命名、删除、搜索、筛选、列头排序并进入工作页面 |
| SSH 终端 | `/online/terminal` | 多 Bash 会话、直接输入、命令历史、`cd`、`clear` |
| SFTP 文件传输 | `/online/sftp` | 浏览、创建、上传、下载、重命名、删除 |
| 在线代码运行 | `/online/code` | 文件树、CodeMirror、可拖拽分割面板、编译和运行 |

核心设计：

- 普通用户只能访问自己的沙盒；管理员接口使用超级管理员权限。
- 浏览器不直接访问 OpenSandbox，API Key 只保存在后端。
- 沙盒以 `timeout=None` 创建，带 `opensandbox.io/manual-cleanup=true` 标签。
- 空闲 1800 秒后自动暂停，保留文件和进程状态，不按 TTL 删除。
- 旧版本有限 TTL 沙盒在到期前自动续期，避免 OpenSandbox 直接删除。
- 终端命令、代码运行和必要的文件命令写入 `sys_opensandbox_command`。
- 工作子页面不显示“沙盒管理”按钮；沙盒生命周期集中在“我的沙盒”中管理。
- 管理员通过“系统管理 → 沙盒管理”下的“沙盒实例”统一查看和管理所有用户沙盒，并可在页面中创建、同步、启动/停止/重启/重命名、复选框多选及批量执行沙盒生命周期操作；“命令审计”用于查询全部用户的命令、输出和退出码。OpenSandbox 服务器地址、全局镜像、每用户配额、空闲策略和资源限制在“参数配置 → 沙盒配置”中设置；API Key 仍只从后端 `.env` 读取。
- “沙盒实例”页面的“启用 API/暂停 API”只修改 `sys_config` 中的 `OPEN_SANDBOX_API_STATUS`，不会启动或停止 OpenSandbox Server 进程，也不会删除容器或文件。暂停时概览、列表和审计仍可读，其他操作返回 503；真正启停进程需在 WSL2、systemd 或 Docker 编排层完成。
- 资源管理器与编辑区、编辑器与输出区均支持拖拽调整比例。

相关文档：

- [OpenSandbox 部署](docs/deployment/opensandbox.md)
- [OpenSandbox 参考配置](docs/reference/opensandbox.sandbox.toml.example)
- [沙盒工作台用户指南](docs/user-guides/online-programming.md)
- [用户接口](docs/api/opensandbox-user.md)
- [管理员接口](docs/api/opensandbox-admin.md)
- [沙盒生命周期](docs/architecture/sandbox-lifecycle.md)

---

## 在线会话

会话用户 ID 以字符串返回；状态 `1` 表示在线，`0` 表示未连接。
有有效 Socket 连接或最近 180 秒内存在已认证请求时判定在线，前端每 60 秒检查会话。
列表只返回活跃会话，未连接会话不展示。关闭页面后，最近请求的活跃标记最多保留 180 秒。
退出请求携带访问令牌并撤销对应会话；同一浏览器重新登录后，验证原刷新 Cookie 或访问令牌，
撤销原会话后签发新会话，允许多端登录的用户在其他设备上的会话不受影响。
强制下线删除指定会话的访问令牌、刷新令牌及在线记录；后续认证请求立即失败，
浏览器在下次请求或定时会话检查时处理登录失效。

## ID 响应类型

统一 JSON 响应将 `id`、`*_id`、`ids`、`*_ids` 中的整数 ID 转为字符串，
包括嵌套对象、分页记录、外键及 ID 列表；自增和雪花主键采用相同规则。
数据库列及 Python 模式的模型数据保持整数，分页数量、状态和文件大小保持数字，空 ID 保持 `null`。
角色数据权限接口直接返回字符串 ID 数组，前端统一使用 `SysId = string`。

## 相关文档

- [项目完整文档](docs/README.md)
- [部署与 OpenSandbox](docs/deployment/opensandbox.md)
- [沙盒工作台用户指南](docs/user-guides/online-programming.md)
- [项目 API](docs/api/README.md)
- [项目架构](docs/architecture/README.md)
- [官方架构文档](https://fastapi-practices.github.io/fastapi_best_architecture_docs/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Celery 文档](https://docs.celeryq.dev/)
- [OpenSandbox 官方文档](https://open-sandbox.ai/)
- [Vben Admin 文档](https://doc.vben.pro/)
