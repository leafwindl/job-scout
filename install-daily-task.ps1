# 注册每日自动更新任务（Windows 计划任务）
#
# 用法：右键「使用 PowerShell 运行」
# 前提：浏览器已登录 BOSS 直聘，油猴脚本 v0.10.0+
#
# 注意：计划任务会用默认浏览器打开采集页。如果你不想每天弹窗口，
# 就别用这个脚本，改成每天手动点一下网页上的「开始采集」。

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$taskName = "job-scout-daily"

Write-Host "=== 注册每日采集任务 ===" -ForegroundColor Cyan
Write-Host "项目目录: $root"

# 检查 uv 是否可用
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host "找不到 uv，请先安装：https://docs.astral.sh/uv/" -ForegroundColor Red
    exit 1
}

$hour = Read-Host "每天几点跑？（0-23，默认 9）"
if ([string]::IsNullOrWhiteSpace($hour)) { $hour = "9" }
$minute = Read-Host "几分？（0-59，默认 30）"
if ([string]::IsNullOrWhiteSpace($minute)) { $minute = "30" }

$time = "{0:D2}:{1:D2}" -f [int]$hour, [int]$minute

# 用 cmd 包一层，避免计划任务里的引号地狱
$inner = "cd /d `"$root`" && uv run python -m job_scout.cli daily --timeout-min 70"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $inner" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $time
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "job-scout 每日增量采集：采列表 → 抓 JD → 标记停招 → 出日报" `
        -Force | Out-Null
} catch {
    Write-Host "注册失败（可能需要管理员权限）：$_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ 已注册任务「$taskName」，每天 $time 运行" -ForegroundColor Green
Write-Host ""
Write-Host "常用操作：" -ForegroundColor Cyan
Write-Host "  立即测试:  Start-ScheduledTask -TaskName $taskName"
Write-Host "  查看状态:  Get-ScheduledTaskInfo -TaskName $taskName"
Write-Host "  删除任务:  Unregister-ScheduledTask -TaskName $taskName -Confirm:`$false"
Write-Host ""
Write-Host "提醒：运行时会用默认浏览器打开采集页，脚本会自动滚动并抓 JD。"
Write-Host "      如果浏览器没登录，先手动登录一次（登录态会保持）。"
