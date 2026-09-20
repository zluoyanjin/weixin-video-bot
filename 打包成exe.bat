@echo off
chcp 65001 >nul

cd /d "%~dp0"



echo ========================================

echo   打包成 视频号机器人.exe

echo   （开发者在自己电脑上执行，客户不需要）

echo ========================================

echo.



set "PY=python"

where python >nul 2>nul

if errorlevel 1 (

    set "PY=py"

)



%PY% -m pip install pyinstaller

if errorlevel 1 (

    echo [XX] PyInstaller 安装失败

    pause

    exit /b 1

)



echo 正在打包，需要几分钟，请耐心等待...

echo.



%PY% -m PyInstaller --noconfirm --clean --onefile --noconsole --name "视频号机器人" --collect-all playwright --hidden-import playwright.sync_api app\gui.py



if errorlevel 1 (

    echo.

    echo [XX] 打包失败，请把上面的错误截图

    pause

    exit /b 1

)



echo.

echo ========================================

echo   已生成 dist\视频号机器人.exe

echo   把它和 config、chrome_profiles 放在同一层发给客户

echo ========================================

echo.

pause

