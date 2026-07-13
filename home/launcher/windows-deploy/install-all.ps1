# Windows 主机联动部署脚本
# 自动安装 Sunshine + Python + Syncthing + PyWxDump

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Windows 主机联动部署 ===" -ForegroundColor Cyan
Write-Host ""

# 创建临时目录
$TempDir = "$env:TEMP\windows-deploy"
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

# 1. 安装 Sunshine
Write-Host "[1/4] 安装 Sunshine 串流服务..." -ForegroundColor Yellow
$SunshineUrl = "https://github.com/LizardByte/Sunshine/releases/latest/download/sunshine-windows-installer.exe"
$SunshineInstaller = "$TempDir\sunshine-installer.exe"
if (-not (Test-Path "C:\Program Files\Sunshine")) {
    Write-Host "  下载 Sunshine..."
    Invoke-WebRequest -Uri $SunshineUrl -OutFile $SunshineInstaller -UseBasicParsing
    Write-Host "  安装 Sunshine（需要管理员权限）..."
    Start-Process -FilePath $SunshineInstaller -ArgumentList "/S" -Wait -Verb RunAs
    Write-Host "  ✓ Sunshine 安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✓ Sunshine 已安装" -ForegroundColor Green
}

# 2. 安装 Python 3.12
Write-Host "[2/4] 安装 Python 3.12..." -ForegroundColor Yellow
$PythonInstaller = "$TempDir\python-installer.exe"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  下载 Python 3.12..."
    $PythonUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonInstaller -UseBasicParsing
    Write-Host "  安装 Python（添加到 PATH）..."
    Start-Process -FilePath $PythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    Write-Host "  ✓ Python 安装完成" -ForegroundColor Green
    # 刷新环境变量
    $MachinePath = [System.Environment]::GetEnvironmentVariable("Path","Machine")
    $UserPath = [System.Environment]::GetEnvironmentVariable("Path","User")
    $env:Path = "$MachinePath;$UserPath"
} else {
    Write-Host "  ✓ Python 已安装" -ForegroundColor Green
}

# 3. 安装 Syncthing
Write-Host "[3/4] 安装 Syncthing..." -ForegroundColor Yellow
$SyncthingDir = "C:\Program Files\Syncthing"
if (-not (Test-Path "$SyncthingDir\syncthing.exe")) {
    Write-Host "  下载 Syncthing..."
    $SyncthingUrl = "https://github.com/syncthing/syncthing/releases/latest/download/syncthing-windows-amd64-v1.28.1.zip"
    $SyncthingZip = "$TempDir\syncthing.zip"
    Invoke-WebRequest -Uri $SyncthingUrl -OutFile $SyncthingZip -UseBasicParsing
    Write-Host "  解压 Syncthing..."
    Expand-Archive -Path $SyncthingZip -DestinationPath $TempDir -Force
    New-Item -ItemType Directory -Force -Path $SyncthingDir | Out-Null
    Copy-Item "$TempDir\syncthing-windows-amd64-*\syncthing.exe" -Destination $SyncthingDir
    Write-Host "  配置 Syncthing 服务..."
    Start-Process -FilePath "$SyncthingDir\syncthing.exe" -ArgumentList "--no-browser","--no-restart" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "  ✓ Syncthing 安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✓ Syncthing 已安装" -ForegroundColor Green
}

# 4. 安装 PyWxDump
Write-Host "[4/4] 安装 PyWxDump..." -ForegroundColor Yellow
try {
    python -m pip install --upgrade pip -q
    python -m pip install pywxdump -q
    Write-Host "  ✓ PyWxDump 安装完成" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ PyWxDump 安装失败: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Green
Write-Host "下一步："
Write-Host "  1. 打开浏览器访问 https://localhost:47990 配置 Sunshine"
Write-Host "  2. 打开浏览器访问 http://localhost:8384 配置 Syncthing"
Write-Host "  3. 在 NixOS 上运行 moonlight-qt 连接此主机"
