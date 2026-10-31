# 架构文档

| 文档 | 内容 |
|---|---|
| [系统总览](system-overview.md) | 前端、后端、OpenSandbox 与数据库的整体关系 |
| [后端插件](backend-plugin.md) | fba 分层、插件目录、数据表与定时任务 |
| [前端结构](frontend.md) | web-ele 页面、API 模块、路由和交互结构 |
| [沙盒生命周期](sandbox-lifecycle.md) | 创建、运行、暂停、恢复、删除和旧 TTL 保护 |
| [安全设计](security.md) | 鉴权、权限、API Key、路径约束与审计 |

设计目标：

- 用户只通过 fba 后端操作 OpenSandbox，浏览器不持有 OpenSandbox API Key。
- 普通用户与管理员权限边界清晰。
- 沙盒空闲自动暂停而不是自动删除。
- 命令、文件、终端和代码运行共享同一套归属校验。
- 文档、配置和实现保持可追踪。
