# 故障排查

## 1. 通用检查顺序

```powershell
# 1. 基础设施
docker ps
# 2. OpenSandbox
curl.exe -fsS http://127.0.0.1:8080/health
curl.exe -fsS http://127.0.0.1:8080/version
# 3. fba
curl.exe -fsS http://127.0.0.1:8000/health
# 4. 前端
curl.exe -fsS http://127.0.0.1:5777
```

| 检查 | 失败含义 |
|---|---|
| Docker 容器未运行 | 数据库、Redis 或沙盒运行时不可用 |
| OpenSandbox 无响应 | WSL 端口、进程、Docker socket 或配置错误 |
| fba 无响应 | Python 依赖、端口、环境变量或启动日志错误 |
| 前端无响应 | Node/pnpm 依赖或 Vite 端口错误 |

## 2. 后端启动失败

查看后端日志：

```powershell
.venv\Scripts\fba.exe run
```

常见原因：

- Python 版本低于 3.12。
- `uv sync` 未执行。
- PostgreSQL 或 Redis 连接错误。
- `.env` 使用 Windows CRLF 并被 WSL 脚本读取。
- 端口 8000 已被占用。
- 插件 SQL 未执行。

检查端口：

```powershell
netstat -ano | Select-String ':8000'
```

## 3. 401 Unauthorized

- 浏览器请求需要 `Authorization: Bearer <access_token>`。
- 登录过期后重新登录。
- 管理接口需要超级管理员账号，普通用户会得到 403。
- 如果使用 curl，确认请求头没有被 PowerShell 引号拆散。

## 4. 数据库表不存在

检查：

```sql
select to_regclass('public.sys_opensandbox');
select to_regclass('public.sys_opensandbox_command');
```

初始化：

```powershell
.venv\Scripts\fba.exe init
```

或在 Docker 中重建 API 容器，触发首次初始化检查：

```powershell
docker compose -f docker-simply-compose.yml restart fba_server
```

不要在已有数据库上直接删除数据卷。

## 5. 前端依赖问题

```powershell
node --version
pnpm --version
pnpm install --frozen-lockfile
pnpm -F @vben/web-ele run typecheck
```

如果出现 `node: not found`，说明执行环境是 WSL/Git Bash，但 Node 只安装在 Windows。改用 Windows PowerShell，或在 Linux 中安装符合要求的 Node.js。

## 6. 前端接口地址错误

检查 `apps/web-ele/.env.development` 和 `.env.production`：

```dotenv
VITE_GLOB_API_URL=http://localhost:8000/api
```

必须保留 `/api`，版本号由前端 API 模块自动追加。修改生产环境变量后必须重新执行 `pnpm build:ele`。

## 7. CORS 错误

后端 `backend/.env` 或根目录 `.env` 中的 `CORS_ALLOWED_ORIGINS` 必须是 JSON 数组：

```dotenv
CORS_ALLOWED_ORIGINS='["http://localhost:5777","http://127.0.0.1:5777"]'
```

修改后重启后端。

## 8. OpenSandbox 不可达

### Windows 无法访问 WSL 的 8080

在 WSL 中检查：

```bash
curl -fsS http://127.0.0.1:8080/health
ss -ltnp | grep 8080
ps -ef | grep opensandbox-server | grep -v grep
```

如果 WSL 内正常但 Windows 不通，检查 WSL 端口转发或 Docker Desktop 的 localhost forwarding。

### Server 日志

```bash
tail -f /tmp/opensandbox-server.log
```

### Docker 权限

```bash
docker ps
```

若提示 permission denied，把 WSL 用户加入 `docker` 组并重新登录：

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

## 9. 沙盒 API 状态与开关

前端状态由三个字段组合判断：

| 界面状态 | 条件 | 含义 |
|---|---|---|
| 未配置 | `configured=false` | 尚未启用或配置 OpenSandbox |
| 已暂停 | `api_enabled=false` | 管理员暂停了平台 API；Server 进程可能仍在运行 |
| 进程不可达 | `api_enabled=true` 且 `server_available=false` | 平台开关已启用，但健康检查失败 |
| 可用 | `api_enabled=true` 且 `server_available=true` | 平台 API 和 Server 均可用 |

