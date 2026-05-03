# ============================================================
# 一键设置 Windows 计划任务（管理员身份运行）
# 每小时自动解密微信数据库
# ============================================================

$TaskName = "WeChatAutoDecrypt"
$ScriptPath = "C:\WeChatSync\wechat-auto-decrypt.ps1"

# 删除旧任务
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# 创建任务
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""

# 每小时触发
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration (New-TimeSpan -Days 365)

# 开机启动触发
$TriggerBoot = New-ScheduledTaskTrigger -AtStartup

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger @($Trigger, $TriggerBoot) `
    -Settings $Settings `
    -Description "每小时自动解密微信数据库，供 HyperChat 同步" `
    -RunLevel Highest

Write-Host ""
Write-Host "=============================" -ForegroundColor Green
Write-Host " 计划任务已创建: $TaskName" -ForegroundColor Green
Write-Host " 频率: 每小时 + 开机自启" -ForegroundColor Green
Write-Host " 脚本: $ScriptPath" -ForegroundColor Green
Write-Host " 输出: C:\WeChatSync\decrypted\" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. 安装 Syncthing 并共享 C:\WeChatSync\decrypted" -ForegroundColor Yellow
Write-Host "2. 在 NixOS 端配置同步接收" -ForegroundColor Yellow
