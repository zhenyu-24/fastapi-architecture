# 安全设计

## 认证

- 浏览器使用 JWT Bearer Token。
- 请求由 Vben request client 自动附加。
- Token 过期后重新登录。
- 管理员接口额外要求 `is_superuser=true`。

## 沙盒归属

普通用户访问沙盒前执行：

```text
sandbox_record.user_id == current_user.id
```

不满足返回 403。管理员可跨越归属限制。

## API Key

OpenSandbox API Key：

```text
Browser -> 不接触
fba backend -> OPEN_SANDBOX_API_KEY -> OPEN-SANDBOX-API-KEY -> OpenSandbox
```

要求：

- 不写入前端环境变量。
- 不写入命令审计。
- 不写入普通日志。
- 生产环境使用 32 字节以上随机值。
- 空 Key 只用于隔离的本机开发。

## 路径约束

文件 API 使用 `normalize_workspace_path()`：

- 仅允许 `/workspace` 及其子目录。
- 阻断 `..` 越界。
- 终端会话可以 `cd` 到其他目录，但文件管理接口仍限制工作区。
- 代码运行和文件操作不接收用户构造的 Shell 拼接路径，构建命令时使用引号转义。

## 命令执行

- 命令超时由请求参数和后端最大限制控制。
- 输出超过上限会截断。
- 命令和结果写入 `sys_opensandbox_command`。
- 普通用户不能读取审计日志。
- 管理员按用户、沙盒、命令、时间和状态查询。

## 终端限制

当前终端不是完整 PTY 代理，不会把任意控制序列直接注入浏览器。这样降低了终端仿真复杂度，但也意味着 `vim`、`top` 等交互式程序支持有限。

## 沙盒 API 开关

- 仅管理员可调用。
- 只修改 `sys_config` 中的 `OPEN_SANDBOX_API_STATUS`，不执行系统命令。
- 暂停后拒绝创建、同步、命令、文件和生命周期写操作，保留概览、沙盒列表和命令审计的只读访问。
- 真正启停 OpenSandbox Server 应由 systemd、supervisor、WSL2 或 Docker 编排层管理。

## 网络安全

- PostgreSQL、Redis、OpenSandbox Server 不暴露公网。
- 沙盒动态端口只在内网。
- 反向代理为命令执行增加足够的 read timeout。
- 启用 HTTPS，限制 CORS。
- 不允许浏览器直接调用 OpenSandbox API。

## 数据安全

- 数据库密码和 API Key 使用 secret 管理。
- 备份数据库、文件存储和 OpenSandbox store。
- 删除沙盒前确认用户文件备份。
- 命令审计含敏感输出时应设置保留期限和访问审计。
