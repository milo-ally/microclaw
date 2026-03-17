"""
microclaw GUI - Gradio-based web interface.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import os
import time
from typing import Any, Generator, Optional

import gradio as gr

from microclaw.client import GatewayClient, parse_sse_events


class GuiGatewayClient(GatewayClient):
    def chat_stream(self, payload: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
        """Yield normalized stream events for GUI rendering."""
        for event_name, data in parse_sse_events(self.chat_stream_lines(payload)):
            if event_name == "error":
                try:
                    obj = json.loads(data)
                    yield {"type": "error", "content": obj.get("content", data)}
                except Exception:
                    yield {"type": "error", "content": data}
                continue
            if event_name == "end":
                continue
            try:
                obj = json.loads(data)
            except Exception:
                continue
            et = obj.get("type")
            if et:
                yield obj


_client: Optional[GuiGatewayClient] = None


GUI_CSS = """
    :root {
        --surface: #f6f4ee;
        --surface-strong: #fffdf9;
        --panel: rgba(255, 251, 245, 0.88);
        --panel-strong: #fffdfa;
        --ink: #1f2937;
        --muted: #6b7280;
        --line: rgba(107, 114, 128, 0.16);
        --accent: #5b7cff;
        --accent-deep: #4b63d3;
        --accent-soft: rgba(91, 124, 255, 0.14);
        --olive: #2f855a;
        --shadow: 0 20px 50px rgba(44, 54, 80, 0.10);
        --radius-xl: 28px;
        --radius-lg: 20px;
        --radius-md: 16px;
    }
    .gradio-container {
        max-width: 1180px;
        margin: 0 auto;
        color: var(--ink);
        background:
            radial-gradient(circle at top left, rgba(91, 124, 255, 0.12), transparent 28%),
            radial-gradient(circle at top right, rgba(47, 133, 90, 0.08), transparent 24%),
            linear-gradient(180deg, #fbfaf7 0%, #f2efe8 100%);
    }
    .app-shell {
        border: 1px solid var(--line);
        background: var(--panel);
        backdrop-filter: blur(18px);
        border-radius: var(--radius-xl);
        box-shadow: var(--shadow);
        padding: 22px;
    }
    .hero-bar {
        margin-bottom: 14px;
        padding: 18px 22px;
        border-radius: 22px;
        background:
            linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(247, 248, 252, 0.88)),
            linear-gradient(135deg, rgba(91, 124, 255, 0.06), rgba(47, 133, 90, 0.03));
        border: 1px solid var(--line);
    }
    .hero-title {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin: 0;
    }
    .hero-copy {
        margin-top: 6px;
        color: var(--muted);
        font-size: 14px;
    }
    .model-chip {
        margin-top: 12px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent-deep);
        font-size: 13px;
        font-weight: 700;
    }
    .session-toolbar {
        margin-bottom: 14px;
        padding: 14px;
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid var(--line);
        border-radius: 18px;
    }
    .bottom-actions {
        display: flex;
        gap: 0.75rem;
        justify-content: flex-start;
        flex-wrap: wrap;
    }
    .bottom-actions > button {
        flex: 0 0 auto;
    }
    .clean-note {
        font-size: 0.88rem;
        color: var(--muted);
    }
    .chat-container {
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 6px;
    }
    .chat-container .message-wrap {
        border-radius: 18px !important;
    }
    .chat-container .message.user {
        background: #f4f1ea !important;
        border: 1px solid rgba(107, 114, 128, 0.12) !important;
        color: var(--ink) !important;
    }
    .chat-container .message.bot {
        background: #fffdf9 !important;
        border: 1px solid rgba(107, 114, 128, 0.10) !important;
        color: var(--ink) !important;
    }
    .chat-container .message.bot p,
    .chat-container .message.bot li,
    .chat-container .message.bot code,
    .chat-container .message.bot pre {
        color: inherit !important;
    }
    .chat-container .message.bot pre {
        background: rgba(244, 246, 250, 0.95) !important;
        border: 1px solid rgba(107, 114, 128, 0.08);
    }
    #chat-input textarea {
        min-height: 140px !important;
        border-radius: 20px !important;
        border: 1px solid var(--line) !important;
        background: rgba(255, 255, 255, 0.88) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.65);
        color: var(--ink) !important;
    }
    #send-btn, #boot-btn {
        background: #f7f5f0 !important;
        color: var(--ink) !important;
        border: 1px solid rgba(107, 114, 128, 0.14) !important;
        box-shadow: none !important;
    }
    .fc-inline-card {
        border-radius: 16px;
        background: linear-gradient(180deg, rgba(252, 251, 248, 0.98), rgba(247, 245, 240, 0.98));
        border: 1px solid rgba(107, 114, 128, 0.14);
        padding: 14px 16px;
        color: #243042;
        box-shadow: 0 8px 20px rgba(67, 82, 114, 0.05);
    }
    .fc-inline-card + .fc-inline-card {
        margin-top: 8px;
    }
    .fc-inline-meta {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 8px;
        color: #7a8190;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }
    .fc-inline-title {
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .fc-inline-card pre,
    .fc-inline-card ul,
    .fc-inline-body {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 12px;
        line-height: 1.65;
        color: #243042;
    }
    .fc-inline-card pre {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        border: 1px solid rgba(107, 114, 128, 0.10);
        padding: 10px 12px;
    }
    .fc-inline-card ul {
        padding-left: 18px;
    }
    .fc-inline-thinking {
        border-left: 3px solid #c9c2b6;
    }
    .fc-inline-tool.pending {
        border-left: 3px solid #d2cbc0;
    }
    .fc-inline-tool.done {
        border-left: 3px solid #bdb7aa;
    }
    .fc-inline-rag {
        border-left: 3px solid #d8d2c8;
    }
    .fc-inline-error {
        border-left: 3px solid #d7b8b8;
        background: linear-gradient(180deg, rgba(255, 248, 247, 0.98), rgba(252, 242, 241, 0.98));
    }
    .fc-status {
        min-height: 0;
        margin: 10px 2px 14px 2px;
    }
    .fc-status-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid rgba(107, 114, 128, 0.12);
        background: rgba(255, 252, 246, 0.9);
        color: #4b5563;
        box-shadow: 0 8px 18px rgba(67, 82, 114, 0.04);
    }
    .fc-busy-guard {
        display: none;
        min-height: 0;
        margin: 10px 2px 14px 2px;
    }
    .fc-busy-guard.is-active {
        display: block;
    }
    .fc-status-copy {
        min-width: 0;
        flex: 1;
        font-size: 13px;
        line-height: 1.5;
    }
    .fc-status-title {
        font-weight: 700;
        color: #374151;
    }
    .fc-status-text {
        color: #6b7280;
    }
    .fc-loading {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        min-height: 24px;
    }
    .fc-loading-dot {
        width: 7px;
        height: 7px;
        border-radius: 999px;
        background: #b8b2a7;
        display: inline-block;
        animation: fc-bounce 1.2s infinite ease-in-out;
    }
    .fc-loading-dot:nth-child(2) {
        animation-delay: 0.15s;
    }
    .fc-loading-dot:nth-child(3) {
        animation-delay: 0.3s;
    }
    @keyframes fc-bounce {
        0%, 80%, 100% {
            transform: translateY(0);
            opacity: 0.45;
        }
        40% {
            transform: translateY(-4px);
            opacity: 1;
        }
    }
"""


def _client_or_raise() -> GuiGatewayClient:
    if _client is None:
        raise RuntimeError("Gateway client not initialized")
    return _client


def _health_ui() -> str:
    try:
        c = _client_or_raise()
        h = c.health()
        return f"```json\n{json.dumps(h, ensure_ascii=False, indent=2)}\n```"
    except Exception as e:
        return f"❌ **Error:** {e}"


_TOOL_EXTRA_PARAMS = {
    "sql_tools": [("db_uri", "DB URI")],
    "tavily_search_tool": [("tavily_api_key", "Tavily API Key")],
    "vision_tool": [("base_url", "Base URL"), ("api_key", "API Key"), ("model", "Model")],
}
_COMMON_TOOLS = [
    "ask_user_question_tool",
    "fetch_url_tool",
    "python_repl_tool",
    "sql_tools",
    "read_file_tool",
    "tavily_search_tool",
    "terminal_tool",
    "rm_tool",
    "sed_all_tool",
    "sed_first_tool",
    "write_tool",
    "grep_tool",
    "vision_tool",
]


def _config_load_to_form() -> tuple:
    try:
        c = _client_or_raise()
        cfg = c.get_config()
    except Exception as e:
        raise RuntimeError(f"Failed to load config: {e}") from e

    platform = str(cfg.get("platform", "") or "")
    base_dir = str(cfg.get("base_dir", "") or "")
    rag_mode = bool(cfg.get("rag_mode", False))
    deepagent = bool(cfg.get("deepagent", False))

    llm = cfg.get("llm") or {}
    llm_provider = str(llm.get("provider") or "")
    llm_info = llm.get("info") or {}
    llm_model = str(llm_info.get("model") or "")
    llm_base_url = str(llm_info.get("base_url") or "")
    llm_api_key = str(llm_info.get("api_key") or "")
    llm_temperature = float(llm_info.get("temperature", 0.1))
    llm_is_reasoning_model = bool(llm_info.get("is_reasoning_model", False))
    emb = cfg.get("embeddings") or {}
    emb_provider = str(emb.get("provider") or "")
    emb_info = emb.get("info") or {}
    emb_model = str(emb_info.get("model") or "")
    emb_base_url = str(emb_info.get("base_url") or "")
    emb_api_key = str(emb_info.get("api_key") or "")

    tools = cfg.get("tools") or {}
    tool_checks = []
    tool_extras = []
    for t in _COMMON_TOOLS:
        entry = tools.get(t) or {}
        status = str(entry.get("status", "off")).lower()
        tool_checks.append(status == "on")
        for param_key, _ in _TOOL_EXTRA_PARAMS.get(t, []):
            tool_extras.append(str(entry.get(param_key, "")))

    return (
        platform,
        base_dir,
        rag_mode,
        deepagent,
        llm_provider,
        llm_model,
        llm_base_url,
        llm_api_key,
        llm_temperature,
        llm_is_reasoning_model,
        emb_provider,
        emb_model,
        emb_base_url,
        emb_api_key,
        *tool_checks,
        *tool_extras,
    )


def _config_save_from_form(
    platform: str,
    base_dir: str,
    rag_mode: bool,
    deepagent: bool,
    llm_provider: str,
    llm_model: str,
    llm_base_url: str,
    llm_api_key: str,
    llm_temperature: float,
    llm_is_reasoning_model: bool,
    emb_provider: str,
    emb_model: str,
    emb_base_url: str,
    emb_api_key: str,
    tool_ask: bool,
    tool_fetch: bool,
    tool_python: bool,
    tool_sql: bool,
    tool_read: bool,
    tool_tavily: bool,
    tool_terminal: bool,
    tool_rm: bool,
    tool_sed_all: bool,
    tool_sed_first: bool,
    tool_write: bool,
    tool_grep: bool,
    tool_vision: bool,
    sql_db_uri: str,
    tavily_api_key: str,
    vision_base_url: str,
    vision_api_key: str,
    vision_model: str,
) -> str:
    try:
        c = _client_or_raise()

        def _s(x):
            return (x or "").strip()

        tools_map = {
            "ask_user_question_tool": {"status": "on" if tool_ask else "off"},
            "fetch_url_tool": {"status": "on" if tool_fetch else "off"},
            "python_repl_tool": {"status": "on" if tool_python else "off"},
            "sql_tools": {"status": "on" if tool_sql else "off", "db_uri": _s(sql_db_uri)},
            "read_file_tool": {"status": "on" if tool_read else "off"},
            "tavily_search_tool": {"status": "on" if tool_tavily else "off", "tavily_api_key": _s(tavily_api_key)},
            "terminal_tool": {"status": "on" if tool_terminal else "off"},
            "rm_tool": {"status": "on" if tool_rm else "off"},
            "sed_all_tool": {"status": "on" if tool_sed_all else "off"},
            "sed_first_tool": {"status": "on" if tool_sed_first else "off"},
            "write_tool": {"status": "on" if tool_write else "off"},
            "grep_tool": {"status": "on" if tool_grep else "off"},
            "vision_tool": {
                "status": "on" if tool_vision else "off",
                "base_url": _s(vision_base_url),
                "api_key": _s(vision_api_key),
                "model": _s(vision_model),
            },
        }
        llm = {
            "provider": _s(llm_provider),
            "format": "openai",
            "info": {
                "model": _s(llm_model),
                "base_url": _s(llm_base_url),
                "api_key": _s(llm_api_key),
                "temperature": float(llm_temperature or 0.1),
                "is_reasoning_model": bool(llm_is_reasoning_model),
            },
        }
        embeddings = {
            "provider": _s(emb_provider),
            "format": "openai",
            "info": {"model": _s(emb_model), "base_url": _s(emb_base_url), "api_key": _s(emb_api_key)},
        }
        base_dir_val = _s(base_dir)
        platform_val = _s(platform)
        patch = {"rag_mode": rag_mode, "deepagent": deepagent, "llm": llm, "embeddings": embeddings, "tools": tools_map}
        if platform_val:
            patch["platform"] = platform_val
        if base_dir_val:
            patch["base_dir"] = base_dir_val
        c.put_config(patch)
        return "✅ **Config saved successfully.**"
    except Exception as e:
        return f"❌ **Error:** {e}"


def _sessions_list_ui() -> str:
    try:
        c = _client_or_raise()
        sessions = c.list_sessions()
        if not sessions:
            return "_No sessions._"
        lines = ["| ID | Title | Updated |", "|----|-------|---------|"]
        for s in sessions[:30]:
            sid = s.get("id", "")
            title = (s.get("title") or "")[:40]
            ts = s.get("updated_at", 0)
            try:
                ts_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(ts)))
            except Exception:
                ts_str = str(ts)
            lines.append(f"| {sid} | {title} | {ts_str} |")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ **Error:** {e}"


def _session_delete_ui(session_id: str) -> str:
    if not session_id.strip():
        return "⚠️ Enter a session ID."
    try:
        c = _client_or_raise()
        c.delete_session(session_id.strip())
        return f"✅ Deleted session `{session_id}`."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _session_clear_ui(session_id: str) -> str:
    if not session_id.strip():
        return "⚠️ Enter a session ID."
    try:
        c = _client_or_raise()
        c.clear_session(session_id.strip())
        return f"✅ Cleared session `{session_id}`."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _sessions_for_dropdown() -> tuple[list[tuple[str, str]], str]:
    try:
        c = _client_or_raise()
        sessions = c.list_sessions()
        choices = [("➕ New chat", "__new__")]
        for s in sessions:
            sid = s.get("id", "")
            if not sid:
                continue
            choices.append((sid, sid))
        return choices, "__new__"
    except Exception:
        return [("➕ New chat", "__new__")], "__new__"


def _load_session_ui(session_id: str) -> tuple[list[dict[str, str]], str]:
    if not session_id or session_id == "__new__":
        new_id = f"session_{time.strftime('%Y%m%d_%H%M%S')}"
        return [], new_id
    try:
        c = _client_or_raise()
        data = c.get_session(session_id)
        messages = data.get("messages", [])
        history = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role in ("user", "assistant"):
                history.append({"role": role, "content": content})
        return history, session_id
    except Exception:
        return [], session_id


def _current_model_ui() -> str:
    """Return a friendly description of the currently configured LLM model."""
    try:
        c = _client_or_raise()
        cfg = c.get_config()
        llm = cfg.get("llm") or {}
        info = llm.get("info") or {}
        model_name = str(info.get("model", "") or "").strip()
        base_url = str(info.get("base_url", "") or "").strip()
        is_reasoning = bool(info.get("is_reasoning_model", False))
        if not model_name:
            return "<div class='model-chip'>No LLM configured</div>"
        kind = "reasoning" if is_reasoning else "chat"
        provider = str(llm.get("provider", "") or "").strip() or "openai-compatible"
        base_label = re.sub(r"^https?://", "", base_url).rstrip("/") if base_url else "default endpoint"
        return (
            "<div class='model-chip'>"
            f"<strong>{html.escape(model_name)}</strong>"
            f"<span>{html.escape(kind)}</span>"
            f"<span>{html.escape(provider)}</span>"
            f"<span>{html.escape(base_label)}</span>"
            "</div>"
        )
    except Exception as e:
        return f"<div class='model-chip'>Could not load model: {html.escape(str(e))}</div>"


def _format_jsonish(value: Any) -> str:
    try:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)
    except Exception:
        return str(value)


def _truncate_text(value: Any, limit: int = 420) -> str:
    text = _format_jsonish(value).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _render_inline_event(event: dict[str, Any], reasoning_text: str = "", is_streaming: bool = False) -> str:
    et = event.get("type", "")
    if et == "reasoning_token":
        state = "Streaming" if is_streaming else "Captured"
        return (
            "<div class='fc-inline-card fc-inline-thinking'>"
            "<div class='fc-inline-meta'><span>Thinking</span>"
            f"<span>{html.escape(state)}</span></div>"
            f"<div class='fc-inline-body'>{html.escape(reasoning_text.strip())}</div>"
            "</div>"
        )
    if et == "tool_calling_summary":
        state = "Preparing" if is_streaming else "Prepared"
        return (
            "<div class='fc-inline-card fc-inline-tool pending'>"
            f"<div class='fc-inline-meta'><span>Tool</span><span>{html.escape(state)}</span></div>"
            "<div class='fc-inline-title'>Tool input</div>"
            f"<pre>{html.escape(_truncate_text(event.get('content', ''), 260))}</pre>"
            "</div>"
        )
    if et == "tool_execute":
        return (
            "<div class='fc-inline-card fc-inline-tool pending'>"
            "<div class='fc-inline-meta'><span>Tool</span><span>Running</span></div>"
            f"<div class='fc-inline-title'>{html.escape(str(event.get('tool', 'unknown')))}</div>"
            f"<pre>{html.escape(_truncate_text(event.get('input', ''), 260))}</pre>"
            "</div>"
        )
    if et == "tool_response":
        return (
            "<div class='fc-inline-card fc-inline-tool done'>"
            "<div class='fc-inline-meta'><span>Tool</span><span>Completed</span></div>"
            f"<div class='fc-inline-title'>{html.escape(str(event.get('tool', 'unknown')))}</div>"
            f"<pre>{html.escape(_truncate_text(event.get('output', ''), 360))}</pre>"
            "</div>"
        )
    if et == "retrieval":
        results = event.get("results") or []
        items = "".join(f"<li>{html.escape(_truncate_text(r.get('text', ''), 140))}</li>" for r in results[:3])
        return (
            "<div class='fc-inline-card fc-inline-rag'>"
            f"<div class='fc-inline-meta'><span>Memory</span><span>{len(results)} hits</span></div>"
            "<div class='fc-inline-title'>Retrieved context</div>"
            f"<ul>{items}</ul>"
            "</div>"
        )
    if et == "error":
        return (
            "<div class='fc-inline-card fc-inline-error'>"
            "<div class='fc-inline-meta'><span>Error</span><span>Blocked</span></div>"
            f"<div class='fc-inline-body'>{html.escape(_truncate_text(event.get('content', ''), 500))}</div>"
            "</div>"
        )
    return ""


def _loading_bubble_html() -> str:
    return (
        "<div class='fc-loading' aria-label='loading'>"
        "<span class='fc-loading-dot'></span>"
        "<span class='fc-loading-dot'></span>"
        "<span class='fc-loading-dot'></span>"
        "</div>"
    )


def _empty_status_html() -> str:
    return ""


def _render_transient_status(title: str, subtitle: str = "") -> str:
    subtitle_html = f"<div class='fc-status-text'>{html.escape(subtitle)}</div>" if subtitle else ""
    return (
        "<div class='fc-status'>"
        "<div class='fc-status-card'>"
        f"{_loading_bubble_html()}"
        "<div class='fc-status-copy'>"
        f"<div class='fc-status-title'>{html.escape(title)}</div>"
        f"{subtitle_html}"
        "</div>"
        "</div>"
        "</div>"
    )


def _chat_stream_ui(
    message: str,
    history: list[dict[str, str]],
    session_id: str,
) -> Generator[tuple[list[dict[str, str]], Any, str], None, None]:

    if not message.strip():
        yield history, message, _empty_status_html()
        return
    base_history: list[dict[str, str]] = history + [{"role": "user", "content": message}]
    display_history = list(base_history)
    display_history.append({"role": "assistant", "content": _loading_bubble_html()})
    loading_index: Optional[int] = len(display_history) - 1
    status_html = _render_transient_status(
        "Thinking",
        "Waiting for model response.",
    )
    yield display_history, "", status_html
    current_assistant = ""
    current_assistant_index: Optional[int] = None
    reasoning_text = ""
    reasoning_index: Optional[int] = None
    tool_calling_text = ""
    tool_calling_index: Optional[int] = None
    last_event_type: Optional[str] = None

    def _finalize_reasoning_card() -> None:
        nonlocal reasoning_text, reasoning_index
        if reasoning_index is not None and reasoning_text.strip():
            display_history[reasoning_index]["content"] = _render_inline_event(
                {"type": "reasoning_token"},
                reasoning_text=reasoning_text,
                is_streaming=False,
            )
        reasoning_text = ""
        reasoning_index = None

    def _finalize_tool_calling_card() -> None:
        nonlocal tool_calling_text, tool_calling_index
        if tool_calling_index is not None and tool_calling_text.strip():
            display_history[tool_calling_index]["content"] = _render_inline_event(
                {"type": "tool_calling_summary", "content": tool_calling_text},
                is_streaming=False,
            )
        tool_calling_text = ""
        tool_calling_index = None

    def _clear_loading_if_needed() -> None:
        nonlocal loading_index
        if loading_index is not None:
            display_history.pop(loading_index)
            loading_index = None

    def _finalize_assistant_text_block() -> None:
        nonlocal current_assistant, current_assistant_index
        current_assistant = ""
        current_assistant_index = None

    def _set_status(title: str, subtitle: str = "") -> None:
        nonlocal status_html
        status_html = _render_transient_status(
            title,
            subtitle,
        )

    try:
        c = _client_or_raise()
        payload = {"session_id": session_id or "default", "message": message, "is_reasoning_model": False}
        for event in c.chat_stream(payload):
            et = event.get("type", "")
            if et != "token" and last_event_type == "token":
                _finalize_assistant_text_block()
            if et == "token":
                if last_event_type == "reasoning_token":
                    _finalize_reasoning_card()
                if last_event_type == "tool_calling":
                    _finalize_tool_calling_card()
                _set_status("Responding", "Model is writing the reply.")
                current_assistant += event.get("content") or ""
                if current_assistant_index is None:
                    if loading_index is not None:
                        display_history[loading_index]["content"] = current_assistant
                        current_assistant_index = loading_index
                        loading_index = None
                    else:
                        display_history.append({"role": "assistant", "content": current_assistant})
                        current_assistant_index = len(display_history) - 1
                else:
                    display_history[current_assistant_index]["content"] = current_assistant
            elif et == "reasoning_token":
                if last_event_type != "reasoning_token":
                    if last_event_type == "tool_calling":
                        _finalize_tool_calling_card()
                    _finalize_reasoning_card()
                    _set_status("Thinking", "Model is reasoning.")
                    reasoning_text = event.get("content") or ""
                    card = _render_inline_event(
                        {"type": "reasoning_token"},
                        reasoning_text=reasoning_text,
                        is_streaming=True,
                    )
                    if loading_index is not None:
                        display_history[loading_index]["content"] = card
                        reasoning_index = loading_index
                        loading_index = None
                    else:
                        display_history.append({"role": "assistant", "content": card})
                        reasoning_index = len(display_history) - 1
                else:
                    reasoning_text += event.get("content") or ""
                    _set_status("Thinking", "Model is reasoning.")
                    if reasoning_index is not None:
                        display_history[reasoning_index]["content"] = _render_inline_event(
                            {"type": "reasoning_token"},
                            reasoning_text=reasoning_text,
                            is_streaming=True,
                        )
            elif et == "tool_calling":
                if last_event_type == "reasoning_token":
                    _finalize_reasoning_card()
                if last_event_type != "tool_calling":
                    _finalize_tool_calling_card()
                    tool_calling_text = event.get("content") or ""
                    _set_status("Preparing tool call", "Agent is composing tool input.")
                    card = _render_inline_event(
                        {"type": "tool_calling_summary", "content": tool_calling_text},
                        is_streaming=True,
                    )
                    if loading_index is not None:
                        display_history[loading_index]["content"] = card
                        tool_calling_index = loading_index
                        loading_index = None
                    else:
                        display_history.append({"role": "assistant", "content": card})
                        tool_calling_index = len(display_history) - 1
                else:
                    tool_calling_text += event.get("content") or ""
                    _set_status("Preparing tool call", "Agent is composing tool input.")
                    if tool_calling_index is not None:
                        display_history[tool_calling_index]["content"] = _render_inline_event(
                            {"type": "tool_calling_summary", "content": tool_calling_text},
                            is_streaming=True,
                        )
            elif et in {"tool_execute", "tool_response", "retrieval", "error"}:
                if last_event_type == "reasoning_token":
                    _finalize_reasoning_card()
                if last_event_type == "tool_calling":
                    _finalize_tool_calling_card()
                if et == "tool_execute":
                    _set_status("Running tool", "Tool execution in progress.")
                elif et == "tool_response":
                    _set_status("Processing tool result", "Agent is reading tool output.")
                elif et == "retrieval":
                    _set_status("Retrieving context", "Memory results received.")
                elif et == "error":
                    status_html = _empty_status_html()
                card = _render_inline_event(event)
                if loading_index is not None:
                    display_history.pop(loading_index)
                    loading_index = None
                display_history.append({"role": "assistant", "content": card})
            elif et == "tool_execute_done":
                if last_event_type == "reasoning_token":
                    _finalize_reasoning_card()
                if last_event_type == "tool_calling":
                    _finalize_tool_calling_card()
                _set_status("Continuing response", "Tool phase completed, model is continuing.")
            elif et == "all_done":
                if last_event_type == "reasoning_token":
                    _finalize_reasoning_card()
                if last_event_type == "tool_calling":
                    _finalize_tool_calling_card()
                status_html = _empty_status_html()
            if et:
                last_event_type = et
            yield display_history, gr.skip(), status_html
    except Exception as e:
        status_html = _empty_status_html()
        error_html = _render_inline_event({"type": "error", "content": f"Error during chat: {str(e)}"})
        if loading_index is not None:
            display_history[loading_index]["content"] = error_html
            loading_index = None
        elif current_assistant_index is not None:
            display_history.append({"role": "assistant", "content": error_html})
        else:
            display_history.append({"role": "assistant", "content": error_html})
        yield display_history, gr.skip(), status_html
        return

    _finalize_reasoning_card()
    _finalize_tool_calling_card()
    _clear_loading_if_needed()
    yield display_history, gr.skip(), _empty_status_html()


def _boot_md_stream_ui(
    history: list[dict[str, str]],
    session_id: str,
) -> Generator[tuple[list[dict[str, str]], Any, str], None, None]:
    """
    GUI button: simulate a user sending the boot message.
    """
    yield from _chat_stream_ui("Wake up, my friend!", history, session_id)


def _workplace_files_ui() -> dict:
    try:
        c = _client_or_raise()
        files = c.list_workplace_files()
        return gr.update(choices=files)
    except Exception:
        return gr.update(choices=[])


def _workplace_load_ui(filename: str) -> str:
    if not filename:
        return ""
    try:
        c = _client_or_raise()
        return c.read_workplace_file(filename)
    except Exception as e:
        return f"Error: {e}"


def _workplace_save_ui(filename: str, content: str) -> str:
    if not filename:
        return "⚠️ Select a file first."
    try:
        c = _client_or_raise()
        c.write_workplace_file(filename, content)
        return f"✅ Saved `{filename}`."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _memory_load_ui() -> str:
    try:
        c = _client_or_raise()
        return c.read_memory()
    except Exception as e:
        return f"Error: {e}"


def _memory_save_ui(content: str) -> str:
    try:
        c = _client_or_raise()
        c.write_memory(content)
        return "✅ Saved MEMORY.md."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _cleanup_workspace_ui() -> str:
    try:
        c = _client_or_raise()
        out = c.cleanup_workspace()
        removed = out.get("removed", [])
        if removed:
            return f"✅ **Workspace cleaned.** Removed: {', '.join(removed)}"
        return "✅ **Workspace already clean.** Nothing to remove."
    except Exception as e:
        return f"❌ **Error:** {e}"


def _build_ui(gateway_url: str) -> gr.Blocks:
    global _client
    _client = GuiGatewayClient(base_url=gateway_url)

    with gr.Blocks(title="microclaw") as demo:
        gr.Markdown("# microclaw · Gateway GUI")

        with gr.Tabs():
            with gr.TabItem("💬 Chat"):
                with gr.Column(elem_classes=["app-shell"]):
                    gr.HTML(
                        """
                        <section class="hero-bar">
                          <h1 class="hero-title">microclaw Console</h1>
                        </section>
                        """
                    )
                    model_md = gr.HTML("<div class='model-chip'>Loading model...</div>")
                    with gr.Row(elem_classes=["session-toolbar"]):
                        refresh_sessions_btn = gr.Button("Refresh", scale=0)
                        sessions_dd = gr.Dropdown(
                            label="Session",
                            choices=[("➕ New chat", "__new__")],
                            value="__new__",
                            allow_custom_value=False,
                        )
                    session_id_state = gr.State(value=f"session_{time.strftime('%Y%m%d_%H%M%S')}")
                    chatbot = gr.Chatbot(
                        label="",
                        elem_classes=["chat-container"],
                        height=620,
                        show_label=False,
                        render_markdown=True,
                        sanitize_html=False,
                        group_consecutive_messages=False,
                    )
                    busy_guard_html = gr.HTML(
                        """
                        <div id="fc-busy-guard" class="fc-busy-guard" aria-hidden="true">
                          <div class="fc-status-card">
                            <div class="fc-loading" aria-label="loading">
                              <span class="fc-loading-dot"></span>
                              <span class="fc-loading-dot"></span>
                              <span class="fc-loading-dot"></span>
                            </div>
                            <div class="fc-status-copy">
                              <div class="fc-status-title">Thinking</div>
                              <div class="fc-status-text">Waiting for model response.</div>
                            </div>
                          </div>
                        </div>
                        """
                    )
                    status_html = gr.HTML(_empty_status_html(), elem_id="fc-status-host")
                    msg = gr.Textbox(
                        label="Message",
                        placeholder="直接输入你的需求。Enter 发送，Ctrl+Enter 换行。",
                        lines=5,
                        show_label=False,
                        elem_id="chat-input",
                    )
                    with gr.Row(elem_classes=["bottom-actions"]):
                        boot_md_btn = gr.Button("Boot", variant="secondary", elem_id="boot-btn")
                        submit_btn = gr.Button("Send", variant="primary", elem_id="send-btn")
                        clear_btn = gr.Button("Clear")
                        clean_btn = gr.Button("Clean workspace", variant="secondary")
                    gr.Markdown(
                        "_Clean workspace removes all files except memory, sessions, skills, storage, and workplace._",
                        elem_classes=["clean-note"],
                    )
                    clean_status = gr.Markdown("")

                def _refresh_sessions():
                    choices, _ = _sessions_for_dropdown()
                    return gr.update(choices=choices, value="__new__"), f"session_{time.strftime('%Y%m%d_%H%M%S')}"

                def _on_session_select(sid):
                    hist, chat_id = _load_session_ui(sid)
                    return hist, chat_id

                refresh_sessions_btn.click(_refresh_sessions, outputs=[sessions_dd, session_id_state]).then(
                    lambda: [], outputs=[chatbot]
                )
                sessions_dd.change(
                    _on_session_select,
                    inputs=[sessions_dd],
                    outputs=[chatbot, session_id_state],
                )

                def _refresh_choices_after_send(sid):
                    choices, _ = _sessions_for_dropdown()
                    ids = [c[1] for c in choices]
                    if sid and sid in ids:
                        return gr.update(choices=choices, value=sid)
                    return gr.update(choices=choices)

                boot_md_btn.click(
                    _boot_md_stream_ui,
                    inputs=[chatbot, session_id_state],
                    outputs=[chatbot, msg, status_html],
                ).then(
                    _refresh_choices_after_send, inputs=[session_id_state], outputs=[sessions_dd]
                )

                submit_btn.click(
                    _chat_stream_ui,
                    inputs=[msg, chatbot, session_id_state],
                    outputs=[chatbot, msg, status_html],
                ).then(_refresh_choices_after_send, inputs=[session_id_state], outputs=[sessions_dd])
                msg.submit(
                    _chat_stream_ui,
                    inputs=[msg, chatbot, session_id_state],
                    outputs=[chatbot, msg, status_html],
                ).then(_refresh_choices_after_send, inputs=[session_id_state], outputs=[sessions_dd])
                clear_btn.click(lambda: ([], "", _empty_status_html()), outputs=[chatbot, msg, status_html])
                clean_btn.click(_cleanup_workspace_ui, outputs=[clean_status])
                demo.load(_refresh_sessions, outputs=[sessions_dd, session_id_state]).then(
                    _current_model_ui, outputs=[model_md]
                )

            with gr.TabItem("⚙️ Config"):
                config_status = gr.Markdown("_Click **Load config** to fetch current config, edit below, then **Save config**._")
                with gr.Row():
                    config_load_btn = gr.Button("Load config")
                    config_save_btn = gr.Button("Save config", variant="primary")

                with gr.Accordion("📌 Basic", open=True):
                    with gr.Row():
                        cfg_platform = gr.Textbox(label="Platform", placeholder="e.g. Ubuntu24.04", scale=1)
                        cfg_base_dir = gr.Textbox(label="Base directory (agent path)", placeholder="/path/to/agent", scale=2)
                    with gr.Row():
                        cfg_rag_mode = gr.Checkbox(label="RAG mode", value=False)
                        cfg_deepagent = gr.Checkbox(label="DeepAgent", value=False)

                with gr.Accordion("🤖 LLM (Chat model)", open=True):
                    with gr.Row():
                        with gr.Column(scale=1):
                            cfg_llm_provider = gr.Textbox(label="Provider", placeholder="deepseek / openai")
                            cfg_llm_model = gr.Textbox(label="Model", placeholder="deepseek-chat")
                            cfg_llm_temp = gr.Number(label="Temperature", value=0.1, minimum=0, maximum=2, step=0.1)
                            cfg_llm_thinking = gr.Checkbox(label="Reasoning model", value=False)
                        with gr.Column(scale=1):
                            cfg_llm_base_url = gr.Textbox(label="Base URL", placeholder="https://api.deepseek.com")
                            cfg_llm_api_key = gr.Textbox(label="API Key", type="password", placeholder="sk-...")

                with gr.Accordion("📐 Embeddings", open=False):
                    with gr.Row():
                        with gr.Column(scale=1):
                            cfg_emb_provider = gr.Textbox(label="Provider", placeholder="aliyun / openai")
                            cfg_emb_model = gr.Textbox(label="Model", placeholder="text-embedding-v3")
                        with gr.Column(scale=1):
                            cfg_emb_base_url = gr.Textbox(label="Base URL", placeholder="https://...")
                            cfg_emb_api_key = gr.Textbox(label="API Key", type="password", placeholder="sk-...")

                with gr.Accordion("🔧 Tools (on/off)", open=True):
                    gr.Markdown("勾选需要启用的工具；带额外参数的工具在下方「工具参数」中填写。")
                    with gr.Row():
                        cfg_tool_ask = gr.Checkbox(label="ask_user_question", value=True)
                        cfg_tool_fetch = gr.Checkbox(label="fetch_url", value=True)
                        cfg_tool_python = gr.Checkbox(label="python_repl", value=True)
                        cfg_tool_read = gr.Checkbox(label="read_file", value=True)
                        cfg_tool_terminal = gr.Checkbox(label="terminal", value=True)
                    with gr.Row():
                        cfg_tool_rm = gr.Checkbox(label="rm_tool", value=True)
                        cfg_tool_sed_all = gr.Checkbox(label="sed_all_tool", value=True)
                        cfg_tool_sed_first = gr.Checkbox(label="sed_first_tool", value=True)
                        cfg_tool_write = gr.Checkbox(label="write_tool", value=True)
                        cfg_tool_grep = gr.Checkbox(label="grep_tool", value=True)
                    with gr.Row():
                        cfg_tool_sql = gr.Checkbox(label="sql_tools", value=False)
                        cfg_tool_tavily = gr.Checkbox(label="tavily_search", value=False)
                        cfg_tool_vision = gr.Checkbox(label="vision_tool", value=False)

                with gr.Accordion("🔑 工具参数 (SQL / Tavily / Vision)", open=False):
                    cfg_sql_db_uri = gr.Textbox(
                        label="SQL: DB URI（启用 sql_tools 时填写）",
                        placeholder="postgresql+psycopg2://user:pass@host:5432/db",
                    )
                    cfg_tavily_key = gr.Textbox(
                        label="Tavily: API Key（启用 tavily_search 时填写）",
                        placeholder="tvly-...",
                        type="password",
                    )
                    gr.Markdown("**Vision**：须使用 OpenAI API 格式（base_url 指向兼容 `/chat/completions` 的端点）")
                    with gr.Row():
                        cfg_vision_base_url = gr.Textbox(
                            label="Vision Base URL",
                            placeholder="https://api.openai.com/v1",
                            scale=2,
                        )
                        cfg_vision_api_key = gr.Textbox(
                            label="Vision API Key",
                            type="password",
                            placeholder="sk-...",
                            scale=1,
                        )
                    cfg_vision_model = gr.Textbox(label="Vision Model", placeholder="", scale=1)

                with gr.Accordion("📖 Model support (参考)", open=False):
                    gr.Markdown(
                        "本项目仅支持 **OpenAI 兼容** 的 provider，`llm.format` 与 `embeddings.format` 保持 `\"openai\"`。\n\n"
                        "**当前支持的 `llm.info.model`：**\n"
                        "- `deepseek-chat`（is_reasoning_model = false）\n"
                        "- `deepseek-reasoner`（is_reasoning_model = true）\n"
                        "- `MiniMax-M2.5`（is_reasoning_model = true）\n"
                        "- `glm-5`（chat / reasoning 由 is_reasoning_model 控制）"
                    )

                config_load_btn.click(
                    _config_load_to_form,
                    outputs=[
                        cfg_platform,
                        cfg_base_dir,
                        cfg_rag_mode,
                        cfg_deepagent,
                        cfg_llm_provider,
                        cfg_llm_model,
                        cfg_llm_base_url,
                        cfg_llm_api_key,
                        cfg_llm_temp,
                        cfg_llm_thinking,
                        cfg_emb_provider,
                        cfg_emb_model,
                        cfg_emb_base_url,
                        cfg_emb_api_key,
                        cfg_tool_ask,
                        cfg_tool_fetch,
                        cfg_tool_python,
                        cfg_tool_sql,
                        cfg_tool_read,
                        cfg_tool_tavily,
                        cfg_tool_terminal,
                        cfg_tool_rm,
                        cfg_tool_sed_all,
                        cfg_tool_sed_first,
                        cfg_tool_write,
                        cfg_tool_grep,
                        cfg_tool_vision,
                        cfg_sql_db_uri,
                        cfg_tavily_key,
                        cfg_vision_base_url,
                        cfg_vision_api_key,
                        cfg_vision_model,
                    ],
                )
                config_save_btn.click(
                    _config_save_from_form,
                    inputs=[
                        cfg_platform,
                        cfg_base_dir,
                        cfg_rag_mode,
                        cfg_deepagent,
                        cfg_llm_provider,
                        cfg_llm_model,
                        cfg_llm_base_url,
                        cfg_llm_api_key,
                        cfg_llm_temp,
                        cfg_llm_thinking,
                        cfg_emb_provider,
                        cfg_emb_model,
                        cfg_emb_base_url,
                        cfg_emb_api_key,
                        cfg_tool_ask,
                        cfg_tool_fetch,
                        cfg_tool_python,
                        cfg_tool_sql,
                        cfg_tool_read,
                        cfg_tool_tavily,
                        cfg_tool_terminal,
                        cfg_tool_rm,
                        cfg_tool_sed_all,
                        cfg_tool_sed_first,
                        cfg_tool_write,
                        cfg_tool_grep,
                        cfg_tool_vision,
                        cfg_sql_db_uri,
                        cfg_tavily_key,
                        cfg_vision_base_url,
                        cfg_vision_api_key,
                        cfg_vision_model,
                    ],
                    outputs=[config_status],
                )

            with gr.TabItem("📋 Sessions"):
                sessions_refresh = gr.Button("Refresh list")
                sessions_md = gr.Markdown("_Click Refresh to load._")
                with gr.Row():
                    session_del_id = gr.Textbox(label="Session ID to delete", placeholder="default")
                    session_del_btn = gr.Button("Delete", variant="stop")
                with gr.Row():
                    session_clear_id = gr.Textbox(label="Session ID to clear", placeholder="default")
                    session_clear_btn = gr.Button("Clear messages")
                session_status = gr.Markdown("")
                sessions_refresh.click(_sessions_list_ui, outputs=[sessions_md])
                session_del_btn.click(_session_delete_ui, inputs=[session_del_id], outputs=[session_status]).then(
                    _sessions_list_ui, outputs=[sessions_md]
                )
                session_clear_btn.click(_session_clear_ui, inputs=[session_clear_id], outputs=[session_status]).then(
                    _sessions_list_ui, outputs=[sessions_md]
                )

            with gr.TabItem("❤️ Health"):
                health_btn = gr.Button("Check gateway")
                health_md = gr.Markdown("_Click to check._")
                health_btn.click(_health_ui, outputs=[health_md])

            with gr.TabItem("📁 Workplace files"):
                gr.Markdown("Edit `workplace/*.md` files.")
                with gr.Row():
                    wp_file_dd = gr.Dropdown(label="Select file", choices=[], allow_custom_value=False)
                    wp_refresh_btn = gr.Button("Refresh list")
                wp_editor = gr.Textbox(label="Content", lines=20)
                wp_save_btn = gr.Button("Save", variant="primary")
                wp_status = gr.Markdown("")

                wp_refresh_btn.click(_workplace_files_ui, outputs=[wp_file_dd])
                wp_file_dd.change(_workplace_load_ui, inputs=[wp_file_dd], outputs=[wp_editor])
                wp_save_btn.click(_workplace_save_ui, inputs=[wp_file_dd, wp_editor], outputs=[wp_status])
                demo.load(_workplace_files_ui, outputs=[wp_file_dd])

            with gr.TabItem("🧠 Memory (MEMORY.md)"):
                gr.Markdown("Edit `memory/MEMORY.md` — long-term memory.")
                memory_editor = gr.Textbox(label="MEMORY.md", lines=20)
                with gr.Row():
                    memory_load_btn = gr.Button("Load")
                    memory_save_btn = gr.Button("Save", variant="primary")
                memory_status = gr.Markdown("")
                memory_load_btn.click(_memory_load_ui, outputs=[memory_editor])
                memory_save_btn.click(_memory_save_ui, inputs=[memory_editor], outputs=[memory_status])
                demo.load(_memory_load_ui, outputs=[memory_editor])

        gr.Markdown(f"_Gateway: {gateway_url}_")

        demo.load(
            None,
            js="""
            () => {
                const inputRoot = document.querySelector('#chat-input textarea, #chat-input input');
                const sendBtn = document.querySelector('#send-btn');
                const bootBtn = document.querySelector('#boot-btn');
                const busyGuard = document.querySelector('#fc-busy-guard');
                const statusHost = document.querySelector('#fc-status-host');

                const startBusyGuard = () => {
                    if (!busyGuard) return;
                    busyGuard.setAttribute('aria-hidden', 'false');
                    busyGuard.classList.add('is-active');
                };

                const stopBusyGuard = () => {
                    if (!busyGuard) return;
                    busyGuard.classList.remove('is-active');
                    busyGuard.setAttribute('aria-hidden', 'true');
                };

                if (inputRoot && sendBtn && !inputRoot.dataset.fcBound) {
                    inputRoot.dataset.fcBound = '1';
                    inputRoot.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) {
                            e.preventDefault();
                            sendBtn.click();
                        } else if (e.key === 'Enter' && e.ctrlKey) {
                            e.preventDefault();
                            const el = e.target;
                            const start = el.selectionStart ?? el.value.length;
                            const end = el.selectionEnd ?? el.value.length;
                            const value = el.value ?? "";
                            el.value = value.slice(0, start) + "\\n" + value.slice(end);
                            const pos = start + 1;
                            el.selectionStart = el.selectionEnd = pos;
                        }
                    });
                }
                if (sendBtn && !sendBtn.dataset.fcBusyBound) {
                    sendBtn.dataset.fcBusyBound = '1';
                    sendBtn.addEventListener('click', () => startBusyGuard());
                }
                if (bootBtn && !bootBtn.dataset.fcBusyBound) {
                    bootBtn.dataset.fcBusyBound = '1';
                    bootBtn.addEventListener('click', () => startBusyGuard());
                }
                if (statusHost && !statusHost.dataset.fcObserved) {
                    statusHost.dataset.fcObserved = '1';
                    const observer = new MutationObserver(() => {
                        const hasStatus = !!statusHost.querySelector('.fc-status');
                        if (hasStatus) {
                            stopBusyGuard();
                        } else {
                            const hasAssistantLoading = !!document.querySelector('.chat-container .fc-loading');
                            if (!hasAssistantLoading) stopBusyGuard();
                        }
                    });
                    observer.observe(statusHost, { childList: true, subtree: true, characterData: true });
                }
            }
            """,
        )

    return demo


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="microclaw gui", description="microclaw Gradio GUI")
    parser.add_argument(
        "--gateway",
        default=os.environ.get("microclaw_GATEWAY", "http://127.0.0.1:8000"),
        help="Gateway base URL",
    )
    parser.add_argument("--port", "-p", type=int, default=7860, help="Gradio server port (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Create public share link")
    args = parser.parse_args(argv)

    demo = _build_ui(args.gateway)
    demo.launch(
        server_name="127.0.0.1",
        server_port=args.port,
        share=args.share,
        inbrowser=True,
        theme=gr.themes.Soft(),
        css=GUI_CSS,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
