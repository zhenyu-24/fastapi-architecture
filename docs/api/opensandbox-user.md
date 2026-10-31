# 沙盒工作台用户接口

前缀：

```text
/api/v1/opensandbox
```

所有接口都需要 JWT 登录。普通用户只能操作自己的沙盒；管理员可操作自己的沙盒，并可访问下面接口中归属于超级管理员的扩展能力。

## 接口总览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/overview` | 服务、限制和工作区概览 |
| GET | `/sandboxes` | 当前用户沙盒 |
| POST | `/sandboxes` | 创建沙盒 |
| GET | `/sandboxes/{sandbox_id}` | 获取沙盒状态 |
| POST | `/sandboxes/{sandbox_id}/pause` | 暂停沙盒 |
| POST | `/sandboxes/{sandbox_id}/resume` | 恢复沙盒 |
| POST | `/sandboxes/{sandbox_id}/restart` | 重启运行中的沙盒 |
| POST | `/sandboxes/{sandbox_id}/rename` | 修改沙盒显示名称 |
| DELETE | `/sandboxes/{sandbox_id}` | 删除沙盒 |
| POST | `/sandboxes/{sandbox_id}/renew` | 续期有限 TTL 沙盒 |
| GET | `/sandboxes/{sandbox_id}/files` | 列出目录 |
| GET | `/sandboxes/{sandbox_id}/file` | 读取文本文件 |
| PUT | `/sandboxes/{sandbox_id}/file` | 保存文本文件 |
| POST | `/sandboxes/{sandbox_id}/file/mkdir` | 创建目录 |
| POST | `/sandboxes/{sandbox_id}/file/rename` | 重命名或移动 |
| POST | `/sandboxes/{sandbox_id}/file/delete` | 删除文件或目录 |
| POST | `/sandboxes/{sandbox_id}/file/upload` | 上传文件 |
| GET | `/sandboxes/{sandbox_id}/file/download` | 下载文件 |
| POST | `/sandboxes/{sandbox_id}/execute` | 执行命令 |
| POST | `/sandboxes/{sandbox_id}/sessions` | 创建终端会话 |
| DELETE | `/sandboxes/{sandbox_id}/sessions/{session_id}` | 关闭终端会话 |

## 沙盒信息结构

```json
{
  "sandbox_id": "adb01f99-91ab-44bb-8ba4-7a76d987e610",
  "name": "python-lab",
  "image": "registry.example.com/opensandbox/code-interpreter:v1.1.0",
  "state": "Running",
  "reason": null,
  "message": null,
  "owner_id": "2048601269672738816",
  "owner_username": "admin",
  "created_at": "2026-10-31 13:00:00",
  "expires_at": null,
  "last_activity_time": "2026-10-31 13:10:00",
  "auto_paused": false,
  "workspace_root": "/workspace"
}
```

## 概览

```http
GET /api/v1/opensandbox/overview
```

响应字段：

| 字段 | 说明 |
|---|---|
| `service.configured` | 是否配置 OpenSandbox |
| `service.api_enabled` | 管理员是否启用了沙盒 API |
| `service.server_available` | OpenSandbox Server 是否可连通 |
| `service.available` | 平台 API 是否可用（已启用且 Server 可连通） |
| `service.version` | OpenSandbox 版本 |
| `service.message` | 当前状态说明 |
| `service.checked_time` | 健康检查时间 |
| `idle_timeout_seconds` | 空闲暂停阈值 |
| `auto_pause_enabled` | 是否启用自动暂停 |
| `default_image` | 默认沙盒镜像 |
| `workspace_root` | 默认工作目录 |
| `max_sandboxes` | 每用户最大沙盒数 |

示例：

```bash
curl http://127.0.0.1:8000/api/v1/opensandbox/overview   -H 'Authorization: Bearer <token>'
```

平台 API 暂停时，`GET /overview` 和 `GET /sandboxes` 仍可用于查看现有记录；创建、命令、文件及生命周期操作会被拒绝。

## 沙盒 CRUD

### 获取当前用户沙盒

```http
GET /api/v1/opensandbox/sandboxes
```

返回 `SandboxInfo[]`。

### 创建沙盒

```http
POST /api/v1/opensandbox/sandboxes
Content-Type: application/json
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 否 | 沙盒名称，最长 64 |
| `image` | string/null | 否 | 自定义镜像 |
| `owner_id` | integer/null | 否 | 管理员为其他用户创建时使用 |
| `owner_username` | string/null | 否 | 管理员按用户名创建时使用 |

普通用户示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/opensandbox/sandboxes   -H 'Authorization: Bearer <token>'   -H 'Content-Type: application/json'   -d '{"name":"python-lab"}'
```

管理员为指定用户创建：

```json
{
  "owner_username": "test",
  "name": "test-python"
}
```

### 获取状态

```http
GET /api/v1/opensandbox/sandboxes/{sandbox_id}
```

### 暂停

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/pause
```

暂停不会删除容器。OpenSandbox Docker runtime 使用 `docker pause`。

### 恢复

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/resume
```

