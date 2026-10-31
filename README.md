<div align="center">

<img alt="The logo includes the abstract combination of the three letters FBA, forming a lightning bolt that seems to spread out from the ground" width="320" src="https://wu-clan.github.io/picx-images-hosting/logo/fba.png">

# FastAPI Best Architecture

Enterprise-level backend architecture solution

English | [简体中文](./README.zh-CN.md)

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

## Extended Backend Distribution

This repository is a customized distribution of the upstream
[FastAPI Best Architecture](https://github.com/fastapi-practices/fastapi_best_architecture)
project. The original architecture, conventions, commands and upstream links are retained below.

- Maintainer: XiangZhenyu ([GitHub @zhenyu-24](https://github.com/zhenyu-24))
- This repository: [fastapi-architecture](https://github.com/zhenyu-24/fastapi-architecture)
- Paired frontend: [vue-vben-admin](https://github.com/zhenyu-24/vue-vben-admin)
- Upstream project: [fastapi-practices/fastapi_best_architecture](https://github.com/fastapi-practices/fastapi_best_architecture)
- Upstream documentation: [FastAPI Best Architecture Docs](https://fastapi-practices.github.io/fastapi_best_architecture_docs/)

### Added in this distribution

- Unified file management: chunked and resumable uploads, reference tracking, file center, range downloads and scheduled cleanup.
- Task scheduling improvements, including task management, execution records and administrative task controls.
- OpenSandbox integration: per-user lifecycle management, terminal, SFTP, web code runner, administrator management, command auditing and an API switch that does not stop the OpenSandbox Server process.
- A reduced set of official plugins in the paired frontend: some upstream plugin features are intentionally left without frontend entries.
- Backend API under `/api/v1`, consumed by the paired `web-ele` frontend through `VITE_GLOB_API_URL`.

See [MyREADME.md](./MyREADME.md) and [docs/README.md](./docs/README.md) for project-specific deployment and usage instructions.

## Three-tier architecture

The MVC architecture is common in Python Web as a general design pattern, but the three-tier architecture is more
fascinating

However, please note that we do not have a traditional multi-app (microservices) directory structure (django,
springBoot...). ), but a self-righteous directory structure that you can give it any twist if you don't like this model!

| workflow       | java           | fastapi_best_architecture |
|----------------|----------------|---------------------------|
| view           | controller     | api                       |
| data transmit  | dto            | schema                    |
| business logic | service + impl | service                   |
| data access    | dao / mapper   | crud                      |
| model          | model / entity | model                     |

## Help

For more details, please check
the [official documentation](https://fastapi-practices.github.io/fastapi_best_architecture_docs/)

## Sponsors

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

## Contributors

<a href="https://github.com/fastapi-practices/fastapi_best_architecture/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=fastapi-practices/fastapi_best_architecture"/>
</a>

## Special thanks

- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/latest/)
- [SQLAlchemy](https://docs.sqlalchemy.org/en/20/)
- [Casbin](https://casbin.org/zh/)
- [Ruff](https://beta.ruff.rs/docs/)
- ...

## Interactivity

[Discord](https://wu-clan.github.io/homepage/)

## License

This project is licensed by the terms of
the [MIT](https://github.com/fastapi-practices/fastapi_best_architecture/blob/master/LICENSE) license

[![Stargazers over time](https://starchart.cc/fastapi-practices/fastapi_best_architecture.svg?variant=adaptive)](https://starchart.cc/fastapi-practices/fastapi_best_architecture)
