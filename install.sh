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
echo ""
echo "microclaw environment is ready."
echo ""
echo "Next steps (Linux / macOS):"
echo "  1) Activate venv:"
echo "       source .venv/bin/activate"
echo "  2) Start gateway (in one terminal):"
echo "       python -m uvicorn microclaw.gateway:app --host 127.0.0.1 --port 8000"
echo "  3) Start TUI (in another terminal):"
echo "       python -m microclaw.tui --gateway http://127.0.0.1:8000"
echo "     or start GUI:"
echo "       microclaw gui --port 8000"
echo ""
echo "This script only installs dependencies and does not start services automatically."

