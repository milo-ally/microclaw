from __future__ import annotations

from pathlib import Path
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from microclaw.config import get_tools_config


class WriteInput(BaseModel):
    filename: str = Field(description="Target file path (relative to workspace root if not absolute)")
    content: str = Field(description="Content to write")


class WriteTool(BaseTool):
    name: str = "write"
    description: str = (
        "Write or overwrite a file. Like: echo content > file. "
        "Relative paths are resolved against the workspace base_dir."
    )
    args_schema: Type[BaseModel] = WriteInput
    root_dir: str | None = None

    def _resolve_path(self, filename: str) -> Path:
        # Absolute path: respect as-is (still bounded by OS permissions)
        p = Path(filename)
        if p.is_absolute() or not self.root_dir:
            return p
        root = Path(self.root_dir).resolve()
        # Normalize potential "../" etc. relative segments
        full = (root / filename).expanduser().resolve()
        return full

    def _run(self, filename: str, content: str) -> str:
        try:
            target = self._resolve_path(filename)
            # Ensure parent directory exists
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Success: written to {target}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _arun(self, filename: str, content: str) -> str:
        return self._run(filename, content)


def create_write_tool(root_dir: str | None = None) -> WriteTool | None:
    tools_cfg = get_tools_config() or {}
    status = str((tools_cfg.get("write_tool") or {}).get("status", "off")).lower()
    if status == "on":
        return WriteTool(root_dir=root_dir)
    return None


if __name__ == "__main__":
    """
    Self-test for WriteTool using an `agent/`-like path in a temp dir.

    - Writes a markdown file in a temporary directory.
    - Reads it back to confirm content.
    """
    import tempfile
    from pathlib import Path as _Path

    project_root = _Path(__file__).resolve().parent.parent
    print(f"Project root: {project_root}")
    print(f"write_tool status: {TOOL_STATUS}")

    tool = create_write_tool()
    if tool is None:
        print("WriteTool is disabled in config.tools.write_tool.status == 'off'.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            # simulate something like agent/workplace/NOTES.md
            agent_like_dir = _Path(tmpdir) / "agent" / "workplace"
            agent_like_dir.mkdir(parents=True, exist_ok=True)
            p = agent_like_dir / "NOTES.md"
            out = tool._run(str(p), "hello from WriteTool\nthis is a test line")
            print("Tool output:", out)
            print("File exists:", p.exists())
            if p.exists():
                print("Content:\n", p.read_text(encoding="utf-8"))

