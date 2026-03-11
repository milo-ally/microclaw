@echo off
:: 强制设置编码为UTF-8（兼容中文，避免乱码）
chcp 65001 > nul 2>&1

:: 定义虚拟环境名称（避免变量解析错误）
set "VENV_NAME=.venv"

echo Checking Python environment...
:: 检查python是否可用，优先兼容python3命令
python --version > nul 2>&1
if errorlevel 1 (
    python3 --version > nul 2>&1
    if errorlevel 1 (
        echo Error: Python is not installed or not in PATH!
        echo Please install Python and add it to system environment variables.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=python3"
    )
) else (
    set "PY_CMD=python"
)

echo.
echo Checking for virtual environment...
if not exist "%VENV_NAME%" (
    echo Virtual environment not found, creating %VENV_NAME%...
    %PY_CMD% -m venv "%VENV_NAME%"
    if errorlevel 1 (
        echo Error: Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment %VENV_NAME% already exists.
)

echo.
echo Activating virtual environment...
call "%VENV_NAME%\Scripts\activate.bat"
if errorlevel 1 (
    echo Error: Failed to activate virtual environment!
    pause
    exit /b 1
)

echo.
echo Upgrading pip...
%PY_CMD% -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo Error: Failed to upgrade pip!
    pause
    exit /b 1
)

echo.
echo Installing project dependencies...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo Error: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo Installing project in editable mode...
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo Error: Failed to install project!
    pause
    exit /b 1
)

echo.
echo Installation completed successfully!
echo.
echo Tip: For CLI mode, you can run: microclaw onboard
echo.
echo Starting microclaw GUI on port 8000...
echo.

:: 启动 microclaw GUI
microclaw gui --port 8000

if errorlevel 1 (
    echo.
    echo Error: Failed to start microclaw GUI!
    echo Please check if the installation was successful.
    echo.
    echo To activate the virtual environment, run: %VENV_NAME%\Scripts\activate.bat
    echo After activation, start the program with: microclaw onboard
    pause
    exit /b 1
)

:: 防止窗口闪退（可选）
pause
