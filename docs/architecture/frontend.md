# 前端结构

## 应用

当前项目使用：

```text
vue-vben-admin/apps/web-ele
```

技术栈：

- Vue 3 + TypeScript
- Element Plus
- Vben Admin 5
- CodeMirror 6
- Vue Router
- Vben request client

## 沙盒工作台路由

`src/router/routes/modules/online.ts` 定义：

| 菜单 | 路径 | 页面 |
|---|---|---|
| 我的沙盒 | `/online/my-sandbox` | `views/online/my-sandbox/index.vue` |
| SSH 终端 | `/online/terminal` | `views/online/terminal/index.vue` |
| SFTP 文件传输 | `/online/sftp` | `views/online/sftp/index.vue` |
| 在线代码运行 | `/online/code` | `views/online/code/index.vue` |

“我的沙盒”集中提供沙盒创建、启动、停止和删除。三个工作页面共用 `OpenSandboxToolbar.vue`，工具栏只提供当前沙盒选择、状态和刷新，不显示沙盒生命周期操作。

## 管理员沙盒管理

系统管理中的“沙盒管理”页面：

- 菜单：`系统管理 → 沙盒管理`
- 沙盒实例：`/admin/sandbox/instances`，组件 `views/admin/sandbox/index.vue`。
- 命令审计：`/admin/sandbox/audit`，组件 `views/admin/sandbox/audit/index.vue`。
- 使用 VxeGrid 分页查询全部用户沙盒。
- 表格支持复选框多选和批量生命周期操作。
- 沙盒名称、沙盒 ID 和所属用户名分列显示。
- 支持用户名、状态、名称关键词查询和列排序。
- 支持为指定用户创建沙盒、同步远端沙盒，以及启动/停止/重启/重命名/删除沙盒。
- 提供“启用 API/暂停 API”平台开关和管理概览；该开关只写 `sys_config`，不会启动或停止 OpenSandbox Server。
- “命令审计”页面支持按用户名、沙盒 ID、命令关键词、状态和起止时间查询，并查看完整输出。

“我的沙盒”也使用 VxeGrid，提供查询表单、统计、列头排序、分页和统一的表格工具栏。

## API 模块

`src/api/opensandbox.ts`：

- 定义 ServiceStatus、SandboxItem、FileEntry、CommandResult 等类型。
- 封装用户与管理员 API。
- 统一在路径前使用 `/v1/opensandbox`。
- 通过 Vben request client 自动携带 JWT。

## 共享 composable

`useOpenSandbox.ts`：

- 初始化 overview 和沙盒列表。
- 选择并保持当前沙盒。
- 创建、暂停、恢复和删除。
- 状态中文标签和标签颜色。

## 终端页面

- `ElTabs` 管理多个 Bash 会话。
- 隐藏的 input 捕获键盘输入。
- `outputs` 按会话 ID 保存输出。
- `result.cwd` 更新顶部路径。
- `clear` 清空当前输出。
- 底部横线光标。

## SFTP 页面

- 左右两张卡片，页面高度铺满。
- 文件列表和传输列表内部滚动。
- 上传使用 `ElUpload` 的 `before-upload`。
- 下载使用后端流式接口。
- 路径校验由后端执行。

## 代码运行页面

- 外层水平 `ElSplitter`：资源管理器 / 编辑区。
- 内层垂直 `ElSplitter`：编辑器 / 输出。
- `RemoteFileTree` 懒加载目录。
- 点击文件后调用读取接口。
- CodeMirror 深色主题仅在系统/偏好为暗色时加载。
- 语言根据扩展名自动切换。

## 状态与错误

- API 错误由 request client 统一提示。
- 文件操作使用 Element Plus 对话框和确认框。
- 服务状态区分为“未配置”“已暂停”“进程不可达”“可用”：`api_enabled=false` 表示管理员暂停平台 API，`server_available=false` 表示 Server 不可达，二者同时为 `true` 才显示“可用”。
- API 暂停时，工作页面禁用创建、终端输入、文件操作和代码运行，并提示联系管理员；概览、列表和审计仍可读取。
- 页面不直接访问 OpenSandbox，不包含 API Key。

## 构建检查

```powershell
Set-Location D:\work\code\web_learning\template\vue-vben-admin
pnpm -F @vben/web-ele run typecheck
pnpm -F @vben/web-ele run build
```
