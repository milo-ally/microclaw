"""Tools module - provides get_all_tools for agent use."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool

from microclaw.config import get_base_dir
from tools.registry import iter_enabled_tools


def get_all_tools(base_dir: str | Path | None = None) -> list[BaseTool]:
    """
    Build tool list for the agent.

    Compatibility guarantee:
    - Keeps the same public function name and return type.
    - Tool enable/disable still comes from config.json -> tools.*.status.
    """
    root = str(base_dir or get_base_dir())
    return list(iter_enabled_tools(root_dir=root))


__all__ = ["get_all_tools", "iter_enabled_tools"]
