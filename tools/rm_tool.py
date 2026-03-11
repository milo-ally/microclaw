import os
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_tools_config

TOOL_STATUS = get_tools_config()["rm_tool"]["status"]

class RmInput(BaseModel):
    filepath: str = Field(description="Path to the file to delete")

class RmTool(BaseTool):
    name: str = "rm"
    description: str = "Delete a single file. Does not delete directories."
    args_schema: Type[BaseModel] = RmInput

    def _run(self, filepath: str) -> str:
        try:
            if not os.path.isfile(filepath):
                return f"Error: file not found - {filepath}"

            os.remove(filepath)
            return f"Success: deleted file - {filepath}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _arun(self, filepath: str) -> str:
        return self._run(filepath)

def create_rm_tool() -> RmTool | None:
    if TOOL_STATUS == "on":
        return RmTool()
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

