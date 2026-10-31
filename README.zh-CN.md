<div align="center">

<img alt="Logo 包含了 FBA 三个字母抽象结合，形成了一个类似从地面扩散投影上来的闪电" width="320" src="https://wu-clan.github.io/picx-images-hosting/logo/fba.png">

# FastAPI Best Architecture

企业级后端架构解决方案

简体中文 | [English](./README.md)

[![GitHub](https://img.shields.io/github/license/fastapi-practices/fastapi_best_architecture)](https://github.com/fastapi-practices/fastapi_best_architecture/blob/master/LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
![MySQL](https://img.shields.io/badge/MySQL-8.0%2B-%2300758f)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.0%2B-%23336791)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-%23778877)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
![Docker](https://img.shields.io/badge/Docker-%232496ED?logo=docker&logoColor=white)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?logo=discord&logoColor=white)](https://discord.com/invite/yNN3wTbVAC)
![Discord](https://img.shields.io/discord/1185035164577972344)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/fastapi-practices/fastapi_best_architecture)

</div>

## 后端二次开发版

本仓库二次开发自 GitHub 项目
[FastAPI Best Architecture](https://github.com/fastapi-practices/fastapi_best_architecture)。
以下保留原项目的架构说明、使用方式和 GitHub 链接，便于对照上游文档和后续升级。

- 维护者：XiangZhenyu（[GitHub @zhenyu-24](https://github.com/zhenyu-24)）
- 本仓库：[fastapi-architecture](https://github.com/zhenyu-24/fastapi-architecture)
- 配套前端：[vue-vben-admin](https://github.com/zhenyu-24/vue-vben-admin)
- 上游项目：[fastapi-practices/fastapi_best_architecture](https://github.com/fastapi-practices/fastapi_best_architecture)
- 上游文档：[FastAPI Best Architecture 官方文档](https://fastapi-practices.github.io/fastapi_best_architecture_docs/)

### 新增功能

- 统一文件管理：分片与断点续传、引用追踪、文件中心、Range 下载和定时清理。
- 任务调度优化：任务管理、执行记录和管理员任务控制。
- 接入 OpenSandbox：每用户沙盒生命周期管理、SSH 终端、SFTP、在线代码运行、管理员沙盒管理、命令审计和平台 API 开关；暂停 API 不会停止 OpenSandbox Server 进程。
- 精简官方插件：部分官方插件功能已放弃，配套前端不再提供对应入口。
- 后端统一提供 `/api/v1` 接口，由配套 `web-ele` 前端通过 `VITE_GLOB_API_URL` 调用。

项目专属的部署与使用说明见 [MyREADME.md](./MyREADME.md) 和 [docs/README.md](./docs/README.md)。

## 三层架构

mvc 架构作为常规设计模式，在 python web 中很常见，但是三层架构更令人着迷

但请注意，我们并没有传统的多 app （微服务）目录结构（django、springBoot...），而是自以为是的目录结构，如果您不喜欢这种模式，可以对其进行任意改造！

| 工作流程 | java           | fastapi_best_architecture |
|------|----------------|---------------------------|
| 视图   | controller     | api                       |
| 数据传输 | dto            | schema                    |
| 业务逻辑 | service + impl | service                   |
| 数据访问 | dao / mapper   | crud                      |
| 模型   | model / entity | model                     |

## 帮助

更多详情请查看 [官方文档](https://fastapi-practices.github.io/fastapi_best_architecture_docs/)

## 赞助商

<div align="center">
  <table>
    <tr>
      <td align="center">
        <a href="https://claude.uy/home">
          <img src="https://purple-sun-4f5a.wuyao1243.workers.dev/" alt="Claude.uy" width="400">
        </a>
      </td>
    </tr>
  </table>
</div>

## 贡献者

<a href="https://github.com/fastapi-practices/fastapi_best_architecture/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=fastapi-practices/fastapi_best_architecture"/>
</a>

## 特别鸣谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/latest/)
- [SQLAlchemy](https://docs.sqlalchemy.org/en/20/)
- [Casbin](https://casbin.org/zh/)
- [Ruff](https://beta.ruff.rs/docs/)
- ...

## 互动

[Discord](https://wu-clan.github.io/homepage/)

## 许可证

本项目由 [MIT](https://github.com/fastapi-practices/fastapi_best_architecture/blob/master/LICENSE) 许可证的条款进行许可

[![Stargazers over time](https://starchart.cc/fastapi-practices/fastapi_best_architecture.svg?variant=adaptive)](https://starchart.cc/fastapi-practices/fastapi_best_architecture)
