@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   微信视频号机器人 - 自检
echo   不需要真实视频号账号
echo ========================================

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

%PY% app\selftest.py

echo.
echo ========================================
echo   全部 PASS 才能放心交付
echo ========================================
echo.
pause
