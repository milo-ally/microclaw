# Microclaw (ComputerUseAgent)

**Microclaw** 是一个本地运行的 Agent 项目，提供：
- **Gateway**：FastAPI 服务（默认 `127.0.0.1:8000`）
- **TUI**：终端界面
- **GUI**：Gradio Web UI（默认 `127.0.0.1:7860`）

> 说明：本 README 只描述“如何安装/配置/启动”。不会改变任何现有功能与参数约定。

## 极速开始（推荐）

- **Windows**：双击 `install.bat`  
  - 前提：已安装 Python，且 `python` / `pip` 可用
- **Linux**：

```bash
chmod +x install.sh
bash install.sh
```

安装脚本会自动：
- 创建/复用虚拟环境 `.venv`
- 安装依赖 `requirements.txt`
- 以可编辑模式安装项目 `pip install -e .`
- 启动 `microclaw gui --port 8000`（即 Gateway 在 8000 端口）

## 环境要求

- **Python**: `>= 3.12`（建议 `3.12.3+`）

## 从源码安装（手动方式）

```bash
python -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## 配置（必须）

项目通过根目录的 `config.json` 读取运行配置（模型、embedding、工具开关、workspace 路径等）。

### 关键约束：OpenAI-compatible

**重要（硬性要求）**：Chat / Embeddings 提供方都必须提供 **OpenAI-compatible** 接口，因此配置里必须使用：

- `llm.format = "openai"`
- `embeddings.format = "openai"`

如果 `format` 不是 `"openai"`，将无法正常调用模型（网关会按 OpenAI Chat Completions / Embeddings 规范组装请求）。

### 安全提示：不要提交密钥

`config.json` 里包含 `api_key` 等敏感字段，请务必：
- 仅在本地保存真实密钥
- 不要将真实密钥提交到 git/公开仓库

## Workspace 目录结构（必须）

Microclaw 的“工作区”**默认使用当前用户 home 目录下的隐藏目录 `~/.microclaw`**。

- 首次运行 `microclaw onboard` 时，如果 `base_dir` 未配置，将自动建议 `~/.microclaw` 作为 workspace 根目录（回车即可接受）。
- Workspace 会从仓库内的 `agent/` 模板复制/补全目录结构到 `base_dir`，不会覆盖你已有的文件。
- 你也可以在 `config.json` 中手动修改 `base_dir` 为任意路径。

`agent/` 模板目录结构示例：

```bash
agent
├── memory
│   ├── logs
│   └── MEMORY.md
├── sessions
│   └── default.json
├── skills
│   ├── docx
│   │   └── ...
│   └── xlsx
│       └── ...
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

其中 `skills/` 目录可参考 `anthropics/skills` 的每一个条目格式（本项目兼容 anthropic skills 格式）：  
`https://github.com/anthropics/skills/tree/main/skills`

## 启动方式

### 一键引导（推荐）：`microclaw onboard`

`microclaw onboard` 会做一个交互式引导：
- 填写/补全 `config.json` 的关键字段（包括 `base_dir`、LLM/Embeddings、工具开关）
- 启动 Gateway 并做健康检查
- 让你选择启动 TUI 或 GUI

```bash
microclaw onboard
microclaw onboard --port 7132
```

### TUI（终端界面）

```bash
microclaw tui
microclaw tui --port 7132
microclaw tui -- port 7132
```

### GUI（Gradio Web UI）

```bash
microclaw gui
microclaw gui --port 7132
microclaw gui --port 7132 --gui-port 7860
microclaw gui -- port 7132
```

### 仅启动 Gateway（高级用法）

如果你只想启动 FastAPI Gateway（不启动 TUI/GUI），请使用：

```bash
python -m uvicorn microclaw.gateway:app --host 127.0.0.1 --port 8000
```

> 说明：本项目已移除旧的兼容启动方式（例如 `uvicorn gateway:app` / `run_gateway.py` 等）。

## 端口与环境变量

- **Gateway Host/Port**：
  - 环境变量：`GATEWAY_HOST`（默认 `127.0.0.1`）、`GATEWAY_PORT`（默认 `8000`）
  - CLI 参数：`microclaw {tui|gui|onboard} --port <PORT>`
- **GUI 端口**：
  - CLI 参数：`microclaw gui --gui-port <PORT>`（默认 `7860`）

## 常见问题（Troubleshooting）

- **启动时提示 config 缺失/不完整**：运行 `microclaw onboard` 补全配置
- **GUI/TUI 启动但无法连接 Gateway**：确认端口未被占用，或改用 `--port` 指定其它端口
- **安装脚本后仍提示未安装**：确认已激活 `.venv`，并执行 `pip install -e .`
- **Windows 双击闪退**：使用 `start.bat`/`install.bat`（会 `pause` 保留窗口输出）

## 安全与使用边界（建议阅读）

Microclaw 可能启用读写文件、执行命令等工具能力。请避免将其暴露给不可信用户或公网环境；如需远程访问，请自行加上访问控制与隔离策略。

