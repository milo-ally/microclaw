@echo off
chcp 65001 > nul 2>&1

:: 定义虚拟环境名称
set "VENV_NAME=.venv"
set "START_SUCCESS=0"

echo Attempting to start microclaw GUI on port 8000...
echo.

:: 先检查虚拟环境是否存在
if not exist "%VENV_NAME%\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please run install.bat first to complete the installation.
    pause
    exit /b 1
)

:: 激活虚拟环境并启动
call "%VENV_NAME%\Scripts\activate.bat" && (
    microclaw gui --port 8000
    if errorlevel 1 (
        set "START_SUCCESS=1"
    )
)

:: 启动失败提示
if "%START_SUCCESS%"=="1" (
    echo.
    echo Error: Failed to start microclaw GUI!
    echo Possible reasons:
    echo 1. Dependencies are not installed correctly
    echo 2. microclaw is not installed in editable mode
    echo.
    echo Please run install.bat to reinstall and try again.
    pause
    exit /b 1
)

:: 防止窗口闪退
pause
