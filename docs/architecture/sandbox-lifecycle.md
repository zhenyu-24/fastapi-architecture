# 沙盒生命周期

## 状态机

```text
                 create(timeout=None)
                         |
                         v
                     Pending
                         |
                         v
                     Running <-------------------+
                         |                        |
                  idle timeout / admin pause      |
                         |                        |
                         v                        |
                      Paused -------------------+
                         |                 resume/access
                         |
                 admin delete
                         |
                         v
                    Terminated
```

## 创建

后端调用：

```python
Sandbox.create(
    image,
    timeout=None,
    ready_timeout=timedelta(seconds=120),
    resource={"cpu": "1", "memory": "2Gi"},
    metadata={
        "fba_user_id": "...",
        "fba_username": "...",
        "fba_name": "...",
        "fba_managed": "true",
    },
)
```

`timeout=None` 表示手动清理，不按 OpenSandbox TTL 自动删除。

## 运行

- 用户通过 execd 执行命令、读写文件。
- 每次命令和文件操作刷新 `last_activity_time`。
- 沙盒最大数量、输出大小、上传大小由配置限制。

## 自动暂停

触发条件：

- `OPEN_SANDBOX_AUTO_PAUSE_ENABLED=true`
- 状态为 Running 或 Pending
- `last_activity_time < now - OPEN_SANDBOX_IDLE_TIMEOUT_SECONDS`
- 不在当前进程的 active 执行集合中

动作：

1. 调用 OpenSandbox pause。
2. Docker runtime 执行 `docker pause`。
3. 保留容器、文件系统和进程内存。
4. 数据库状态改为 Paused。

暂停不是删除。

## 平台 API 开关

`OPEN_SANDBOX_API_STATUS` 是平台访问开关，不是 OpenSandbox Server 的进程控制：

| 条件 | 平台行为 |
|---|---|
| API 启用且 Server 可连通 | 允许创建、同步、终端、SFTP、代码运行和生命周期操作 |
| API 暂停且 Server 仍在运行 | 概览、列表和审计可读；其余沙盒操作返回 503 |
| API 启用但 Server 不可达 | 健康检查失败，操作返回网关错误或不可用提示 |

- 暂停期间不会删除容器、`/workspace` 文件或数据库记录。
- 空闲自动暂停和旧有限 TTL 续期巡检在 API 暂停时跳过，避免后台继续调用 Server。
- 真正停止或重启 Server 必须在 WSL2、systemd 或 Docker 编排层执行。

## 手动恢复

用户或管理员调用 resume：

1. OpenSandbox 恢复容器。
2. 等待状态 Running。
3. 更新 `paused_time=null` 和 `last_activity_time=now`。

## 显式删除

只有用户删除自己的沙盒或管理员删除任意沙盒时：

1. 调用 kill/delete。
2. OpenSandbox 删除容器和相关资源。
3. fba 记录软删除并设置 Terminated。

## 旧有限 TTL 沙盒保护

旧版本可能创建了带 TTL 的沙盒。为了避免 OpenSandbox 到期直接删除：

- 每分钟同步远端沙盒。
- 当 `expires_at` 距当前时间少于 1 小时时调用 renew。
- 默认续期 365 天。
- 之后继续纳入空闲暂停策略。

这不是新沙盒的正常路径。新沙盒必须是 `manual-cleanup`。

## 验证命令

```powershell
docker inspect <container> --format '{{json .Config.Labels}}'
docker inspect <container> --format '{{.State.Status}}'
```

期望：

- 创建后：`manual-cleanup=true`
- 空闲后：容器状态 `paused`
- 恢复后：`running`
- 删除后：容器不存在
