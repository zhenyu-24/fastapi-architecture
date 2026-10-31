# 系统总览

## 总体结构

```text
+-----------------------------+
| Vue Vben Admin / web-ele    |
| 沙盒工作台页面               |
+--------------+--------------+
               | HTTP /api/v1
               v
+-----------------------------+
| FastAPI fba                 |
| - JWT / RBAC                |
| - OpenSandbox 插件          |
| - 命令审计                  |
+----+-------------+----------+
     |             |
     | SQL         | OpenSandbox SDK
     v             v
+---------+   +-----------------------+
| DB      |   | OpenSandbox Server    |
| PG/MySQL|   | - lifecycle API       |
| Redis   |   | - proxy / runtime     |
+---------+   +-----------+-----------+
                          |
                          v
                  +------------------+
                  | Docker sandboxes |
                  | execd + image    |
                  +------------------+
```

## 职责划分

### 前端

- 展示沙盒列表、服务状态和操作按钮。
- 维护终端标签和当前工作目录显示。
- 提供 SFTP 页面与可拖拽代码工作台。
- 不直接连接 OpenSandbox，不接触 API Key。

### 后端

- 校验 JWT 和用户身份。
- 限制普通用户只能访问自己的沙盒。
- 管理员接口使用超级管理员依赖。
- 通过 OpenSandbox Python SDK 调用 lifecycle/execd API。
- 读取 `sys_config` 中的 `OPEN_SANDBOX_API_STATUS`；暂停时拒绝写操作，保留概览、列表和审计的只读访问。
- 在创建、命令、文件操作时记录活动时间。
- 执行空闲暂停巡检。
- 写入命令审计日志。

### OpenSandbox Server

- 创建、暂停、恢复、删除沙盒容器。
- 维护沙盒生命周期状态。
- 代理 execd 命令和文件接口。
- 使用 Docker runtime 启动沙盒容器。

### 数据库与 Redis

- `sys_opensandbox`：沙盒归属、状态、活动时间、过期时间。
- `sys_opensandbox_command`：命令审计。
- Redis：fba 原有会话、缓存和 Celery 任务。

## 关键请求流

### 创建沙盒

```text
Browser -> POST /opensandbox/sandboxes
  -> ensure JWT
  -> resolve owner
  -> check per-user max
  -> OpenSandbox Sandbox.create(timeout=None)
  -> write sys_opensandbox
  -> return SandboxInfo
```

### 终端执行

```text
Browser -> POST /execute
  -> ensure_access
  -> find/create Bash session
  -> OpenSandbox run_in_session
  -> collect stdout/stderr
  -> write sys_opensandbox_command
  -> update last_activity_time
  -> return CommandResult
```

### 平台 API 开关

```text
Browser -> POST /opensandbox/admin/service/stop
  -> ensure superuser
  -> write sys_config OPEN_SANDBOX_API_STATUS=0
  -> read-only overview/list/audit remain available
  -> create/execute/file/lifecycle -> 503
```

接口路径沿用历史名称，`service/start` 表示启用平台 API，`service/stop` 表示暂停平台 API，二者都不会启动或停止 OpenSandbox Server 进程。

### 空闲暂停

```text
Plugin lifespan
  -> every 60 seconds
  -> sync managed remote sandboxes
  -> protect legacy finite TTL
  -> find Running records idle >= 1800s
  -> OpenSandbox pause
  -> write status=Paused
```

## 数据边界

| 数据 | 所属系统 | 是否可自动删除 |
|---|---|---|
| 沙盒文件 | OpenSandbox 容器 `/workspace` | 仅显式删除沙盒或容器丢失 |
| 沙盒归属记录 | fba 数据库 | 管理员删除时软删除 |
| 命令审计 | fba 数据库 | 按运维策略清理 |
| API Key | 后端环境变量 | 不进入前端和审计 |
| 前端终端显示 | 浏览器内存 | 刷新即清空 |

## 扩展点

- 新增语言执行规则：前端 `languages` 和命令构建逻辑。
- 新增文件操作：后端 FileService + OpenSandbox files SDK + 前端 API。
- 新增管理员功能：Admin API + 前端系统管理页面。
- 更换沙盒运行时：仅在 OpenSandbox Server 配置层调整，fba 接口保持不变。
