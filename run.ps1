# job-scout 本地一键启动（不依赖 Docker）
#
# 用法：右键「使用 PowerShell 运行」，或在终端里 .\run.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=== job-scout 启动中 ===" -ForegroundColor Cyan

if (-not (Test-Path "$root\data\job_scout.db")) {
    Write-Host "警告：没找到 data\job_scout.db，请先采集数据" -ForegroundColor Yellow
}

# 后端
Write-Host "启动 API (8001)..." -ForegroundColor Green
Start-Process pwsh -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root'; uv run uvicorn api.app.main:app --port 8001"
)

Start-Sleep -Seconds 8

# 前端
Write-Host "启动 Web (3000)..." -ForegroundColor Green
Start-Process pwsh -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\web'; if (-not (Test-Path node_modules)) { pnpm install }; pnpm dev"
)

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "API 文档: http://127.0.0.1:8001/docs" -ForegroundColor Cyan
Write-Host "前端页面: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "关闭对应窗口即可停止服务。"
