# 生产部署

## 推荐拓扑

```text
Browser
  -> HTTPS / Nginx
      -> /            -> Vue `apps/web-ele/dist`
      -> /api/...     -> FastAPI
                           -> PostgreSQL
                           -> Redis
                           -> OpenSandbox Server
                                -> Docker sandbox containers
```

前端不直接连接 OpenSandbox。浏览器只访问 FastAPI，OpenSandbox API Key 仅保存在后端。

## 1. 构建前端

```powershell
Set-Location D:\work\code\web_learning\template\vue-vben-admin
pnpm install --frozen-lockfile
pnpm build:ele
```

构建前设置：

```dotenv
VITE_GLOB_API_URL=https://example.com/api
VITE_ROUTER_HISTORY=hash
VITE_COMPRESS=none
```

| 配置 | 说明 |
|---|---|
| `VITE_GLOB_API_URL` | 浏览器可访问的 API 根地址，必须包含 `/api` |
| `VITE_ROUTER_HISTORY` | 建议 `hash`，减少 Nginx `try_files` 配置 |
| `VITE_COMPRESS` | 可改为 `gzip` 或 `brotli`，以便生成压缩资源 |

产物位于 `apps/web-ele/dist`，同目录可能生成 `dist.zip`。

## 2. 配置 Nginx

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    root /srv/fba/web;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 660s;
    }
}
```

| 参数 | 说明 |
|---|---|
| `root` | 前端 `dist` 目录 |
| `try_files` | 前端路由回退到 `index.html` |
| `proxy_pass` | 将 `/api/` 转发到后端 |
| `proxy_read_timeout 660s` | 为最长 600 秒的代码/命令执行请求留出余量 |

## 3. 后端运行方式

### 方式 A：宿主机 + systemd

```ini
[Unit]
Description=FBA API
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
WorkingDirectory=/srv/fba/backend-project
EnvironmentFile=/srv/fba/backend-project/backend/.env
ExecStart=/srv/fba/backend-project/.venv/bin/fba run --host 127.0.0.1 --port 8000 --no-reload --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fba-api
sudo systemctl status fba-api
```

### 方式 B：Docker Compose

参考 [Docker Compose](docker-compose.md)。生产环境应固定镜像标签，避免直接使用 `latest`。

## 4. 必须替换的密钥

- `TOKEN_SECRET_KEY`：至少 32 字节随机值。
- `DATABASE_PASSWORD`：数据库强密码。
- `REDIS_PASSWORD`：生产环境建议启用。
- `OPEN_SANDBOX_API_KEY`：与 OpenSandbox `server.api_key` 完全一致。
- OAuth、邮件等第三方凭据。

## 5. OpenSandbox 生产要求

- OpenSandbox Server 只监听内网地址，或由防火墙限制来源。
- 沙盒动态端口范围 `40000-60000` 不对公网开放。
- 推荐使用 API Key；空 API Key 只允许在完全可信的本机环境使用。
- 不允许 OpenSandbox TTL 自动删除沙盒；新沙盒必须使用 `manual-cleanup`。
- 后端插件的空闲暂停任务必须运行，且只能有一个实例执行破坏性维护操作。
- 管理员“暂停 API”只影响平台访问，不能替代进程监控；Server 进程应由 systemd、supervisor 或容器编排层管理。
- 开启审计日志，并限制管理员账号数量。

## 6. 数据持久化

| 数据 | 位置/卷 | 备份建议 |
|---|---|---|
| PostgreSQL | `fba_postgres` 数据卷或外部数据库 | 每日全量 + WAL 归档 |
| Redis | `fba_redis` 数据卷 | 允许重建，但需评估会话和 Celery 队列 |
| 文件存储 | `fba_storage` 卷或 `FILE_STORAGE_ROOT` | 每日增量或对象存储快照 |
| OpenSandbox SQLite/PostgreSQL store | `~/.opensandbox/opensandbox.db` 或 PostgreSQL | 与沙盒策略变更同步备份 |

## 7. 发布检查清单

- [ ] 后端测试与 lint 通过。
- [ ] 前端 typecheck 与 build 通过。
- [ ] 数据库已备份。
- [ ] 插件 SQL 已执行或确认已初始化。
- [ ] OpenSandbox `/health` 和 `/version` 正常。
- [ ] 新沙盒创建后确认 `expires_at=null`、`opensandbox.io/manual-cleanup=true`。
- [ ] 空闲暂停实测通过。
- [ ] 普通用户不能访问管理员接口。
- [ ] 命令审计仅管理员可读。
- [ ] 暂停 API 后列表和审计仍可读，其他沙盒操作返回 503；启用后状态恢复为“可用”。
- [ ] HTTPS、CORS、上传大小和代理超时符合业务要求。
