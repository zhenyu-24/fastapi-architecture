# 运维手册

| 文档 | 内容 |
|---|---|
| [日常运行手册](runbook.md) | 健康检查、日志、启停、异常处理 |
| [备份与恢复](backup-restore.md) | 数据库、文件、OpenSandbox store 和配置备份 |

## 日常检查

```powershell
docker ps -a
curl.exe -fsS http://127.0.0.1:8080/health
curl.exe -fsS http://127.0.0.1:8000/health
curl.exe -fsS http://127.0.0.1:5777
```

## 关键指标

- fba API 可用性、错误率、响应时间。
- OpenSandbox `/health` 和 `/version`。
- Running / Paused 沙盒数量。
- 命令失败率和审计日志增长。
- PostgreSQL 连接数、磁盘、慢查询。
- Redis 内存、连接数、Celery 队列长度。
- 沙盒动态端口占用和容器资源。
