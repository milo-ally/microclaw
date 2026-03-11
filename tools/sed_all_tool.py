from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_tools_config

TOOL_STATUS = get_tools_config()["sed_all_tool"]["status"]

class SedAllInput(BaseModel):
    filepath: str = Field(description="File to modify")
    old_str: str = Field(description="String to replace globally")
    new_str: str = Field(description="Replacement string")

class SedAllTool(BaseTool):
    name: str = "sed_all"
    description: str = "Replace ALL occurrences of a string in file."
    args_schema: Type[BaseModel] = SedAllInput

    def _run(self, filepath: str, old_str: str, new_str: str) -> str:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if old_str not in content:
                return "Error: old_str not found"

            new_content = content.replace(old_str, new_str)
            count = content.count(old_str)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f"Success: replaced {count} occurrences in {filepath}"

        except Exception as e:
            return f"Error: {str(e)}"

    async def _arun(self, filepath: str, old_str: str, new_str: str):
        return self._run(filepath, old_str, new_str)

def create_sed_all_tool():
    if TOOL_STATUS == "on":
        return SedAllTool()
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

