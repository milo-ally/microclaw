@echo off
:: Set codepage to support basic characters (avoid garbled code)
chcp 65001 > nul 2>&1

:: Define virtual environment name (fixed variable syntax)
set "VENV_NAME=.venv"

echo Checking Python environment...
:: Check Python availability (compatible with python/python3)
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
echo microclaw environment is ready.
echo.
echo Next steps (Windows):
echo   1^)  Activate venv:
echo        call .venv\Scripts\activate.bat
echo   2^)  Start gateway ^(in one terminal^):
echo        python -m uvicorn microclaw.gateway:app --host 127.0.0.1 --port 8000
echo   3^)  Start TUI ^(in another terminal^):
echo        python -m microclaw.tui --gateway http://127.0.0.1:8000
echo       or start GUI:
echo        microclaw gui --port 8000
echo.
echo This script only installs dependencies and does not start services automatically.
echo.
pause
