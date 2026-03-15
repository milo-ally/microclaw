"""
microclaw GUI - Gradio-based web interface.
"""

from __future__ import annotations

import argparse
import json
import re
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Generator, Optional

import gradio as gr

from microclaw.client import GatewayClient, parse_sse_events


class GuiGatewayClient(GatewayClient):
    def chat_stream(self, payload: dict[str, Any]) -> Generator[tuple[str, str], None, None]:
        """Yield (role, chunk) for streaming display with beautified tool info."""
        for event_name, data in parse_sse_events(self.chat_stream_lines(payload)):
            if event_name == "error":
                try:
                    obj = json.loads(data)
                    yield ("assistant", f"<div class='error-box'>❌ Error: {obj.get('content', data)}</div>")
                except Exception:
                    yield ("assistant", f"<div class='error-box'>❌ Error: {data}</div>")
                continue
            if event_name == "end":
                continue
            try:
                obj = json.loads(data)
            except Exception:
                continue
            et = obj.get("type")
            content = obj.get("content") or ""
            if et == "token":
                yield ("assistant", content)
            elif et == "reasoning_token":
                yield ("assistant", f"<span class='reasoning-text'>{content}</span>")
            elif et == "tool_calling":
                continue
            elif et == "toolcall_message":
                continue
            elif et == "tool_execute":
                tname = obj.get("tool", "")
                tin = obj.get("input", "")
                try:
                    tin_formatted = json.dumps(tin, ensure_ascii=False, indent=2) if isinstance(tin, dict) else str(tin)
                except Exception:
                    tin_formatted = str(tin)
                tool_card = f"""
<div class='tool-card tool-executing'>
  <div class='tool-header'>
    <span class='tool-icon'>🔧</span>
    <span class='tool-name'>{tname}</span>
    <span class='tool-status'>Executing</span>
  </div>
  <div class='tool-content'>
    <div class='tool-label'>Input:</div>
    <pre class='tool-pre'>{tin_formatted[:200]}...</pre>
  </div>
</div>
"""
                yield ("assistant", tool_card)
            elif et == "tool_response":
                tname = obj.get("tool", "")
                tout = obj.get("output", "")
                try:
                    tout_formatted = (
                        json.dumps(tout, ensure_ascii=False, indent=2) if isinstance(tout, dict) else str(tout)
                    )
                except Exception:
                    tout_formatted = str(tout)
                tool_card = f"""
<div class='tool-card tool-success'>
  <div class='tool-header'>
    <span class='tool-icon'>✅</span>
    <span class='tool-name'>{tname}</span>
    <span class='tool-status'>Completed</span>
  </div>
  <div class='tool-content'>
    <div class='tool-label'>Output:</div>
    <pre class='tool-pre'>{tout_formatted[:300]}...</pre>
  </div>
</div>
"""
                yield ("assistant", tool_card)
            elif et == "retrieval":
                results = obj.get("results") or []
                if results:
                    rag_items = []
                    for i, r in enumerate(results[:3], 1):
                        text = (r.get("text") or "")[:150]
                        rag_items.append(f"<div class='rag-item'>{i}. {text}...</div>")
                    rag_card = f"""
<div class='tool-card tool-rag'>
  <div class='tool-header'>
    <span class='tool-icon'>📚</span>
    <span class='tool-name'>RAG Retrieval</span>
    <span class='tool-status'>Found {len(results)} results</span>
  </div>
  <div class='tool-content rag-content'>
    {''.join(rag_items)}
  </div>
</div>
"""
                    yield ("assistant", rag_card)
            elif et == "all_done":
                continue


_client: Optional[GuiGatewayClient] = None


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
            return "_No LLM configured. Go to **Config** tab to set one._"
        kind = "reasoning" if is_reasoning else "chat"
        return f"**Current LLM:** `{model_name}`  ·  _{kind}_  · "
    except Exception as e:
        return f"_Could not load current model: {e}_"


