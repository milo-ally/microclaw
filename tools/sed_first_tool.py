from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_tools_config

TOOL_STATUS = get_tools_config()["sed_first_tool"]["status"]

class SedFirstInput(BaseModel):
    filepath: str = Field(description="File to modify")
    old_str: str = Field(description="String to replace")
    new_str: str = Field(description="Replacement string")

class SedFirstTool(BaseTool):
    name: str = "sed_first"
    description: str = "Replace the FIRST occurrence of a string in file."
    args_schema: Type[BaseModel] = SedFirstInput

    def _run(self, filepath: str, old_str: str, new_str: str) -> str:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            content = "".join(lines)

            if old_str not in content:
                return "Error: old_str not found"

            replace_line = None
            new_lines = []
            replaced = False

            for i, line in enumerate(lines):
                if not replaced and old_str in line:
                    new_lines.append(line.replace(old_str, new_str, 1))
                    replace_line = i + 1
                    replaced = True
                else:
                    new_lines.append(line)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write("".join(new_lines))

            return (
                f"Success: replaced in {filepath}\n"
                f"Line approx: {replace_line}\n"
                f"First occurrence replaced."
            )

        except Exception as e:
            return f"Error: {str(e)}"

    async def _arun(self, filepath: str, old_str: str, new_str: str) -> str:
        return self._run(filepath, old_str, new_str)

def create_sed_first_tool():
    if TOOL_STATUS == "on":
        return SedFirstTool()
    return None


if __name__ == "__main__":
    """
    Self-test for SedFirstTool using a copy of a real agent markdown file.

    - Copies `agent/workplace/USER.md` into a temporary directory.
    - Replaces the first occurrence of 'master' with 'MASTER' in the copy.
    """
    import tempfile
    from pathlib import Path as _Path

    project_root = _Path(__file__).resolve().parent.parent
    source = project_root / "agent" / "workplace" / "USER.md"

    print(f"Project root: {project_root}")
    print(f"Source file for test: {source}  (exists={source.exists()})")
    print(f"sed_first_tool status: {TOOL_STATUS}")

    tool = create_sed_first_tool()
    if tool is None:
        print("SedFirstTool is disabled in config.tools.sed_first_tool.status == 'off'.")
    else:
        if not source.exists():
            print("USER.md not found; cannot run real-file copy test.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = _Path(tmpdir) / "USER_copy.md"
                tmp_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                print("Before:\n", tmp_path.read_text(encoding="utf-8")[:400])
                out = tool._run(str(tmp_path), "master", "MASTER")
                print("Tool output:\n", out)
                print("After:\n", tmp_path.read_text(encoding="utf-8")[:400])

