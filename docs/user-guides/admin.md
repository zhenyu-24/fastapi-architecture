# 管理员操作

## 权限要求

管理接口使用 `DependsSuperUser`，只有超级管理员可以访问。普通用户访问会得到 403。

## 沙盒管理

管理员可以：

- 查看所有用户沙盒
- 按用户、状态或名称筛选
- 为指定用户创建沙盒
- 暂停、恢复、重启、续期、删除任意沙盒
- 同步 OpenSandbox 远端沙盒到本地数据库
- 查看全部命令审计
- 启用或暂停沙盒 API（不会停止 OpenSandbox 进程）

“系统管理 → 沙盒管理”包含两个子页面：

- “沙盒实例”，路径 `/admin/sandbox/instances`：全部用户沙盒分页查询、用户名/状态/名称筛选、列排序、创建、同步、沙盒 API 启用/暂停，以及沙盒启动、停止、重启、重命名、删除。表格支持复选框多选和批量操作。
- “命令审计”，路径 `/admin/sandbox/audit`：按用户、沙盒、命令、状态和时间查询全部命令，并查看 stdout、stderr、退出码、工作目录和耗时。

## 全局沙盒配置

管理员可在“系统管理 → 参数配置 → 沙盒配置”中调整：

- OpenSandbox 服务器地址（API Key 仍只从后端 `.env` 读取）
- 默认镜像
- 全局每用户最大沙盒数
- 空闲暂停时间和自动暂停开关
- 默认 CPU、内存
- 命令输出、上传文件和文本预览限制

用户配额默认采用全局值，没有单独的用户配额页面。配置保存后对新创建或后续操作生效。

## 为其他用户创建沙盒

请求示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/opensandbox/admin/sandboxes   -H 'Authorization: Bearer <admin-token>'   -H 'Content-Type: application/json'   -d '{"owner_username":"test","name":"test-python","image":"sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.1.0"}'
```

参数：

| 参数 | 说明 |
|---|---|
| `owner_id` | 目标用户 ID，二选一 |
| `owner_username` | 目标用户名，二选一 |
| `name` | 沙盒名称 |
| `image` | 可选镜像，留空使用默认镜像 |

## 删除沙盒

删除会调用 OpenSandbox kill/delete 接口并软删除本地记录。该操作不可通过“启动”恢复，必须重新创建。

删除前确认：

- 用户已经备份 `/workspace` 文件。
- 没有正在执行的命令。
- 不是误操作的目标沙盒。

## 命令审计

管理员可以按以下条件查询：

- 用户 ID 或用户名
- 沙盒 ID
- 命令关键词
- 状态
- 开始/结束时间

审计详情包含完整命令、stdout、stderr、退出码、工作目录、来源和耗时。

## 沙盒 API 启用与暂停

“启用 API”和“暂停 API”只修改 `sys_config` 中的 `OPEN_SANDBOX_API_STATUS` 开关，不执行系统命令，也不会启动或停止 OpenSandbox Server 进程。

- 暂停后，创建、同步、终端、SFTP、代码运行、暂停/恢复/重启/删除等接口会返回 HTTP 503“沙盒 API 已被管理员暂停”；
- 概览、沙盒列表和命令审计仍可访问；
- 沙盒、容器和 `/workspace` 文件不会被删除；
- 启用后还需要 OpenSandbox Server 健康检查通过，前端才会显示“可用”。

只有管理员可以操作该开关。真正启动或停止 OpenSandbox Server 需要在 WSL2、systemd 或 Docker 编排层单独执行。
