# Dependencies (microclaw 0.1.0)

This project is intentionally “batteries included”, but many packages are **optional** depending on what features you use.

## Core (required)

- **Runtime**: Python **>= 3.12**
- **Server**: `fastapi`, `uvicorn`
- **LLM integration**: `openai`, `langchain`, `langchain-openai`, `tiktoken`
- **UI**:
  - **TUI**: no extra deps beyond core
  - **GUI**: `gradio`

## Optional feature groups

- **SSE helper**: `sse-starlette`
  - Microclaw **can run without it** (it falls back to Starlette streaming).
  - Installing it improves SSE ergonomics.

- **RAG / indexing (optional)**: `llama-index*`
  - Only needed if you use the LlamaIndex-based pieces.

- **Tavily search (optional)**: `langchain-tavily`
  - Only needed when `tavily_search_tool` is enabled in `config.json`.

- **PostgreSQL tools (optional)**: `sqlalchemy`, `psycopg2-binary`
  - Only needed when `sql_tools` is enabled.

- **DeepAgent (optional)**: `deepagents`
  - Only needed when `deepagent` mode is enabled.

## Notes about environments

- **Use the project `.venv`**.
  - The `microclaw` CLI prefers `./.venv/bin/python` when present, to avoid accidentally launching the gateway with a different interpreter (e.g. conda) that may miss dependencies like `langchain`.