排查步骤：

1. “已暂停”：管理员进入“系统管理 → 沙盒管理 → 沙盒实例”，点击“启用 API”。不要通过重启或终止进程来解决暂停状态。
2. “进程不可达”：在 WSL2 中检查 `opensandbox-server` 进程、Docker 和 `http://127.0.0.1:8080/health`；若 Windows 访问不到 WSL2 端口，检查端口转发或修改“参数配置 → 沙盒配置 → 服务器地址”。
3. 核对开关值：

```sql
SELECT key, value FROM sys_config WHERE key = 'OPEN_SANDBOX_API_STATUS';
```

`1` 表示启用，`0` 表示暂停。修改开关只影响平台 API，不会启动、停止或删除 OpenSandbox 进程、容器和文件。

## 10. OpenSandbox 401/403

- 确认 `OPEN_SANDBOX_API_KEY` 与 `server.api_key` 一致。
- 使用 `OPENSANDBOX_SERVER_API_KEY` 启动时，确认本机配置没有另一个空 `api_key` 覆盖。
- 检查请求头名：`OPEN-SANDBOX-API-KEY`。
- 不要在浏览器端硬编码 API Key。

## 11. OpenSandbox 502 或容器访问失败

WSL2 常见原因是 Server 无法解析 Docker bridge 内部地址。设置：

```toml
[proxy]
resolve_internal = false
```

然后重启 Server。

若使用 Docker Desktop，确认 Server 已连接正确的 Docker context：

```bash
docker context show
docker info
```

## 12. 沙盒创建后立即消失

检查：

1. 后端是否真的调用 `timeout=None`。
2. Server 版本和 SDK 版本是否匹配 1.2.0。
3. 是否由旧版本创建了有限 TTL 沙盒。
4. 是否手动执行了删除接口。
5. Docker 容器是否因 OOM、Docker 重启或宿主机关闭而退出。

查看标签和日志：

```powershell
docker ps -a --filter "label=fba_managed=true"
docker inspect <sandbox-container> --format "{{json .Config.Labels}}"
```

如果是旧 TTL 沙盒，插件的 `OPEN_SANDBOX_LEGACY_EXPIRY_GUARD_ENABLED` 会在到期前续期。新沙盒应显示 `opensandbox.io/manual-cleanup=true`。

## 13. 空闲后没有暂停

检查：

```dotenv
OPEN_SANDBOX_AUTO_PAUSE_ENABLED=true
OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS=1800
OPEN_SANDBOX_AUTO_PAUSE_SWEEP_SECONDS=60
```

后端启动日志应出现 OpenSandbox 插件加载信息。等待或手动缩短阈值验证。

## 14. 上传失败

- 检查 `OPEN_SANDBOX_UPLOAD_LIMIT_BYTES`。
- 检查 Nginx `client_max_body_size`。
- 检查浏览器到后端的反向代理超时。
- 确认目标路径位于 `/workspace` 内。
- 大文件传输会受具体网络和服务端磁盘空间影响。

## 15. 终端命令不生效

- `cd` 仅在同一个终端会话内保持。刷新页面会新建前端会话。
- `clear` 是插件虚拟命令，清空当前前端终端并写入审计日志。
- 复杂交互式程序如 `vim`、`top` 仍依赖 OpenSandbox execd 的终端能力，不等同于完整 SSH PTY。
- 命令输出超过 `OPEN_SANDBOX_MAX_OUTPUT_CHARS` 会被截断。

## 16. 收集诊断信息

```powershell
Get-Date
docker version
docker ps -a
wsl --status
wsl -d Ubuntu-24.04 -u xzy -- bash -lc "ps -ef | grep opensandbox-server | grep -v grep"
wsl -d Ubuntu-24.04 -u xzy -- bash -lc "tail -n 200 /tmp/opensandbox-server.log"
curl.exe -v http://127.0.0.1:8080/health
curl.exe -v http://127.0.0.1:8000/health
```

提交问题时请移除 API Key、密码和访问令牌。