### 重启

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/restart
```

OpenSandbox SDK 当前没有独立的容器 restart 接口，后端通过“暂停 → 等待 Paused → 恢复 → 等待 Running”实现重启。工作区和暂停前保留的进程状态不会因为该操作被删除。

### 重命名

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/rename
Content-Type: application/json
```

```json
{"name":"new-name"}
```

重命名会同时更新本地显示名称和 OpenSandbox 元数据字段 `fba_name`。

### 删除

```http
DELETE /api/v1/opensandbox/sandboxes/{sandbox_id}
```

删除不可通过恢复接口撤销。

### 续期

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/renew
```

| 参数 | 类型 | 范围 | 说明 |
|---|---|---|---|
| `minutes` | integer | 1-10080 | 续期分钟数 |

```json
{"minutes": 60}
```

新沙盒默认 `expires_at=null`，续期接口主要保留给显式有限 TTL 的兼容场景。

## 文件接口

所有文件路径必须位于 `OPEN_SANDBOX_WORKSPACE_ROOT`，默认 `/workspace`。

### 列出目录

```http
GET /api/v1/opensandbox/sandboxes/{sandbox_id}/files?path=/workspace
```

| 查询参数 | 说明 |
|---|---|
| `path` | 目录路径；省略时使用工作区根目录 |

### 读取文本文件

```http
GET /api/v1/opensandbox/sandboxes/{sandbox_id}/file?path=/workspace/main.py
```

响应：

```json
{
  "path": "/workspace/main.py",
  "content": "print('hello')
",
  "size": 15,
  "is_binary": false,
  "truncated": false
}
```

### 保存文本文件

```http
PUT /api/v1/opensandbox/sandboxes/{sandbox_id}/file
```

```json
{
  "path": "/workspace/main.py",
  "content": "print('hello')
"
}
```

### 创建目录

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/file/mkdir
```

```json
{"path": "/workspace/demo"}
```

### 重命名或移动

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/file/rename
```

```json
{
  "source": "/workspace/demo/old.txt",
  "destination": "/workspace/demo/new.txt"
}
```

### 删除文件或目录

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/file/delete
```

```json
{"path": "/workspace/demo/old.txt"}
```

### 上传文件

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/file/upload?path=/workspace/demo
Content-Type: multipart/form-data
```

```bash
curl -X POST 'http://127.0.0.1:8000/api/v1/opensandbox/sandboxes/<sandbox-id>/file/upload?path=/workspace/demo'   -H 'Authorization: Bearer <token>'   -F 'file=@./main.py'
```

| 参数 | 说明 |
|---|---|
| `path` | 目标目录查询参数 |
| `file` | multipart 文件字段 |

### 下载文件

```http
GET /api/v1/opensandbox/sandboxes/{sandbox_id}/file/download?path=/workspace/demo/main.py
```

返回二进制流，响应头包含 `Content-Disposition: attachment`。

## 命令执行与终端会话

### 执行命令

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/execute
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---:|---|
| `command` | string | 必填 | 1-200000 字符 |
| `cwd` | string/null | `/workspace` | 工作目录 |
| `timeout_seconds` | integer | 60 | 1-3600 秒 |
| `source` | enum | `terminal` | `terminal`、`code`、`file` |
| `session_id` | string/null | null | 持久 Bash 会话 ID |

示例：

```json
{
  "command": "python3 main.py",
  "cwd": "/workspace",
  "source": "code",
  "timeout_seconds": 600
}
```

响应：

```json
{
  "log_id": "2227800270073499648",
  "command": "pwd",
  "cwd": null,
  "stdout": "/workspace
",
  "stderr": "",
  "exit_code": 0,
  "status": "success",
  "duration_ms": 76,
  "truncated": false,
  "created_time": "2026-10-31 13:22:54"
}
```

`cwd` 仅在执行 `cd` 后返回会话的当前目录。

### 创建终端会话

```http
POST /api/v1/opensandbox/sandboxes/{sandbox_id}/sessions
```

```json
{"cwd":"/workspace"}
```

响应：

```json
{
  "session_id": "11a042dc-0d64-49d4-b692-7fb9c2f2a009",
  "cwd": "/workspace"
}
```

### 在会话中执行

请求 `/execute` 时带上：

```json
{
  "command": "cd /workspace/demo",
  "cwd": "/workspace",
  "source": "terminal",
  "session_id": "11a042dc-0d64-49d4-b692-7fb9c2f2a009",
  "timeout_seconds": 600
}
```

会话保持工作目录和 Shell 变量。`clear` 命令会被后端识别为终端清屏命令，并记录审计。

### 关闭会话

```http
DELETE /api/v1/opensandbox/sandboxes/{sandbox_id}/sessions/{session_id}
```

## 审计与错误

- 命令输出上限由 `OPEN_SANDBOX_MAX_OUTPUT_CHARS` 控制。
- `truncated=true` 表示输出已截断。
- `status` 可能为 `success`、`failed`、`error`。
- 访问其他用户沙盒返回 403。
- 沙盒不存在返回 404。
- OpenSandbox 不健康时返回 502。
- 管理员暂停平台 API 时，除概览和沙盒列表外的写操作、终端、SFTP 和代码运行返回 503。
