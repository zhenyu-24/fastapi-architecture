# SSH 终端

## 打开终端

进入“沙盒工作台 → SSH 终端”，选择正在运行的沙盒即可开始输入。

终端不需要底部输入框。点击终端区域后直接输入命令：

```bash
pwd
ls -la
cd /workspace
clear
```

## 光标与输入

- 光标显示为底部横线 `_`，与常见 Bash 终端一致。
- 支持 `←`、`→` 在当前命令内移动光标，并可在中间位置继续插入或删除字符。
- 支持 `Home`、`End` 等浏览器输入框光标快捷键。
- 支持 `Enter` 执行。
- 支持 `↑`、`↓` 浏览当前页面记录的命令历史。
- 执行期间显示“执行中”，结束后自动重新聚焦。
- 可以直接用鼠标选中输出文本；松开左键后选择会保留。
- 选中后可点击顶部“复制选中”，或按 `Ctrl+C` 复制。

## 执行用户与 sudo

当前默认的 `code-interpreter` 镜像以 `root` 用户执行命令。终端中的 `whoami` 会返回 `root`，因此普通命令不需要 `sudo`，插件也没有“sudo 密码”或“su 密码”配置项。

实测容器：

```text
uid=0(root) gid=0(root) groups=0(root)
sudo: not found
root password: locked
```

不要依赖 sudo 密码实现用户隔离。沙盒之间的隔离由 OpenSandbox 容器提供；如果某个部署必须让用户代码以非 root 身份运行，应使用自定义镜像和非 root 启动方式，或在后续版本为命令执行增加明确的 `uid`/`gid` 配置。

## 安装软件与 pip

默认镜像没有预装 `pip`，但可以通过 APT 下载安装。容器已经是 root 用户，不要执行 `sudo apt update`，因为镜像没有安装 `sudo`。正确命令是：

```bash
apt-get update
apt-get install -y python3-pip
python3 -m pip --version
```

不要使用 `apt install pip`，Ubuntu 仓库中的包名是 `python3-pip`。第一次安装前必须先执行 APT 索引更新，否则会出现 `Unable to locate package`。安装结果会保留在当前沙盒的文件系统中，沙盒暂停后仍然存在；删除沙盒后会被清除。

## `cd` 行为

同一个 Bash 会话会保留当前工作目录：

```bash
cd /workspace
mkdir -p demo
cd demo
pwd
# /workspace/demo
```

执行 `cd` 后，顶部路径会同步更新，后续命令默认在该目录执行。切换终端标签或页面刷新会创建新的前端会话。

## `clear` 行为

```bash
clear
```

插件会把 `clear` 作为终端控制命令处理：

1. 清空当前前端终端输出。
2. 写入管理员命令审计。
3. 不依赖容器中的 `TERM` 环境变量。

## 多终端

点击“新建终端”可以创建多个 Bash 会话。每个标签拥有独立的：

- 当前工作目录
- Shell 环境变量
- 交互状态

关闭标签时会调用 OpenSandbox 删除会话接口。

## 限制

当前终端基于 OpenSandbox execd 的持久化 Bash 会话，不是完整的浏览器 SSH PTY：

- 普通命令、环境变量和 `cd` 可用。
- `vim`、`top`、密码提示等完整 TTY 程序可能不可用。
- `Ctrl+C` 等字符级中断不等同于本地终端。
- 命令输出在命令完成后统一返回。
- 超大输出会被截断。

## 示例

```bash
# 查看 Python 版本
python3 --version

# 创建目录并写入文件
mkdir -p /workspace/notes
printf 'hello\n' > /workspace/notes/a.txt
cat /workspace/notes/a.txt

# 查看资源
free -h
df -h

# 清理屏幕
clear
```
