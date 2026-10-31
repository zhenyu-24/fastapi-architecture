# 沙盒工作台管理员接口

前缀：

```text
/api/v1/opensandbox/admin
```

全部接口要求超级管理员权限。普通用户访问返回 403。

## 接口总览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/overview` | 管理概览 |
| GET | `/sandboxes` | 分页获取全部沙盒 |
| POST | `/sandboxes` | 为指定用户创建沙盒 |
| POST | `/sandboxes/{sandbox_id}/pause` | 暂停任意沙盒 |
| POST | `/sandboxes/{sandbox_id}/resume` | 恢复任意沙盒 |
| POST | `/sandboxes/{sandbox_id}/restart` | 重启任意运行中的沙盒 |
| POST | `/sandboxes/{sandbox_id}/rename` | 修改任意沙盒显示名称 |
| DELETE | `/sandboxes/{sandbox_id}` | 删除任意沙盒 |
| POST | `/sandboxes/{sandbox_id}/renew` | 续期任意沙盒 |
| POST | `/sync` | 同步远端沙盒到本地 |
| GET | `/users` | 用户选项 |
| GET | `/commands` | 分页查询命令审计 |
| GET | `/commands/{pk}` | 命令审计详情 |
| POST | `/service/start` | 启用沙盒 API |
| POST | `/service/stop` | 暂停沙盒 API |

## 通用请求头

```http
Authorization: Bearer <admin-access-token>
Content-Type: application/json
```

## 管理概览

```http
GET /api/v1/opensandbox/admin/overview
```

响应：

```json
{
  "service": {
    "configured": true,
    "api_enabled": true,
    "server_available": true,
    "available": true,
    "version": "1.2.0",
    "message": "服务可用"
  },
  "total_sandboxes": 3,
  "running_sandboxes": 2,
  "paused_sandboxes": 1,
  "total_users": 2,
  "total_commands": 128
}
```

## 分页查询沙盒

```http
GET /api/v1/opensandbox/admin/sandboxes?page=1&page_size=20
```

| 参数 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `page` | integer | 页码 | `page=1` |
| `page_size` | integer | 每页数量 | `page_size=20` |
| `user_id` | integer | 归属用户 ID | `user_id=2048601269672738816` |
| `username` | string | 用户名模糊匹配 | `username=test` |
| `status` | string | 沙盒状态 | `status=Running` |
| `keyword` | string | 沙盒名称关键词 | `keyword=python` |

bash 示例：

```bash
curl -G http://127.0.0.1:8000/api/v1/opensandbox/admin/sandboxes   -H 'Authorization: Bearer <admin-token>'   --data-urlencode 'page=1'   --data-urlencode 'page_size=20'   --data-urlencode 'status=Running'
```

## 为指定用户创建沙盒

```http
POST /api/v1/opensandbox/admin/sandboxes
```

请求：

```json
{
  "owner_id": "2049946297615646720",
  "owner_username": "test",
  "name": "test-python",
  "image": null
}
```

`owner_id` 与 `owner_username` 至少提供一个，同时提供时按后端解析结果处理。

```bash
curl -X POST http://127.0.0.1:8000/api/v1/opensandbox/admin/sandboxes   -H 'Authorization: Bearer <admin-token>'   -H 'Content-Type: application/json'   -d '{"owner_username":"test","name":"test-python"}'
```

## 暂停、恢复、重启、删除

