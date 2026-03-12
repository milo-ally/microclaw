"""
Tool registry + enable/disable policy for microclaw.

Inspired by OpenClaw's subsystem boundaries:
- Tools are explicit capabilities.
- Loading is policy-driven (config switches + required params).
- Tool modules should avoid import-time side effects (read config lazily).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from langchain_core.tools import BaseTool

from microclaw.config import get_tools_config


ToolFactory = Callable[[str], Optional[BaseTool]]
ToolListFactory = Callable[[str], Optional[list[BaseTool]]]


@dataclass(frozen=True)
class ToolSpec:
    config_key: str
    factory: ToolFactory | ToolListFactory
    kind: str = "single"  # "single" | "list"


def _is_on(cfg: dict[str, Any], key: str) -> bool:
    entry = cfg.get(key) or {}
    return str(entry.get("status", "off")).lower() == "on"


def iter_enabled_tools(*, root_dir: str | Path) -> Iterable[BaseTool]:
    """
    Yield tool instances based on tools config.
    - Keeps current UX: missing optional tool config -> tool is simply absent.
    """
    root = str(Path(root_dir).resolve())
    tools_cfg = get_tools_config() or {}

    # Factories are imported lazily so modules do not run config reads at import-time.
    def _fetch_url(root_dir: str) -> BaseTool | None:
        from .fetch_url_tool import create_fetch_url_tool

        return create_fetch_url_tool()

    def _read_file(root_dir: str) -> BaseTool | None:
        from .read_file_tool import create_sandboxed_read_file_tool

        return create_sandboxed_read_file_tool(root_dir=root_dir)

    def _terminal(root_dir: str) -> BaseTool | None:
        from .terminal_tool import create_terminal_tool

        return create_terminal_tool(root_dir=root_dir)

    def _python_repl(root_dir: str) -> BaseTool | None:
        from .python_repl_tool import create_python_repl_tool

        return create_python_repl_tool(root_dir=root_dir)

    def _ask_user(_: str) -> BaseTool | None:
        from .ask_user_question_tool import create_ask_user_question_tool

        return create_ask_user_question_tool()

    def _tavily(_: str) -> BaseTool | None:
        from .tavily_search_tool import create_tavily_search_tool

        return create_tavily_search_tool()

    def _rm(root_dir: str) -> BaseTool | None:
        from .rm_tool import create_rm_tool

        return create_rm_tool(root_dir=root_dir)

    def _sed_all(root_dir: str) -> BaseTool | None:
        from .sed_all_tool import create_sed_all_tool

        return create_sed_all_tool(root_dir=root_dir)

    def _sed_first(root_dir: str) -> BaseTool | None:
        from .sed_first_tool import create_sed_first_tool

        return create_sed_first_tool(root_dir=root_dir)

    def _write(root_dir: str) -> BaseTool | None:
        from .write_tool import create_write_tool

        return create_write_tool(root_dir=root_dir)

    def _grep(root_dir: str) -> BaseTool | None:
        from .grep_tool import create_grep_tool

        return create_grep_tool(root_dir=root_dir)

    def _sql_tools(_: str) -> list[BaseTool] | None:
        from .sql_tools import create_sql_tools

        return create_sql_tools()

    specs: list[ToolSpec] = [
        ToolSpec("fetch_url_tool", _fetch_url),
        ToolSpec("read_file_tool", _read_file),
        ToolSpec("terminal_tool", _terminal),
        ToolSpec("python_repl_tool", _python_repl),
        ToolSpec("ask_user_question_tool", _ask_user),
        ToolSpec("tavily_search_tool", _tavily),
        ToolSpec("rm_tool", _rm),
        ToolSpec("sed_all_tool", _sed_all),
        ToolSpec("sed_first_tool", _sed_first),
        ToolSpec("write_tool", _write),
        ToolSpec("grep_tool", _grep),
        ToolSpec("sql_tools", _sql_tools, kind="list"),
    ]

    for spec in specs:
        if not _is_on(tools_cfg, spec.config_key):
            continue
        try:
            built = spec.factory(root)
        except Exception:
            # Keep UX stable: tool failures should not crash the whole agent boot.
            continue
        if not built:
            continue
        if spec.kind == "list":
            for t in (built or []):
                if t is not None:
                    yield t
        else:
            yield built  # type: ignore[misc]

