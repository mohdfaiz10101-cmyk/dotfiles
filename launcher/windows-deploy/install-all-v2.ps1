# Windows Host Deployment Script
# Auto-install: Sunshine + Python + Syncthing + PyWxDump

$ErrorActionPreference = "Stop"

Write-Host "=== Windows Host Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Create temp directory
$TempDir = "$env:TEMP\windows-deploy"
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

# 1. Install Sunshine
Write-Host "[1/4] Installing Sunshine..." -ForegroundColor Yellow
$SunshineUrl = "https://github.com/LizardByte/Sunshine/releases/latest/download/sunshine-windows-installer.exe"
$SunshineInstaller = "$TempDir\sunshine-installer.exe"
if (-not (Test-Path "C:\Program Files\Sunshine")) {
    Write-Host "  Downloading Sunshine..."
    Invoke-WebRequest -Uri $SunshineUrl -OutFile $SunshineInstaller -UseBasicParsing
    Write-Host "  Installing Sunshine (requires admin)..."
    Start-Process -FilePath $SunshineInstaller -ArgumentList "/S" -Wait -Verb RunAs
    Write-Host "  [OK] Sunshine installed" -ForegroundColor Green
} else {
    Write-Host "  [OK] Sunshine already installed" -ForegroundColor Green
}

# 2. Install Python 3.12
Write-Host "[2/4] Installing Python 3.12..." -ForegroundColor Yellow
$PythonInstaller = "$TempDir\python-installer.exe"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  Downloading Python 3.12..."
    $PythonUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonInstaller -UseBasicParsing
    Write-Host "  Installing Python (adding to PATH)..."
    Start-Process -FilePath $PythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    Write-Host "  [OK] Python installed" -ForegroundColor Green
} else {
    Write-Host "  [OK] Python already installed" -ForegroundColor Green
}

# 3. Install Syncthing
Write-Host "[3/4] Installing Syncthing..." -ForegroundColor Yellow
$SyncthingDir = "C:\Program Files\Syncthing"
if (-not (Test-Path "$SyncthingDir\syncthing.exe")) {
    Write-Host "  Downloading Syncthing..."
    $SyncthingUrl = "https://github.com/syncthing/syncthing/releases/download/v1.28.1/syncthing-windows-amd64-v1.28.1.zip"
    $SyncthingZip = "$TempDir\syncthing.zip"
    Invoke-WebRequest -Uri $SyncthingUrl -OutFile $SyncthingZip -UseBasicParsing
    Write-Host "  Extracting Syncthing..."
    Expand-Archive -Path $SyncthingZip -DestinationPath $TempDir -Force
    New-Item -ItemType Directory -Force -Path $SyncthingDir | Out-Null
    $ExtractedDir = Get-ChildItem "$TempDir\syncthing-windows-amd64-*" | Select-Object -First 1
    Copy-Item "$($ExtractedDir.FullName)\syncthing.exe" -Destination $SyncthingDir
    Write-Host "  Starting Syncthing..."
    Start-Process -FilePath "$SyncthingDir\syncthing.exe" -ArgumentList "--no-browser","--no-restart" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "  [OK] Syncthing installed" -ForegroundColor Green
} else {
    Write-Host "  [OK] Syncthing already installed" -ForegroundColor Green
}

# 4. Install PyWxDump
Write-Host "[4/4] Installing PyWxDump..." -ForegroundColor Yellow
try {
    python -m pip install --upgrade pip -q
    python -m pip install pywxdump -q
    Write-Host "  [OK] PyWxDump installed" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] PyWxDump install failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Open browser: https://localhost:47990 (Sunshine config)"
Write-Host "  2. Open browser: http://localhost:8384 (Syncthing config)"
Write-Host "  3. Run moonlight on NixOS to connect to this host"
