import os
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_tools_config

TOOL_STATUS = get_tools_config()["write_tool"]["status"]

class WriteInput(BaseModel):
    filename: str = Field(description="Target file path")
    content: str = Field(description="Content to write")

class WriteTool(BaseTool):
    name: str = "write"
    description: str = "Write or overwrite a file. Like: echo content > file"
    args_schema: Type[BaseModel] = WriteInput

    def _run(self, filename: str, content: str) -> str:
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Success: written to {filename}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _arun(self, filename: str, content: str) -> str:
        return self._run(filename, content)

def create_write_tool() -> WriteTool | None:
    if TOOL_STATUS == "on":
        return WriteTool()
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

