# 日常运行手册

## 启动顺序

1. PostgreSQL / Redis
2. OpenSandbox Server
3. fba API
4. 前端静态服务或 Vite

停止时反向操作。

## 健康检查

```powershell
curl.exe -fsS http://127.0.0.1:8080/health
curl.exe -fsS http://127.0.0.1:8080/version
curl.exe -fsS http://127.0.0.1:8000/health
curl.exe -fsS http://127.0.0.1:5777
```

## 日志位置

| 服务 | 日志 |
|---|---|
| fba 本机 | 终端或 systemd journal |
| fba Docker | `docker compose logs -f fba_server` |
| OpenSandbox | `/tmp/opensandbox-server.log` |
| Celery | `docker compose logs -f fba_celery_worker` |
| 前端 | Nginx access/error log |

## 平台 API 开关

“启用 API/暂停 API”不是进程启停：

- 开关保存在 `sys_config` 的 `OPEN_SANDBOX_API_STATUS`，`1` 为启用、`0` 为暂停；
- 暂停后概览、沙盒列表和命令审计仍可读取，其他沙盒操作返回 503；
- 暂停不会停止 OpenSandbox Server，也不会删除容器或 `/workspace` 文件；
- 需要真正重启 Server 时使用下一节命令。

核对开关：

```sql
SELECT key, value FROM sys_config WHERE key = 'OPEN_SANDBOX_API_STATUS';
```

## 重启服务

本节命令重启的是 OpenSandbox/fba 进程，不是管理员页面的平台 API 开关。

```powershell
# OpenSandbox
wsl -d Ubuntu-24.04 -u xzy -- bash -lc "pkill -f opensandbox-server || true"
wsl -d Ubuntu-24.04 -u xzy -- bash -lc "cd ~/projects/opensandbox && setsid -f env OPENSANDBOX_SERVER_API_KEY=replace-me .venv/bin/opensandbox-server </dev/null >/tmp/opensandbox-server.log 2>&1"

# fba
docker compose -f docker-simply-compose.yml restart fba_server
```

如果本机直接运行 fba，使用服务管理器或重新执行 `fba run`。

## 沙盒巡检

```powershell
docker ps -a --filter "label=fba_managed=true" --format "table {{.Names}}	{{.Status}}	{{.RunningFor}}"
```

检查标签：

```powershell
docker inspect <container> --format "{{json .Config.Labels}}"
```

`opensandbox.io/manual-cleanup=true` 表示不会按 TTL 自动删除。

## 命令审计巡检

```sql
select status, count(*) from sys_opensandbox_command
where created_time >= now() - interval '1 day'
group by status;
```

对失败率高的用户或沙盒进一步查询详情。

## 清理策略

- 不要直接删除运行中的沙盒容器。
- 删除沙盒必须通过 fba 用户或管理员 API。
- 审计日志按合规要求定期归档，不建议无限增长。
- 定期清理停止或失败的本地软删除记录。
- 旧 TTL 沙盒续期日志出现时，应安排用户重建为手动清理沙盒。

## 事件处理

### OpenSandbox 不可用

1. 查看管理页状态是“已暂停”“进程不可达”还是“可用”。
2. 若为“已暂停”，在“沙盒实例”页面点击“启用 API”；否则继续检查 WSL 发行版。
3. 检查 Server 进程。
4. 检查 Docker 服务。
5. 查看 `/tmp/opensandbox-server.log`。
6. 验证 8080 端口。
7. 恢复后刷新前端服务状态。

### 数据库不可用

1. 停止 API。
2. 检查容器/外部数据库。
3. 验证连接和磁盘。
4. 恢复后启动 API。
5. 检查插件表存在。

### 前端异常

1. 检查 API 地址。
2. 查看浏览器 Network。
3. 验证 CORS。
4. 重新执行 typecheck/build。
