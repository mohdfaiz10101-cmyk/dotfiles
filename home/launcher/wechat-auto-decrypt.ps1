# ============================================================
# 微信数据自动解密脚本（Windows 端）
# 配合 Syncthing 同步到 NixOS HyperChat
#
# 用法：
#   1. 确保微信 PC 版正在运行且已登录
#   2. 以管理员身份运行此脚本，或设置为计划任务
#   3. 解密后的数据在 C:\WeChatSync\decrypted\
# ============================================================

$ErrorActionPreference = "Continue"
$SyncDir = "C:\WeChatSync"
$DecryptedDir = "$SyncDir\decrypted"
$LogFile = "$SyncDir\sync.log"

# 创建目录
New-Item -ItemType Directory -Force -Path $SyncDir | Out-Null
New-Item -ItemType Directory -Force -Path $DecryptedDir | Out-Null

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $msg" | Tee-Object -Append -FilePath $LogFile
}

# 检查微信是否运行
$wechat = Get-Process -Name "WeChat" -ErrorAction SilentlyContinue
if (-not $wechat) {
    Write-Log "[SKIP] 微信未运行，跳过本次解密"
    exit 0
}

Write-Log "[START] 开始解密微信数据库..."

try {
    # 方式1：使用 pywxdump CLI（pip 安装版）
    if (Get-Command "pywxdump" -ErrorAction SilentlyContinue) {
        # 获取微信信息（密钥、数据目录等）
        $info = pywxdump bias -a 2>&1
        Write-Log "[INFO] $info"

        # 解密所有数据库
        pywxdump decrypt -a -o $DecryptedDir 2>&1
        Write-Log "[OK] pywxdump 解密完成"
    }
    # 方式2：使用 wxdump.exe（独立 EXE 版）
    elseif (Test-Path "$SyncDir\wxdump.exe") {
        & "$SyncDir\wxdump.exe" decrypt -a -o $DecryptedDir 2>&1
        Write-Log "[OK] wxdump.exe 解密完成"
    }
    else {
        Write-Log "[ERROR] 未找到 pywxdump 或 wxdump.exe"
        Write-Log "[HELP] 请运行: pip install pywxdump"
        Write-Log "[HELP] 或下载 wxdump.exe 到 $SyncDir"
        exit 1
    }

    # 统计解密结果
    $dbCount = (Get-ChildItem -Path $DecryptedDir -Filter "*.db" -Recurse).Count
    $totalSize = (Get-ChildItem -Path $DecryptedDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Log "[DONE] 已解密 $dbCount 个数据库，总计 $([math]::Round($totalSize, 1)) MB"

} catch {
    Write-Log "[ERROR] 解密失败: $_"
    exit 1
}

Write-Log "[END] 等待 Syncthing 同步到 NixOS..."
