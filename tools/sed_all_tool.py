from __future__ import annotations

from pathlib import Path
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from microclaw.config import get_tools_config


class SedAllInput(BaseModel):
    filepath: str = Field(
        description="File to modify. Relative paths are resolved against the workspace base_dir."
    )
    old_str: str = Field(description="String to replace globally")
    new_str: str = Field(description="Replacement string")

class SedAllTool(BaseTool):
    name: str = "sed_all"
    description: str = "Replace ALL occurrences of a string in file."
    args_schema: Type[BaseModel] = SedAllInput
    root_dir: str | None = None

    def _resolve_path(self, filepath: str) -> Path:
        p = Path(filepath)
        if p.is_absolute() or not self.root_dir:
            return p
        root = Path(self.root_dir).resolve()
        return (root / filepath).expanduser().resolve()

    def _run(self, filepath: str, old_str: str, new_str: str) -> str:
        try:
            target = self._resolve_path(filepath)
            content = target.read_text(encoding="utf-8")

            if old_str not in content:
                return "Error: old_str not found"

            new_content = content.replace(old_str, new_str)
            count = content.count(old_str)

            target.write_text(new_content, encoding="utf-8")

            return f"Success: replaced {count} occurrences in {target}"

        except Exception as e:
            return f"Error: {str(e)}"

    async def _arun(self, filepath: str, old_str: str, new_str: str):
        return self._run(filepath, old_str, new_str)


def create_sed_all_tool(root_dir: str | None = None):
    tools_cfg = get_tools_config() or {}
    status = str((tools_cfg.get("sed_all_tool") or {}).get("status", "off")).lower()
    if status == "on":
        return SedAllTool(root_dir=root_dir)
    return None


if __name__ == "__main__":
    """
    Self-test for SedAllTool using a copy of a real agent markdown file.

    - Copies `agent/workplace/IDENTITY.md` into a temporary directory.
    - Replaces all occurrences of 'microclaw' with 'MICROCLAW' in the copy.
    """
    import tempfile
    from pathlib import Path as _Path

    project_root = _Path(__file__).resolve().parent.parent
    source = project_root / "agent" / "workplace" / "IDENTITY.md"

    print(f"Project root: {project_root}")
    print(f"Source file for test: {source}  (exists={source.exists()})")
    print(f"sed_all_tool status: {TOOL_STATUS}")

    tool = create_sed_all_tool()
    if tool is None:
        print("SedAllTool is disabled in config.tools.sed_all_tool.status == 'off'.")
    else:
        if not source.exists():
            print("IDENTITY.md not found; cannot run real-file copy test.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = _Path(tmpdir) / "IDENTITY_copy.md"
                tmp_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                print("Before:\n", tmp_path.read_text(encoding="utf-8")[:400])
                out = tool._run(str(tmp_path), "microclaw", "MICROCLAW")
                print("Tool output:", out)
                print("After:\n", tmp_path.read_text(encoding="utf-8")[:400])

