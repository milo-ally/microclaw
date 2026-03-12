from __future__ import annotations

from pathlib import Path
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from microclaw.config import get_tools_config


class RmInput(BaseModel):
    filepath: str = Field(
        description="Path to the file to delete. Relative paths are resolved against the workspace base_dir."
    )


class RmTool(BaseTool):
    name: str = "rm"
    description: str = "Delete a single file. Does not delete directories."
    args_schema: Type[BaseModel] = RmInput
    root_dir: str | None = None

    def _resolve_path(self, filepath: str) -> Path:
        p = Path(filepath)
        if p.is_absolute() or not self.root_dir:
            return p
        root = Path(self.root_dir).resolve()
        return (root / filepath).expanduser().resolve()

    def _run(self, filepath: str) -> str:
        try:
            target = self._resolve_path(filepath)
            if not target.is_file():
                return f"Error: file not found - {target}"
            target.unlink()
            return f"Success: deleted file - {target}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _arun(self, filepath: str) -> str:
        return self._run(filepath)


def create_rm_tool(root_dir: str | None = None) -> RmTool | None:
    tools_cfg = get_tools_config() or {}
    status = str((tools_cfg.get("rm_tool") or {}).get("status", "off")).lower()
    if status == "on":
        return RmTool(root_dir=root_dir)
    return None


if __name__ == "__main__":
    """
    Self-test for RmTool using a copy of a real agent file.

    - Copies `agent/memory/MEMORY.md` into a temporary directory.
    - Deletes the copy (not the original).
    """
    import tempfile
    from pathlib import Path as _Path

    project_root = _Path(__file__).resolve().parent.parent
    source = project_root / "agent" / "memory" / "MEMORY.md"

    print(f"Project root: {project_root}")
    print(f"Source file for test: {source}  (exists={source.exists()})")
    print(f"rm_tool status: {TOOL_STATUS}")

    tool = create_rm_tool()
    if tool is None:
        print("RmTool is disabled in config.tools.rm_tool.status == 'off'.")
    else:
        if not source.exists():
            print("MEMORY.md not found; cannot run real-file copy test.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = _Path(tmpdir) / "MEMORY_copy.md"
                tmp_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"Created copy: {tmp_path} exists={tmp_path.exists()}")
                out = tool._run(str(tmp_path))
                print("Tool output:", out)
                print(f"After rm: exists={tmp_path.exists()}")

