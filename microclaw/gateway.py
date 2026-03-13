"""
FastAPI gateway layer for ComputerUseAgent.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
try:
    # Preferred implementation (better SSE ergonomics).
    from sse_starlette.sse import EventSourceResponse  # type: ignore
except Exception:  # pragma: no cover
    # Fallback: avoid hard dependency on sse-starlette.
    from starlette.responses import StreamingResponse

    class EventSourceResponse(StreamingResponse):
        def __init__(self, content, status_code: int = 200, headers=None):
            super().__init__(content=content, status_code=status_code, headers=headers, media_type="text/event-stream")

from microclaw.config import (
    CONFIG_FILE,
    get_base_dir,
    load_config,
    save_config,
)
from graph.agent import agent_manager
from graph.session_manager import session_manager
from tools.skills_scanner import scan_skills


app = FastAPI(title="ComputerUseAgent Gateway", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _template_dir() -> Path:
    """
    Resolve the agent template directory.

    In some layouts (like this project), the repository root contains a
    `microclaw/agent` directory instead of a top-level `agent` directory.
    We prefer CONFIG_FILE.parent / "agent", but fall back to
    CONFIG_FILE.parent / "microclaw" / "agent" when needed.
    """
    primary = CONFIG_FILE.parent / "agent"
    if primary.exists():
        return primary

    alt = CONFIG_FILE.parent / "microclaw" / "agent"
    if alt.exists():
        return alt

    # Preserve previous behaviour if nothing is found, but clarify path.
    raise HTTPException(
        status_code=500,
        detail=(
            f"Template not found. Tried: {primary} and {alt}. "
            "Cannot initialize workspace."
        ),
    ) from None


@app.on_event("startup")
def _startup_init() -> None:
    try:
        base_dir_str = ""
        try:
            base_dir_str = get_base_dir()
        except Exception:
            return

        base_dir = Path(base_dir_str)
        if not base_dir.exists():
            _init_workspace_from_template(base_dir)
        _ensure_runtime_initialized(base_dir)
    except Exception:
        return


class ConfigPatch(BaseModel):
    platform: Optional[str] = None
    base_dir: Optional[str] = None
    rag_mode: Optional[bool] = None
    deepagent: Optional[bool] = None
    llm: Optional[dict[str, Any]] = None
    embeddings: Optional[dict[str, Any]] = None
    tools: Optional[dict[str, Any]] = None
    mcps: Optional[dict[str, Any]] = None


class ChatStreamRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=64)
    message: str = Field(min_length=1)
    is_reasoning_model: bool = False
    image_url: Optional[str] = None


def _ensure_runtime_initialized(base_dir: Path) -> None:
    base_dir = base_dir.resolve()
    if not base_dir.exists():
        _init_workspace_from_template(base_dir)
    else:
        # IMPORTANT: Do not "heal" deleted template files on every request.
        #
        # Users are expected to delete onboarding files like `workplace/BOOTSTRAP.md`
        # after first-time setup. Previously we copied any missing template files
        # into an existing base_dir on every chat request, which re-created
        # BOOTSTRAP.md repeatedly and caused prompt drift / hallucinations.
        #
        # We only ensure the required runtime directory structure exists.
        for d in ("memory", "sessions", "skills", "storage", "workplace"):
            (base_dir / d).mkdir(parents=True, exist_ok=True)

    session_manager.initialize(base_dir)
    agent_manager.initialize(base_dir=base_dir)
    scan_skills(base_dir=base_dir)


def _init_workspace_from_template(target_dir: Path) -> None:
    template = _template_dir()
    target_dir = target_dir.resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, target_dir)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "config_file": str(CONFIG_FILE),
        "config_exists": CONFIG_FILE.exists(),
    }


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    return load_config()


@app.put("/api/config")
def update_config(patch: ConfigPatch) -> dict[str, Any]:
    current = load_config()
    updates = patch.model_dump(exclude_unset=True)
    merged = {**current, **updates}

    for k in ("llm", "embeddings"):
        block = merged.get(k)
        if isinstance(block, dict):
            block["format"] = "openai"

    if "base_dir" in updates and updates.get("base_dir"):
        base_dir_val = str(updates["base_dir"]).strip()
        if base_dir_val:
            target = Path(base_dir_val).resolve()
            if not target.exists():
                _init_workspace_from_template(target)

    save_config(merged)
    return merged


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    base_dir = Path(get_base_dir())
    session_manager.initialize(base_dir)
    return session_manager.list_sessions()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    base_dir = Path(get_base_dir())
    session_manager.initialize(base_dir)
    return session_manager.get_raw_messages(session_id)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, Any]:
    base_dir = Path(get_base_dir())
    session_manager.initialize(base_dir)
    session_manager.delete_session(session_id)
    return {"deleted": True, "session_id": session_id}


_WORKSPACE_KEEP_DIRS = frozenset({"memory", "sessions", "skills", "storage", "workplace"})


@app.post("/api/cleanup")
def cleanup_workspace() -> dict[str, Any]:
    base_dir = Path(get_base_dir())
    if not base_dir.exists():
        raise HTTPException(status_code=400, detail=f"base_dir not found: {base_dir}")
    removed: list[str] = []
    for item in base_dir.iterdir():
        if item.name not in _WORKSPACE_KEEP_DIRS:
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed.append(item.name)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to remove {item.name}: {e}") from e
    return {"status": "ok", "removed": removed, "kept": list(_WORKSPACE_KEEP_DIRS)}


@app.post("/api/sessions/{session_id}/clear")
def clear_session(session_id: str) -> dict[str, Any]:
    base_dir = Path(get_base_dir())
    session_manager.initialize(base_dir)
    session_manager.clear_messages(session_id)
    return {"cleared": True, "session_id": session_id}


async def _maybe_compress_history(session_id: str) -> None:
    to_compress, num = session_manager.get_messages_to_compress(session_id)
    if not to_compress or num <= 0:
        return
    try:
        summary = await agent_manager.summarize_messages(to_compress)
        if summary:
            session_manager.compress_history_to_system_message(session_id, summary, num)
    except Exception:
        pass


async def _sse_event_generator(req: ChatStreamRequest) -> AsyncGenerator[dict[str, str], None]:
    try:
        base_dir = Path(get_base_dir())
        if not base_dir.exists():
            raise HTTPException(status_code=400, detail=f"base_dir not found: {base_dir}")

        _ensure_runtime_initialized(base_dir)
        history = session_manager.load_session_for_agent(req.session_id)

        session_manager.save_message(req.session_id, "user", req.message)
        await _maybe_compress_history(req.session_id)

        async for event in agent_manager.astream(
            message=req.message,
            history=history,
            image_url=req.image_url,
        ):
            event_type = event.get("type")

            if event_type == "ai_message":
                content = event.get("content") or ""
                if content:
                    session_manager.save_message(req.session_id, "assistant", content)
                    await _maybe_compress_history(req.session_id)

            elif event_type == "toolcall_message":
                content = event.get("content") or ""
                if content:
                    session_manager.save_message(req.session_id, "assistant", content)
                    await _maybe_compress_history(req.session_id)

            elif event_type == "tool_call":
                tool_name = event.get("tool") or ""
                tool_input = event.get("input") or ""
                if tool_name or tool_input:
                    parts: list[str] = []
                    if tool_name:
                        parts.append(f"ToolName: {tool_name}")
                    content = " | ".join(parts)
                    session_manager.save_message(req.session_id, "tool_call", content)
                    await _maybe_compress_history(req.session_id)

            elif event_type == "tool_response":
                tool_output = event.get("output") or ""
                if tool_output:
                    session_manager.save_message(req.session_id, "tool_response", tool_output)
                    await _maybe_compress_history(req.session_id)

            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

        yield {"event": "end", "data": json.dumps({"type": "stream_ended"}, ensure_ascii=False)}

    except HTTPException as e:
        detail = e.detail
        msg = ""
        if isinstance(detail, str):
            msg = detail.strip()
        elif detail is not None:
            msg = str(detail).strip()
        if not msg:
            msg = f"HTTPException {e.status_code or ''}".strip()
        yield {"event": "error", "data": json.dumps({"type": "error", "content": msg}, ensure_ascii=False)}

    except Exception as e:
        msg = str(e).strip() or e.__class__.__name__
        yield {"event": "error", "data": json.dumps({"type": "error", "content": msg}, ensure_ascii=False)}


@app.post("/api/chat/stream")
async def chat_stream(req: ChatStreamRequest):
    return EventSourceResponse(_sse_event_generator(req), media_type="text/event-stream")


def _workplace_dir() -> Path:
    return Path(get_base_dir()) / "workplace"


def _memory_file() -> Path:
    return Path(get_base_dir()) / "memory" / "MEMORY.md"


@app.get("/api/files/workplace")
def list_workplace_md() -> list[str]:
    wp = _workplace_dir()
    if not wp.exists():
        return []
    return sorted(f.name for f in wp.glob("*.md"))


@app.get("/api/files/workplace/{filename}")
def read_workplace_file(filename: str) -> dict[str, Any]:
    if not filename.endswith(".md") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Only .md files allowed, no path traversal")
    fp = (_workplace_dir() / filename).resolve()
    if not fp.exists() or not fp.is_file() or not str(fp).startswith(str(_workplace_dir().resolve())):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    try:
        content = fp.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"filename": filename, "content": content}


class FileContent(BaseModel):
    content: str


@app.put("/api/files/workplace/{filename}")
def write_workplace_file(filename: str, body: FileContent) -> dict[str, Any]:
    if not filename.endswith(".md") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Only .md files allowed, no path traversal")
    wp = _workplace_dir()
    wp.mkdir(parents=True, exist_ok=True)
    fp = wp / filename
    try:
        fp.write_text(body.content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"filename": filename, "saved": True}


@app.get("/api/files/memory")
def read_memory() -> dict[str, Any]:
    fp = _memory_file()
    if not fp.exists():
        return {"filename": "MEMORY.md", "content": ""}
    try:
        content = fp.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"filename": "MEMORY.md", "content": content}


@app.put("/api/files/memory")
def write_memory(body: FileContent) -> dict[str, Any]:
    fp = _memory_file()
    fp.parent.mkdir(parents=True, exist_ok=True)
    try:
        fp.write_text(body.content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"filename": "MEMORY.md", "saved": True}

