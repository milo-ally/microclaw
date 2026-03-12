from __future__ import annotations

from pathlib import Path
from typing import Type

from microclaw.config import get_tools_config

from langchain_core.tools import BaseTool 
from pydantic import BaseModel, Field 

class ReadFileInput(BaseModel): 
    file_path: str = Field(
        description="Relative path of the file to read (relative to project root)"
    )

class SandBoxedReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = (
        "Read the contents of a file and return it as a string. "
        "Use this tool to read files from the project directory. "
        "Input should be a valid relative path to a file in the project directory."
    )
    args_schema: Type[BaseModel] = ReadFileInput
    root_dir: str = "" 

    def _run(self, file_path: str) -> str:
        try:
            root = Path(self.root_dir)
            normalized = file_path.replace("\\", "/").lstrip("./")
            full_path = (root / normalized).resolve()

            # Sandbox 
            if not str(full_path).startswith(str(root.resolve())):
                return "Access denied: path traversal attempted"

            if not full_path.exists():
                return f"File not found: {file_path}"
            
            if not full_path.is_file():
                return f"Path is not a file: {file_path}"
            
            content = full_path.read_text(encoding="utf-8") 
            if len(content) > 8000:
                content = content[:8000] + "\n...[truncated]"
            return content 
        except Exception as e:
            return f"Error reading file: {str(e)}" 
        
def create_sandboxed_read_file_tool(root_dir: str) -> SandBoxedReadFileTool | None:
    tools_cfg = get_tools_config() or {}
    status = str((tools_cfg.get("read_file_tool") or {}).get("status", "off")).lower()
    if status == "on":
        return SandBoxedReadFileTool(root_dir=root_dir)
    return None

# test
if __name__ == "__main__":
    tool = create_sandboxed_read_file_tool(root_dir="/home/milo/learnspace/AI_Application/Agent/ComputerUseAgent/agent")
    print(TOOL_STATUS)
    if tool:
        out = tool.invoke({"file_path": "memory/MEMORY.md"})
        assert isinstance(out, str) and len(out) > 0
        print(out[:800] + ("..." if len(out) > 800 else ""))
        print("read_file ok")
