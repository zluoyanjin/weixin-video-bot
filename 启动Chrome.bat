@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   微信视频号机器人 - 启动 Chrome
echo ========================================
echo.

set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
    set "PY=py"
    where py >nul 2>nul
    if errorlevel 1 (
        echo [XX] 没有检测到 Python，请先运行 安装环境.bat
        pause
        exit /b 1
    )
)

%PY% app\chrome.py

echo.
echo ========================================
echo   请在每个 Chrome 窗口中：
echo   1. 登录对应的视频号
echo   2. 进入要发言的直播间
echo   然后双击 启动机器人.bat
echo ========================================
echo.
pause
