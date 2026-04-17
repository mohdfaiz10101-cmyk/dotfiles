# Windows 自动部署脚本
# 从 NixOS 推送到 Windows 后，以管理员身份运行
# PowerShell -ExecutionPolicy Bypass -File deploy.ps1

$ErrorActionPreference = "Stop"
$DeployDir = $PSScriptRoot
$DownloadDir = "$env:USERPROFILE\Downloads\auto-deploy"
New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null

Write-Host "=== Charlie Windows 自动部署 ===" -ForegroundColor Cyan
Write-Host ""

# ============ 1. Clash Verge Rev ============
Write-Host "[1/5] 安装 Clash Verge Rev..." -ForegroundColor Yellow
$clashVergeUrl = "https://github.com/clash-verge-rev/clash-verge-rev/releases/latest/download/Clash.Verge_x64-setup.exe"
$clashVergeExe = "$DownloadDir\ClashVerge-setup.exe"
if (-not (Test-Path "C:\Program Files\Clash Verge\Clash Verge.exe")) {
    Write-Host "  下载 Clash Verge Rev..."
    Invoke-WebRequest -Uri $clashVergeUrl -OutFile $clashVergeExe -UseBasicParsing
    Write-Host "  安装中..."
    Start-Process -FilePath $clashVergeExe -Args "/S" -Wait
    Write-Host "  ✅ Clash Verge Rev 已安装" -ForegroundColor Green
} else {
    Write-Host "  ✅ 已安装，跳过" -ForegroundColor Green
}

# ============ 2. FlClash ============
Write-Host "[2/5] 安装 FlClash..." -ForegroundColor Yellow
$flclashUrl = "https://github.com/chen08209/FlClash/releases/latest/download/FlClash-windows-x64-setup.exe"
$flclashExe = "$DownloadDir\FlClash-setup.exe"
if (-not (Test-Path "C:\Program Files\FlClash\FlClash.exe")) {
    Write-Host "  下载 FlClash..."
    Invoke-WebRequest -Uri $flclashUrl -OutFile $flclashExe -UseBasicParsing
    Write-Host "  安装中..."
    Start-Process -FilePath $flclashExe -Args "/S" -Wait
    Write-Host "  ✅ FlClash 已安装" -ForegroundColor Green
} else {
    Write-Host "  ✅ 已安装，跳过" -ForegroundColor Green
}

# ============ 3. 导入代理配置 ============
Write-Host "[3/5] 导入代理配置..." -ForegroundColor Yellow
$clashConfigDir = "$env:USERPROFILE\.config\clash-verge-rev\profiles"
New-Item -ItemType Directory -Force -Path $clashConfigDir | Out-Null
Copy-Item "$DeployDir\mihomo-config.yaml" "$clashConfigDir\imported-from-nixos.yaml" -Force
Write-Host "  ✅ 配置已复制到 $clashConfigDir" -ForegroundColor Green
Write-Host "  📋 打开 Clash Verge → Profiles → 导入本地文件 → 选择 imported-from-nixos.yaml"

# ============ 4. Sunshine (远程控制) ============
Write-Host "[4/5] 安装 Sunshine..." -ForegroundColor Yellow
$sunshineUrl = "https://github.com/LizardByte/Sunshine/releases/latest/download/sunshine-windows-installer.exe"
$sunshineExe = "$DownloadDir\sunshine-setup.exe"
if (-not (Get-Service -Name "Sunshine" -ErrorAction SilentlyContinue)) {
    Write-Host "  下载 Sunshine..."
    Invoke-WebRequest -Uri $sunshineUrl -OutFile $sunshineExe -UseBasicParsing
    Write-Host "  安装中（需手动完成配对）..."
    Start-Process -FilePath $sunshineExe -Wait
    Write-Host "  ✅ Sunshine 已安装，访问 https://localhost:47990 配对" -ForegroundColor Green
} else {
    Write-Host "  ✅ 已安装，跳过" -ForegroundColor Green
}

# ============ 5. Input Leap (跨屏互控) ============
Write-Host "[5/5] 安装 Input Leap..." -ForegroundColor Yellow
$inputLeapUrl = "https://github.com/input-leap/input-leap/releases/latest/download/InputLeap-windows-x64.msi"
$inputLeapMsi = "$DownloadDir\InputLeap.msi"
if (-not (Test-Path "C:\Program Files\InputLeap\inputleapc.exe")) {
    Write-Host "  下载 Input Leap..."
    Invoke-WebRequest -Uri $inputLeapUrl -OutFile $inputLeapMsi -UseBasicParsing
    Write-Host "  安装中..."
    Start-Process msiexec -Args "/i `"$inputLeapMsi`" /qn" -Wait
    Write-Host "  ✅ Input Leap 已安装" -ForegroundColor Green
} else {
    Write-Host "  ✅ 已安装，跳过" -ForegroundColor Green
}

# ============ 总结 ============
Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Cyan
Write-Host "  1. Clash Verge Rev → 打开后导入 mihomo-config.yaml"
Write-Host "  2. FlClash         → 备用代理客户端"
Write-Host "  3. Sunshine        → https://localhost:47990 配对 NixOS Moonlight"
Write-Host "  4. Input Leap      → 配置为 Client，Server IP: NixOS IP"
Write-Host ""
Write-Host "代理配置文件: $clashConfigDir\imported-from-nixos.yaml"
Write-Host "30+ 节点（HK/SG/JP/US/KR/TW）已包含"
Write-Host ""
Read-Host "按回车退出"
