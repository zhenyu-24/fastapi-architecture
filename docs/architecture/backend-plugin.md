# 后端插件

## 插件类型

OpenSandbox 是 fba 应用级插件：

```toml
[app]
router = ['v1']
```

目录：

```text
backend/plugin/opensandbox/
├── api/v1/
│   ├── sandbox.py
│   └── admin.py
├── crud/
│   ├── crud_sandbox.py
│   └── crud_command_log.py
├── model/
│   ├── sandbox.py
│   └── command_log.py
├── schema/sandbox.py
├── service/
│   ├── sandbox_service.py
│   ├── command_service.py
│   ├── file_service.py
│   └── control_service.py
├── utils/client.py
├── sql/{mysql,postgresql}/
├── hooks.py
├── plugin.toml
├── requirements.txt
└── README.md
```

## 分层职责

| 层 | 责任 |
|---|---|
| API | JWT、超级管理员依赖、路径/查询参数、响应包装 |
| Schema | 创建、文件、命令、审计、服务状态 DTO |
| Service | 沙盒归属、OpenSandbox 调用、权限、审计、生命周期 |
| CRUD | `sys_opensandbox` 和 `sys_opensandbox_command` 查询 |
| Model | SQLAlchemy ORM 表定义 |
| Utils | OpenSandbox SDK 适配、连接配置、异常包装 |
| Hooks | 插件 lifespan 与空闲暂停循环 |
| SQL | PostgreSQL/MySQL 初始化与卸载脚本 |

## 数据表

### `sys_opensandbox`

核心字段：

- `sandbox_id`：OpenSandbox 沙盒 ID，唯一。
- `user_id`、`username`：归属用户。
- `status`：Running、Paused、Pending、Terminated。
- `last_activity_time`：空闲判断依据。
- `paused_time`：最近暂停时间。
- `expires_at`：OpenSandbox 过期时间；新沙盒为 null。
- `deleted`、`deleted_time`：软删除。

### `sys_opensandbox_command`

核心字段：

- 执行用户、沙盒、来源、会话 ID。
- 命令、工作目录。
- stdout、stderr、退出码、状态。
- 耗时和是否截断。
- 创建时间。

## 权限模型

普通用户接口通过 `_identity()` 获取当前用户，并在 `sandbox_service.ensure_access()` 中校验：

```text
record.user_id == current_user.id
```

管理员接口路由器直接依赖：

```python
DependsSuperUser
```

并通过 `is_admin=True` 跳过归属限制，但仍保留资源存在性校验。

## OpenSandbox SDK 适配层

`utils/client.py` 封装：

- `health()`：请求 `/health` 和 `/version`。
- `create_sandbox()`：`timeout=None`，写入 `fba_managed=true` 元数据。
- `pause_sandbox()`、`resume_sandbox()`、`kill_sandbox()`。
- `run_command()`：普通命令或 `run_in_session()`。
- `files.*`：列目录、读、写、移动、删除、流式下载。
- `renew_sandbox()`：旧有限 TTL 续期。

`ConnectionConfig` 使用：

- `domain=OPEN_SANDBOX_URL`
- `api_key=OPEN_SANDBOX_API_KEY`
- `use_server_proxy=True`

## 空闲暂停循环

`hooks.py` 启动 `opensandbox-auto-pause` 后台任务：

1. 同步带 `fba_managed=true` 的远端沙盒。
2. 对即将到期的旧有限 TTL 沙盒续期。
3. 查询超过空闲阈值的 Running 沙盒。
4. 调用 OpenSandbox pause。
5. 写入本地状态 `Paused`。

循环使用 `asyncio`，退出时取消任务。

## 配置来源

优先级：

```text
系统环境变量 -> backend/.env -> plugin.toml [settings] -> conf.py 默认值
```

敏感值放在 `.env`：

- API Key

OpenSandbox URL 可由参数配置覆盖；沙盒 API 开关保存在 `sys_config` 的 `OPEN_SANDBOX_API_STATUS`。暂停时写操作返回 503，概览、列表和审计保留只读访问。

非敏感默认值放在 `plugin.toml`：

- 镜像、工作区、资源限制、空闲时间、文件大小限制。

## 测试与格式

```powershell
.venv\Scripts\ruff.exe check backend\plugin\opensandbox
.venv\Scripts\ruff.exe format --check backend\plugin\opensandbox
```

建议在功能变更后：

1. 执行 ruff。
2. 启动 fba。
3. 创建沙盒。
4. 测试终端 `cd` 和 `clear`。
5. 测试文件上传下载。
6. 检查审计表。
7. 等待或缩短空闲阈值，验证暂停。
