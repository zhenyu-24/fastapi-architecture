# 一键清除配置缓存 + 重启后端服务
# 直接修改数据库 sys_config 后，运行此脚本即可
# 用法: .\restart_server.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== 1. 清理 Redis 配置缓存 ===" -ForegroundColor Cyan
python C:\Users\xiangzy\AppData\Local\Temp\opencode\clear_config_cache.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Redis 清理失败，请检查 Redis 是否运行中" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== 2. 停止当前服务 ===" -ForegroundColor Cyan
$oldPid = netstat -ano | Select-String ":8000 " | ForEach-Object { ($_ -split '\s+')[-1] }
if ($oldPid) {
    Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "旧服务 (PID: $oldPid) 已停止" -ForegroundColor Green
} else {
    Write-Host "没有找到运行中的服务" -ForegroundColor Yellow
}

Write-Host "`n=== 3. 启动新服务 ===" -ForegroundColor Cyan
Start-Process powershell -WindowStyle Normal -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PSScriptRoot'; Write-Host 'fba 服务启动中...' -ForegroundColor Cyan; python run.py"
)
Start-Sleep -Seconds 3
Write-Host "`n服务已重启，Swagger: http://127.0.0.1:8000/docs" -ForegroundColor Green
