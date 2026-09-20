@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   真实账号体检
echo   只连接、只检查，不会发送任何消息
echo ========================================
echo.
echo   用法：
echo   1. 先双击 启动Chrome.bat
echo   2. 在 Chrome 里登录视频号、进入直播间
echo   3. 再双击本文件
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

%PY% -c "import playwright" 2>nul
if errorlevel 1 (
    echo [XX] 还没安装 Playwright，请先双击 安装环境.bat
    pause
    exit /b 1
)

%PY% app\main.py --probe

echo.
echo ========================================
echo   体检结束
echo ========================================
echo.
pause
