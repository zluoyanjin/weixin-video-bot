@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   微信视频号机器人
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

%PY% -c "import playwright" 2>nul
if errorlevel 1 (
    echo [XX] 还没安装 Playwright，请先双击 安装环境.bat
    pause
    exit /b 1
)

%PY% app\main.py

echo.
echo ========================================
echo   程序已停止（Chrome 不会被关闭）
echo ========================================
echo.
pause
