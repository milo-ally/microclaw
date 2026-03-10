# Microclaw

## 快速开始 
需要的python版本: python>=3.12.3
### 1. 配置环境 

```python 
python -m venv .venv 
source ./.venv/bin/activate
pip install -r requirements.txt
```

### 2. 补充目录结构

在项目根目录下(app.py同级目录下)创建 `agent` 文件夹, 目录结构如下: 

```bash
.
├── memory
│   ├── logs
│   └── MEMORY.md
├── sessions
│   └── default.json
├── skills
│   ├── docx
│   |     ├── ... 
│   └── xlsx
│       ├── ... 
├── storage
│   └── memory_index
│       ├── default__vector_store.json
│       ├── docstore.json
│       ├── graph_store.json
│       ├── image__vector_store.json
│       └── index_store.json
└── workplace
    ├── AGENTS.md
    ├── IDENTITY.md
    ├── SOUL.md
    └── USER.md
```

其中 `skills` 目录参照 https://github.com/anthropics/skills/tree/main/skills 下的每一个条目。本项目兼容 anthropic skills 格式。

### 3. 填写配置文件

将 `example` 文件夹下的 `config.json` 文件放在项目根目录下, 填写相应信息。(注意AI网关统一用openai格式调用, 包括embedding模型, chat模型等。 )

### 4. 启动（推荐：microclaw 一键启动）

```bash
# 安装
pip install -e .

# TUI 模式（终端界面）
microclaw tui
microclaw tui --port 7132
microclaw tui -- port 7132

# GUI 模式（Gradio 网页界面：流式对话、配置、会话、workplace/memory 文件编辑）
microclaw gui
microclaw gui -- port 7132
microclaw gui --port 7132 --gui-port 7860
```

