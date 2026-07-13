@echo off
chcp 65001 >nul
title 微信聊天记录自动同步 - 一键安装

echo.
echo =============================================
echo   微信聊天记录自动同步 - 一键安装
echo =============================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 需要管理员权限，正在提权...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 创建工作目录
if not exist "C:\WeChatSync" mkdir "C:\WeChatSync"
if not exist "C:\WeChatSync\decrypted" mkdir "C:\WeChatSync\decrypted"

:: 复制脚本到工作目录
copy /y "%~dp0wechat-auto-decrypt.ps1" "C:\WeChatSync\" >nul
copy /y "%~dp0setup-wechat-task.ps1" "C:\WeChatSync\" >nul

echo [1/4] 安装 PyWxDump...
where pip >nul 2>&1
if %errorlevel% equ 0 (
    pip install -U pywxdump >nul 2>&1
    if %errorlevel% equ 0 (
        echo       √ PyWxDump 安装成功
    ) else (
        echo       ! pip 安装失败，尝试下载 EXE 版...
        goto :download_exe
    )
) else (
    echo       ! 未找到 pip，尝试下载 EXE 版...
    goto :download_exe
)
goto :setup_task

:download_exe
echo       正在下载 wxdump.exe ...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/xaoyaoo/PyWxDump/releases/latest/download/wxdump.exe' -OutFile 'C:\WeChatSync\wxdump.exe'" 2>nul
if exist "C:\WeChatSync\wxdump.exe" (
    echo       √ wxdump.exe 下载成功
) else (
    echo       × 下载失败，请手动下载到 C:\WeChatSync\wxdump.exe
    echo         https://github.com/xaoyaoo/PyWxDump/releases
)

:setup_task
echo.
echo [2/4] 创建定时解密任务...
powershell -ExecutionPolicy Bypass -File "C:\WeChatSync\setup-wechat-task.ps1" >nul 2>&1
echo       √ 计划任务已创建（每小时 + 开机自启）

echo.
echo [3/4] 检查 Syncthing...
where syncthing >nul 2>&1
if %errorlevel% equ 0 (
    echo       √ Syncthing 已安装
) else (
    echo       ! Syncthing 未安装
    echo       正在下载 Syncthing...
    powershell -Command "$url='https://github.com/syncthing/syncthing/releases/latest/download/syncthing-windows-amd64.zip'; Invoke-WebRequest -Uri $url -OutFile 'C:\WeChatSync\syncthing.zip'" 2>nul
    if exist "C:\WeChatSync\syncthing.zip" (
        powershell -Command "Expand-Archive -Force 'C:\WeChatSync\syncthing.zip' 'C:\WeChatSync\syncthing'" 2>nul
        echo       √ Syncthing 已下载到 C:\WeChatSync\syncthing\
        echo       ※ 请手动运行一次 syncthing.exe 完成初始化
    ) else (
        echo       × 下载失败，请手动安装: https://syncthing.net/downloads/
    )
)

echo.
echo [4/4] 首次执行解密...
echo       确保微信正在运行...
tasklist /fi "imagename eq WeChat.exe" 2>nul | find /i "WeChat.exe" >nul
if %errorlevel% equ 0 (
    echo       √ 微信正在运行
    powershell -ExecutionPolicy Bypass -File "C:\WeChatSync\wechat-auto-decrypt.ps1"
) else (
    echo       ! 微信未运行，跳过首次解密
    echo       请启动微信后手动运行:
    echo       powershell C:\WeChatSync\wechat-auto-decrypt.ps1
)

echo.
echo =============================================
echo   安装完成！
echo =============================================
echo.
echo   解密脚本: C:\WeChatSync\wechat-auto-decrypt.ps1
echo   解密输出: C:\WeChatSync\decrypted\
echo   执行日志: C:\WeChatSync\sync.log
echo   定时任务: 每小时自动运行 + 开机自启
echo.
echo   下一步:
echo   1. 打开 Syncthing (http://localhost:8384)
echo   2. 添加共享文件夹: C:\WeChatSync\decrypted
echo   3. 连接 NixOS 主机的 Syncthing
echo.
echo   NixOS 端接收路径:
echo   ~/xwechat_files/wxid_bjo2p0swoxm822_fe61/decrypted/
echo.
pause