def _chat_stream_ui(message: str, history: list[dict[str, str]], session_id: str) -> Generator[list[dict[str, str]], None, None]:
    def _is_tool_like_chunk(text: str) -> bool:
        t = (text or "").lstrip()
        return t.startswith("<div class='tool-card'>") or t.startswith("<div class='error-box'>")

    if not message.strip():
        yield history
        return
    base_history: list[dict[str, str]] = history + [{"role": "user", "content": message}]
    display_history = list(base_history)
    current_assistant = ""
    current_assistant_index: Optional[int] = None

    try:
        c = _client_or_raise()
        payload = {"session_id": session_id or "default", "message": message, "is_reasoning_model": False}
        for _role, chunk in c.chat_stream(payload):
            if _is_tool_like_chunk(chunk):
                if current_assistant:
                    if current_assistant_index is None:
                        display_history.append({"role": "assistant", "content": current_assistant})
                        current_assistant_index = len(display_history) - 1
                    else:
                        display_history[current_assistant_index]["content"] = current_assistant
                    current_assistant = ""
                    current_assistant_index = None

                display_history.append({"role": "assistant", "content": chunk})
                yield display_history
            else:
                current_assistant += chunk
                if current_assistant_index is None:
                    display_history.append({"role": "assistant", "content": current_assistant})
                    current_assistant_index = len(display_history) - 1
                else:
                    display_history[current_assistant_index]["content"] = current_assistant
                yield display_history
    except Exception as e:
        error_html = f"<div class='error-box'>❌ **Error during chat:** {str(e)}</div>"
        if current_assistant_index is not None:
            display_history[current_assistant_index]["content"] = error_html
        else:
            display_history.append({"role": "assistant", "content": error_html})
        yield display_history


