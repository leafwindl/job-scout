# job-scout 一键启动 / 停止
#
# 双击 start.bat 启动（容器模式），双击 stop.bat 停止
# 也可以用 PowerShell：
#   .\start.ps1            启动
#   .\start.ps1 -Local     本地模式（不用 Docker，效果更好）
#   .\start.ps1 -Stop      停止
#   .\start.ps1 -Rebuild   重建镜像后启动

param(
    [switch]$Stop,
    [switch]$Local,
    [switch]$Rebuild,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

function Write-Step($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  !!  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  XX  $msg" -ForegroundColor Red }

function Test-Port($port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return [bool]$c
}

function Wait-Healthy($port, $seconds = 60) {
    for ($i = 0; $i -lt $seconds; $i += 2) {
        try {
            $r = Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 3
            if ($r.ok) { return $true }
        } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Host ""
Write-Host "  job-scout" -ForegroundColor White
Write-Host "  ----------------" -ForegroundColor DarkGray
Write-Host ""

# ---------------------------------------------------------------- 停止
if ($Stop) {
    Write-Step "停止服务..."
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose down 2>&1 | Out-Null
        Write-Ok "容器已停止"
    }
    # 顺手清掉本地起的进程
    foreach ($p in 8001, 3000) {
        Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    }
    Write-Host ""
    exit 0
}

# ---------------------------------------------------------------- 前置检查
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Fail "找不到 docker，请先安装 Docker Desktop"
    exit 1
}

$dockerOk = $false
try {
    docker version --format '{{.Server.Version}}' 2>&1 | Out-Null
    $dockerOk = $LASTEXITCODE -eq 0
} catch { $dockerOk = $false }

if (-not $dockerOk) {
    Write-Warn2 "Docker 没启动，正在尝试拉起 Docker Desktop..."
    $exe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $exe) {
        Start-Process $exe
        Write-Step "等待 Docker daemon（最多 90 秒）..."
        for ($i = 0; $i -lt 45; $i++) {
            Start-Sleep -Seconds 2
            try {
                docker version --format '{{.Server.Version}}' 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $dockerOk = $true; break }
            } catch { }
        }
    }
    if (-not $dockerOk) {
        Write-Fail "Docker 仍然不可用，请手动启动 Docker Desktop 后重试"
        exit 1
    }
    Write-Ok "Docker 已就绪"
}

# ---------------------------------------------------------------- 本地模式
if ($Local) {
    Write-Step "本地模式（不用 Docker，走完整混合检索）"
    if (-not (Test-Path ".venv")) {
        Write-Fail "没找到 .venv，先运行 uv sync"
        exit 1
    }
    if (-not (Test-Path "web\node_modules")) {
        Write-Fail "没找到 web\node_modules，先 cd web 跑 pnpm install"
        exit 1
    }

    if (Test-Port 8001) {
        Write-Warn2 "8001 已在监听，跳过 API 启动"
    } else {
        Write-Step "启动 API（新窗口）..."
        Start-Process powershell -ArgumentList @(
            "-NoExit", "-Command", "Set-Location '$root'; uv run uvicorn api.app.main:app --port 8001"
        )
        if (Wait-Healthy 8001 90) { Write-Ok "API 就绪" } else { Write-Warn2 "API 还没响应，可能还在加载模型" }
    }

    if (Test-Port 3000) {
        Write-Warn2 "3000 已在监听，跳过前端启动"
    } else {
        Write-Step "启动前端（新窗口）..."
        Start-Process powershell -ArgumentList @(
            "-NoExit", "-Command", "Set-Location '$root\web'; pnpm dev"
        )
        Start-Sleep -Seconds 8
        Write-Ok "前端已启动"
    }

    if (-not $NoBrowser) { Start-Process "http://localhost:3000" }
    Write-Host ""
    Write-Host "  前端  http://localhost:3000" -ForegroundColor White
    Write-Host "  接口  http://127.0.0.1:8001/docs" -ForegroundColor DarkGray
    Write-Host "  采集  http://localhost:3000/collect" -ForegroundColor DarkGray
    Write-Host ""
    exit 0
}

# ---------------------------------------------------------------- 容器模式
if ($Rebuild) {
    Write-Step "重建镜像（首次或改了依赖时用，需要几分钟）..."
    docker compose build 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Fail "镜像构建失败"; exit 1 }
    Write-Ok "镜像已更新"
}

Write-Step "启动容器..."
docker compose up -d 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Fail "容器启动失败，运行 docker compose logs 看原因"; exit 1 }

if (Wait-Healthy 8001 90) {
    Write-Ok "API 就绪"
} else {
    Write-Warn2 "API 60 秒内没响应，可能还在加载"
}

for ($i = 0; $i -lt 30; $i++) {
    if (Test-Port 3000) { break }
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "  前端  http://localhost:3000" -ForegroundColor White
Write-Host "  接口  http://127.0.0.1:8001/docs" -ForegroundColor DarkGray
Write-Host "  采集  http://localhost:3000/collect" -ForegroundColor DarkGray
Write-Host "  停止  double click stop.bat" -ForegroundColor DarkGray
Write-Host ""

if (-not $NoBrowser) { Start-Process "http://localhost:3000" }
