# microclaw (0.1.0)

Local-first agent with:
- **Gateway**: FastAPI server (default `127.0.0.1:8000`)
- **TUI**: terminal UI
- **GUI**: Gradio web UI (default `127.0.0.1:7860`)

## Install

### Script (recommended)

- **Linux**

```bash
chmod +x install.sh
bash install.sh
```

- **Windows**
  - Run `install.bat`

### Manual

```bash
python -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Configure

Copy `config.example.json` to `config.json` and fill your model settings.

```bash
cp config.example.json config.json
```

- **Required**: both `llm.format` and `embeddings.format` must be `"openai"` (OpenAI-compatible API).
- **Security**: `config.json` contains API keys; keep it local (it is in `.gitignore`).
- **Workspace**: default `base_dir` is `~/.microclaw` (created from `agent/` template on first run).

## Run

### Onboarding (recommended)

```bash
microclaw onboard
microclaw onboard --port 7132
```

### TUI

```bash
microclaw tui
microclaw tui --port 7132
```

### GUI

```bash
microclaw gui
microclaw gui --port 7132 --gui-port 7860
```

### Gateway only

```bash
python -m uvicorn microclaw.gateway:app --host 127.0.0.1 --port 8000
```

## Usage tips

- **TUI boot message**: after choosing **`5. Chat`**, answer `boot-md?` to auto-send `Wake up, my friend!`.
- **GUI boot message**: use the **`boot-md`** button in the Chat tab to simulate sending `Wake up, my friend!` (visible in chat history + streamed reply).

## Notes / FAQ

- **BOOTSTRAP.md is not re-created on every message**: the gateway no longer “heals” deleted template files on each request.
- **Dependency overview**: see `DEPENDENCIES.md`.