| 接口 | 方法 | 说明 |
|---|---|---|
| `/sandboxes/{sandbox_id}/pause` | POST | 暂停并保留状态 |
| `/sandboxes/{sandbox_id}/resume` | POST | 恢复运行 |
| `/sandboxes/{sandbox_id}/restart` | POST | 暂停后立即恢复 |
| `/sandboxes/{sandbox_id}/rename` | POST | 修改本地名称和远端 metadata |
| `/sandboxes/{sandbox_id}` | DELETE | 删除容器并软删除记录 |

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/opensandbox/admin/sandboxes/<sandbox-id>/pause   -H 'Authorization: Bearer <admin-token>'
```

## 续期

```http
POST /api/v1/opensandbox/admin/sandboxes/{sandbox_id}/renew
```

```json
{"minutes":1440}
```

| 参数 | 范围 | 说明 |
|---|---:|---|
| `minutes` | 1-10080 | 续期分钟数，最多 7 天 |

## 同步远端沙盒

```http
POST /api/v1/opensandbox/admin/sync
```

仅同步带 `fba_managed=true` 元数据的沙盒。响应为同步数量：

```json
{"code":200,"msg":"请求成功","data":4}
```

## 用户选项

```http
GET /api/v1/opensandbox/admin/users
```

返回可用于创建沙盒的用户列表：

```json
[
  {"id":"2049946297615646720","username":"test","nickname":"用户66666"}
]
```

## 命令审计

### 查询列表

```http
GET /api/v1/opensandbox/admin/commands?page=1&page_size=20
```

| 参数 | 说明 |
|---|---|
| `page` | 页码 |
| `page_size` | 每页数量 |
| `user_id` | 执行用户 ID |
| `username` | 用户名模糊匹配 |
| `sandbox_id` | 沙盒 ID |
| `keyword` | 命令关键词 |
| `status` | `success`、`failed`、`error` |
| `start_time` | ISO 时间 |
| `end_time` | ISO 时间 |

```bash
curl -G http://127.0.0.1:8000/api/v1/opensandbox/admin/commands   -H 'Authorization: Bearer <admin-token>'   --data-urlencode 'username=test'   --data-urlencode 'status=failed'   --data-urlencode 'page=1'
```

### 查询详情

```http
GET /api/v1/opensandbox/admin/commands/{pk}
```

响应包含：

- `command`
- `stdout`
- `stderr`
- `exit_code`
- `cwd`
- `source`
- `session_id`
- `duration_ms`
- `truncated`

普通用户没有该接口权限。

## 沙盒 API 启用与暂停

```http
POST /api/v1/opensandbox/admin/service/start
POST /api/v1/opensandbox/admin/service/stop
```

无请求体。接口只修改 `sys_config` 中 `SANDBOX` 类型的 `OPEN_SANDBOX_API_STATUS`，不会启动或停止 OpenSandbox Server 进程。路径沿用历史名称，`service/start` 表示启用平台 API，`service/stop` 表示暂停平台 API。

成功响应示例：

```json
{
  "success": true,
  "output": "沙盒 API 已暂停；OpenSandbox Server 进程未被停止。",
  "status": {
    "configured": true,
    "api_enabled": false,
    "server_available": true,
    "available": false,
    "version": "1.2.0",
    "url": "http://127.0.0.1:8080",
    "api_key_configured": false,
    "start_command_configured": false,
    "stop_command_configured": false,
    "message": "管理员已暂停沙盒 API；OpenSandbox Server 进程仍在运行",
    "checked_time": "2026-10-31 16:00:00"
  }
}
```

字段说明：

- `api_enabled`：管理员开关是否启用；
- `server_available`：OpenSandbox Server 健康检查是否通过；
- `available`：只有 `api_enabled && server_available` 时才为 `true`；
- `output`：本次开关操作说明，不再是系统命令输出。

`service/start` 的 `success=true` 只表示平台开关已写入 `1`，不表示 Server 健康检查通过；若进程不可达，`server_available=false`、`available=false`，`output` 会提示检查 Server 进程和服务器地址。

暂停后，创建、同步、终端、SFTP、代码运行和沙盒生命周期接口返回 HTTP 503：

```json
{
  "code": 503,
  "msg": "沙盒 API 已被管理员暂停，请在“沙盒实例”页面点击“启用 API”恢复",
  "data": null
}
```

概览、沙盒列表和命令审计仍可访问。`status.start_command_configured` 和 `status.stop_command_configured` 只是旧配置兼容字段，当前版本不会执行对应命令。

## 安全要求

- 不向普通用户开放管理员接口。
- 不在日志中打印 API Key、Token、密码。
- 删除沙盒前确认归属用户和数据备份。
- 沙盒 API 开关只允许管理员操作；真正启停 OpenSandbox 进程应在系统层单独完成。
- 生产环境应限制管理员来源 IP 或启用更强的 MFA/审计措施。
