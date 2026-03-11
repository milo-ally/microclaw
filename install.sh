#!/bin/bash
set -e
VENV_NAME=".venv"

echo "Checking for virtual environment..."
if [ ! -d "$VENV_NAME" ]; then
    echo "Virtual environment not found, creating $VENV_NAME..."
    python3 -m venv "$VENV_NAME"
    echo "Virtual environment created successfully."
else
    echo "Virtual environment $VENV_NAME already exists."
fi

echo ""
echo "Activating virtual environment..."
source "$VENV_NAME/bin/activate"

echo ""
echo "Upgrading pip..."
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""
echo "Installing project dependencies..."
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""
echo "Installing project in editable mode..."
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""
echo "Installation completed successfully!"
echo "To activate the virtual environment, run: source $VENV_NAME/bin/activate"
echo "After activation, start the program with: microclaw onboard"
