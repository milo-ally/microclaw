@echo off
chcp 65001 > nul
set VENV_NAME=.venv

echo Checking for virtual environment...
if not exist "%VENV_NAME%" (
    echo Virtual environment not found, creating %VENV_NAME%...
    python -m venv "%VENV_NAME%"
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

echo.
echo Upgrading pip...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

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
echo Starting microclaw GUI on port 8000...
echo ============================================
echo.

echo Tip: For CLI mode, you can run: microclaw onboard
echo.

REM 启动 microclaw GUI
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
