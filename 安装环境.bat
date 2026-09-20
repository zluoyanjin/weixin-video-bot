@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   微信视频号机器人 - 环境安装
echo ========================================
echo.

set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
    set "PY=py"
    where py >nul 2>nul
)

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo [XX] 没有检测到 Python
        echo.
        echo 请先安装 Python 3.10 或更高版本：
        echo   https://www.python.org/downloads/
        echo 安装时务必勾选 "Add Python.exe to PATH"
        echo.
        pause
        exit /b 1
    )
)

echo [1/2] Python 版本：
%PY% --version
echo.

echo [2/2] 正在安装 Playwright，请耐心等待...
echo.
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [XX] 安装失败，请把上面的红色错误截图发给我
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   安装完成
echo ========================================
echo.
echo 说明：不会下载任何浏览器内核，
echo 机器人连接的是你自己的 Chrome。
echo.
echo 下一步：双击 启动Chrome.bat
echo ========================================
echo.
pause
