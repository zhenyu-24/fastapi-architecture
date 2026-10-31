# 部署指南

## 部署方式

| 方式 | 适用场景 | 后端 | 前端 | OpenSandbox |
|---|---|---|---|---|
| 本地开发 | 功能开发、调试 | `fba run` | `pnpm dev:ele` | WSL2 中运行 |
| 简化 Docker Compose | 单机体验、内网部署 | `docker-simply-compose.yml` | 宿主机或 Nginx | WSL2 或独立 Linux 主机 |
| 生产部署 | 对外服务、多进程 | systemd、容器或进程管理器 | Nginx + 静态文件 | 独立 Docker 主机或受控 WSL2 |

## 推荐部署顺序

1. 阅读 [环境准备](prerequisites.md)。
2. 本机开发按 [本地开发](local-development.md) 操作。
3. 使用容器启动基础服务按 [Docker Compose](docker-compose.md) 操作。
4. 对外部署按 [生产部署](production.md) 操作。
5. OpenSandbox 必须单独阅读 [OpenSandbox 部署](opensandbox.md)，参考配置见 [opensandbox.sandbox.toml.example](../reference/opensandbox.sandbox.toml.example)。
6. 出现问题时阅读 [故障排查](troubleshooting.md)。

## 关键原则

- 后端、前端和 OpenSandbox 是三个独立进程，分别管理生命周期。
- 管理员的“启用 API/暂停 API”只控制 fba 是否调用 OpenSandbox，不会启动或停止 OpenSandbox Server；真实进程启停由 WSL2、systemd 或 Docker 编排层负责。
- OpenSandbox 的 API Key 只保存在后端环境变量中，不发送到浏览器。
- 新建沙盒使用 `manual-cleanup` 模式，禁止依靠 OpenSandbox 的 TTL 自动删除容器。
- 沙盒空闲后由后端插件定时暂停；暂停会保留容器、文件与进程状态。
- 前端构建时会把 `VITE_GLOB_API_URL` 写入静态资源，修改后必须重新构建。
- 生产环境必须替换数据库密码、Token 密钥和 OpenSandbox API Key。
- 根目录 `.env` 用于 `docker-simply-compose.yml`；`backend/.env` 用于本机直接运行后端。
