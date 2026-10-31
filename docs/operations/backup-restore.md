# 备份与恢复

## 备份对象

| 对象 | 位置 | 频率 |
|---|---|---|
| PostgreSQL | 数据卷/外部实例 | 每日 |
| Redis | 数据卷 | 每日或按需 |
| fba 文件存储 | `fba_storage` 或 `FILE_STORAGE_ROOT` | 每日增量 |
| OpenSandbox SQLite | `~/.opensandbox/opensandbox.db` | 每次升级前 |
| 配置 | `.env`、`.sandbox.toml` | 每次变更 |

## PostgreSQL 备份

```bash
pg_dump -h 127.0.0.1 -U postgres -d fba -Fc -f fba-$(date +%F).dump
```

| 参数 | 说明 |
|---|---|
| `-h` | 数据库主机 |
| `-U` | 用户 |
| `-d` | 数据库名 |
| `-Fc` | 自定义压缩格式 |
| `-f` | 输出文件 |

Docker：

```powershell
docker exec fba_postgres pg_dump -U postgres -d fba -Fc -f /tmp/fba.dump
docker cp fba_postgres:/tmp/fba.dump .\fba.dump
```

## 恢复 PostgreSQL

```bash
pg_restore -h 127.0.0.1 -U postgres -d fba --clean --if-exists fba.dump
```

恢复前停止 API 和 Celery。

## OpenSandbox store

```bash
cp ~/.opensandbox/opensandbox.db ~/.opensandbox/opensandbox.db.$(date +%F).bak
```

恢复前停止 OpenSandbox Server。

## 配置备份

至少备份：

- `backend/.env`
- 根目录 `.env`
- `~/.sandbox.toml`
- 反向代理配置
- 前端生产环境变量

配置可能含密钥，必须使用加密存储。

## 恢复顺序

1. 停止 API、Celery 和 OpenSandbox。
2. 恢复 OpenSandbox store。
3. 恢复 PostgreSQL。
4. 恢复 Redis 或允许重建。
5. 恢复文件存储。
6. 恢复配置。
7. 启动 OpenSandbox。
8. 启动 API。
9. 启动 Celery。
10. 验证健康检查和核心接口。

## 验证

```powershell
curl.exe -fsS http://127.0.0.1:8080/health
curl.exe -fsS http://127.0.0.1:8000/health
```

登录系统，检查沙盒列表、文件列表和命令审计。