def _boot_md_stream_ui(history: list[dict[str, str]], session_id: str) -> Generator[list[dict[str, str]], None, None]:
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

    custom_css = """
    .gradio-container {
        max-width: 1200px;
        margin: 0 auto;
    }
    .chat-container {
        max-height: 70vh;
    }
    .session-sidebar {
        min-width: 220px;
    }
    .chat-main {
        min-width: 0;
    }
    .bottom-actions {
        display: flex;
        gap: 0.75rem;
        justify-content: flex-start;
    }
    .bottom-actions > button {
        flex: 0 0 auto;
    }
    .clean-note {
        font-size: 0.85rem;
        color: #666;
    }

    /* 工具卡片样式 */
    .tool-card {
        margin: 8px 0;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        background-color: #f9fafb;
        font-size: 0.95em;
    }
    .tool-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        padding-bottom: 6px;
        border-bottom: 1px solid #e5e7eb;
    }
    .tool-icon {
        font-size: 1.1em;
    }
    .tool-name {
        font-weight: 600;
        flex: 1;
    }
    .tool-status {
        font-size: 0.85em;
        color: #6b7280;
    }
    .tool-content {
        padding-left: 4px;
    }
    .tool-label {
        font-size: 0.85em;
        color: #4b5563;
        margin-bottom: 4px;
        font-weight: 500;
    }
    .tool-pre {
        background-color: #f3f4f6;
        padding: 8px;
        border-radius: 4px;
        font-size: 0.9em;
        overflow-x: auto;
        max-height: 200px;
        white-space: pre-wrap;
    }
    /* 不同类型工具卡片的配色 */
    .tool-executing {
        border-left: 4px solid #3b82f6;
    }
    .tool-success {
        border-left: 4px solid #10b981;
    }
    .tool-rag {
        border-left: 4px solid #8b5cf6;
    }
    /* RAG 内容样式 */
    .rag-content {
        padding-left: 8px;
    }
    .rag-item {
        margin: 4px 0;
        padding-left: 4px;
        border-left: 2px solid #ddd;
    }
    /* 思考过程文本样式 */
    .reasoning-text {
        color: #6b7280;
        font-style: italic;
    }
    /* 错误提示框样式 */
    .error-box {
        margin: 8px 0;
        padding: 12px;
        border-radius: 8px;
        background-color: #fef2f2;
        color: #dc2626;
        border: 1px solid #fecaca;
    }
    """

    with gr.Blocks(title="microclaw", css=custom_css) as demo:
        gr.Markdown("# microclaw · Gateway GUI")

        with gr.Tabs():
            with gr.TabItem("💬 Chat"):
                with gr.Column(elem_classes=["chat-main"]):
                    model_md = gr.Markdown("_Current LLM: loading..._")
                    with gr.Row():
                        refresh_sessions_btn = gr.Button("🔄", scale=0)
                        sessions_dd = gr.Dropdown(
                            label="Select session",
                            choices=[("➕ New chat", "__new__")],
                            value="__new__",
                            allow_custom_value=False,
                        )
                    session_id_state = gr.State(value=f"session_{time.strftime('%Y%m%d_%H%M%S')}")
                    chatbot = gr.Chatbot(label="", elem_classes=["chat-container"], height=520, show_label=False)
                    msg = gr.Textbox(
                        label="Message",
                        placeholder="Type your message... (supports markdown)",
                        lines=4,
                        show_label=False,
                        elem_id="chat-input",
                    )
                    with gr.Row(elem_classes=["bottom-actions"]):
                        boot_md_btn = gr.Button("boot", variant="secondary")
                        submit_btn = gr.Button("Send", variant="primary", elem_id="send-btn")
                        clear_btn = gr.Button("Clear")
                        clean_btn = gr.Button("🧹 Clean workspace", variant="secondary")
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
                sessions_dd.change(_on_session_select, inputs=[sessions_dd], outputs=[chatbot, session_id_state])

                def _refresh_choices_after_send(sid):
                    choices, _ = _sessions_for_dropdown()
                    ids = [c[1] for c in choices]
                    if sid and sid in ids:
                        return gr.update(choices=choices, value=sid)
                    return gr.update(choices=choices)

                boot_md_btn.click(_boot_md_stream_ui, inputs=[chatbot, session_id_state], outputs=[chatbot]).then(
                    _refresh_choices_after_send, inputs=[session_id_state], outputs=[sessions_dd]
                )

                submit_btn.click(_chat_stream_ui, inputs=[msg, chatbot, session_id_state], outputs=[chatbot]).then(
                    lambda: "", outputs=[msg]
                ).then(_refresh_choices_after_send, inputs=[session_id_state], outputs=[sessions_dd])
                msg.submit(_chat_stream_ui, inputs=[msg, chatbot, session_id_state], outputs=[chatbot]).then(
                    lambda: "", outputs=[msg]
                ).then(_refresh_choices_after_send, inputs=[session_id_state], outputs=[sessions_dd])
                clear_btn.click(lambda: [], outputs=[chatbot])
                clean_btn.click(_cleanup_workspace_ui, outputs=[clean_status])
                demo.load(_refresh_sessions, outputs=[sessions_dd, session_id_state]).then(
                    _current_model_ui, outputs=[model_md]
                )

            with gr.TabItem("⚙️ Config"):
                config_status = gr.Markdown("_Click Load to fetch config._")
                gr.Markdown(
                    "**Important:** This project only supports **OpenAI-compatible** providers. "
                    'Keep `llm.format` and `embeddings.format` as `"openai"`.\n\n'
                    "**Supported `llm.info.model` values in this version:**\n\n"
                    "- `deepseek-chat` — set `llm.info.is_reasoning_model = false`\n"
                    "- `deepseek-reasoner` — set `llm.info.is_reasoning_model = true`\n"
                    "- `MiniMax-M2.5` — set `llm.info.is_reasoning_model = true` (MiniMax reasoning_split enabled)\n"
                    "- `glm-5` — chat when `is_reasoning_model = false`, reasoning when `true`\n\n"
                    "Other model names are currently treated as unsupported by the gateway."
                )
                with gr.Row():
                    config_load_btn = gr.Button("Load config")
                    config_save_btn = gr.Button("Save config", variant="primary")

                with gr.Accordion("Basic", open=True):
                    cfg_platform = gr.Textbox(label="Platform", placeholder="e.g. Ubuntu24.04")
                    cfg_base_dir = gr.Textbox(label="Base directory (agent path)", placeholder="/path/to/agent")
                    with gr.Row():
                        cfg_rag_mode = gr.Checkbox(label="RAG mode", value=False)
                        cfg_deepagent = gr.Checkbox(label="DeepAgent", value=False)

                with gr.Accordion("LLM (Chat model)", open=True):
                    cfg_llm_provider = gr.Textbox(label="Provider", placeholder="deepseek / openai")
                    cfg_llm_model = gr.Textbox(label="Model", placeholder="deepseek-chat")
                    cfg_llm_base_url = gr.Textbox(label="Base URL", placeholder="https://api.deepseek.com")
                    cfg_llm_api_key = gr.Textbox(label="API Key", type="password", placeholder="sk-...")
                    with gr.Row():
                        cfg_llm_temp = gr.Number(label="Temperature", value=0.1, minimum=0, maximum=2, step=0.1)
                        cfg_llm_thinking = gr.Checkbox(label="Reasoning model", value=False)

                with gr.Accordion("Embeddings", open=True):
                    cfg_emb_provider = gr.Textbox(label="Provider", placeholder="aliyun / openai")
                    cfg_emb_model = gr.Textbox(label="Model", placeholder="text-embedding-v3")
                    cfg_emb_base_url = gr.Textbox(label="Base URL", placeholder="https://...")
                    cfg_emb_api_key = gr.Textbox(label="API Key", type="password", placeholder="sk-...")

                with gr.Accordion("Tools (switch on/off)", open=True):
                    gr.Markdown("Toggle each tool. Some tools have extra parameters below.")
                    with gr.Row():
                        cfg_tool_ask = gr.Checkbox(label="ask_user_question", value=True)
                        cfg_tool_fetch = gr.Checkbox(label="fetch_url", value=True)
                        cfg_tool_python = gr.Checkbox(label="python_repl", value=True)
                        cfg_tool_sql = gr.Checkbox(label="sql_tools", value=False)
                        cfg_tool_read = gr.Checkbox(label="read_file", value=True)
                        cfg_tool_tavily = gr.Checkbox(label="tavily_search", value=False)
                        cfg_tool_terminal = gr.Checkbox(label="terminal", value=True)
                    with gr.Row():
                        cfg_tool_rm = gr.Checkbox(label="rm_tool", value=True)
                        cfg_tool_sed_all = gr.Checkbox(label="sed_all_tool", value=True)
                        cfg_tool_sed_first = gr.Checkbox(label="sed_first_tool", value=True)
                        cfg_tool_write = gr.Checkbox(label="write_tool", value=True)
                        cfg_tool_grep = gr.Checkbox(label="grep_tool", value=True)
                    with gr.Row():
                        cfg_sql_db_uri = gr.Textbox(
                            label="SQL: DB URI (when sql_tools enabled)",
                            placeholder="postgresql+psycopg2://user:pass@host:5432/db",
                            visible=True,
                        )
                        cfg_tavily_key = gr.Textbox(
                            label="Tavily: API Key (when tavily_search enabled)",
                            placeholder="tvly-...",
                            type="password",
                        )
                        gr.Markdown("**vision_tool**: 须使用 OpenAI API 格式（base_url 指向兼容 `/chat/completions` 的端点）")
                        cfg_tool_vision = gr.Checkbox(label="vision_tool", value=False)
                        cfg_vision_base_url = gr.Textbox(
                            label="Vision: Base URL (OpenAI API 格式，如 https://api.openai.com/v1)",
                            placeholder="https://api.openai.com/v1",
                        )
                        cfg_vision_api_key = gr.Textbox(
                            label="Vision: API Key",
                            type="password",
                            placeholder="sk-...",
                        )
                        cfg_vision_model = gr.Textbox(
                            label="Vision: Model",
                            placeholder="",
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
                if (!inputRoot || !sendBtn) return;
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
            """,
        )

    return demo


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="microclaw gui", description="microclaw Gradio GUI")
    parser.add_argument(
        "--gateway",
        default=os.environ.get("MICROCLAW_GATEWAY", "http://127.0.0.1:8000"),
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

