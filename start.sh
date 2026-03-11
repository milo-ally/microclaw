#!/bin/bash
set -euo pipefail

# 定义虚拟环境名称
VENV_NAME=".venv"
START_SUCCESS=0

echo "Attempting to start microclaw GUI on port 8000..."
echo

# 检查脚本权限
if [ ! -x "$0" ]; then
    echo "Error: Script does not have execute permission!"
    echo "Please run: chmod +x start.sh"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -d "$VENV_NAME/bin" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run install.sh first to complete the installation."
    exit 1
fi

# 激活虚拟环境并启动
source "$VENV_NAME/bin/activate"
if ! microclaw gui --port 8000; then
    START_SUCCESS=1
fi

# 启动失败提示
if [ "$START_SUCCESS" -eq 1 ]; then
    echo
    echo "Error: Failed to start microclaw GUI!"
    echo "Possible reasons:"
    echo "1. Dependencies are not installed correctly"
    echo "2. microclaw is not installed in editable mode"
    echo
    echo "Please run install.sh to reinstall and try again."
    exit 1
fi
