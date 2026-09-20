@echo off
chcp 65001 >nul
cd /d "%~dp0"

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

echo ========================================
echo 正在打开【配置账号】图形窗口...
echo.
echo 注意：弹出来的【图形窗口】才是操作界面（改账号/文案/端口）
echo       这个黑窗口只是启动器，不要关它，关掉图形窗口它自动结束
echo ========================================
echo.

%PY% app\gui.py

echo.
if errorlevel 1 (
    echo [XX] 配置窗口异常退出，请查看上方红色错误信息。
) else (
    echo 配置窗口已关闭。
)
pause