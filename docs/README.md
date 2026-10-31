# 项目文档

本目录记录 FastAPI Best Architecture 后端、Vue Vben Admin 前端以及 OpenSandbox 沙盒工作台插件的部署、使用、接口与架构说明。

## 文档地图

| 目录 | 内容 |
|---|---|
| [deployment](deployment/README.md) | 本地开发、Docker Compose、生产部署、OpenSandbox 与故障排查 |
| [user-guides](user-guides/README.md) | 我的沙盒、终端、SFTP、在线代码运行 |
| [api](api/README.md) | 认证、用户接口、管理员接口与调用示例 |
| [architecture](architecture/README.md) | 系统总览、后端插件、前端结构、沙盒生命周期与安全设计 |
| [reference](reference/configuration.md) | 配置项、命令参数和 OpenSandbox 参考配置 |
| [operations](operations/README.md) | 日常巡检、维护、备份与升级 |

## 技术栈

| 层 | 技术 | 当前版本基线 |
|---|---|---|
| 后端 | FastAPI、SQLAlchemy Async、Pydantic | fba v1.16.0 |
| 前端 | Vue 3、TypeScript、Element Plus、Vben Admin 5 | Vben 5.7.0 |
| 沙盒控制面 | OpenSandbox Server | 1.2.0 |
| OpenSandbox Python SDK | `opensandbox` | `>=1.2.0` |
| 数据库 | PostgreSQL 或 MySQL | PostgreSQL 16 / MySQL 8 |
| 缓存与任务队列 | Redis | Redis 7 |
| 运行时 | Docker、WSL2 | Docker 24+，Ubuntu 24.04 |

## 文档约定

- 标记为 `PowerShell` 的命令在 Windows PowerShell 中执行。
- 标记为 `Bash` 的命令在 Linux、WSL 或 Git Bash 中执行。
- 示例中的沙盒 ID、账号密码和 API Key 均为占位值，部署前必须替换。
- 生产环境不要使用示例密码、示例 API Key 或空 API Key。
- 所有 API 示例默认接口前缀为 `http://127.0.0.1:8000/api/v1`。

## 推荐阅读顺序

1. 新环境部署：从 [环境准备](deployment/prerequisites.md) 开始。
2. 本机开发：阅读 [本地开发](deployment/local-development.md)。
3. 使用 OpenSandbox：阅读 [OpenSandbox 部署](deployment/opensandbox.md)。
4. 联调接口：阅读 [认证](api/authentication.md) 和 [用户接口](api/opensandbox-user.md)。
5. 理解实现：阅读 [系统总览](architecture/system-overview.md) 与 [沙盒生命周期](architecture/sandbox-lifecycle.md)。

OpenSandbox 参考配置：[opensandbox.sandbox.toml.example](reference/opensandbox.sandbox.toml.example)。

## 官方资料

- [FastAPI Best Architecture 官方文档](https://fastapi-practices.github.io/fastapi_best_architecture_docs/)
- [Vben Admin 文档](https://doc.vben.pro/)
- [OpenSandbox 安装](https://open-sandbox.ai/getting-started/installation#server)
- [OpenSandbox Python SDK](https://open-sandbox.ai/sdks/python)
- [OpenSandbox API](https://open-sandbox.ai/api/)
- [OpenSandbox 示例](https://open-sandbox.ai/examples/)
