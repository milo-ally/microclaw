from __future__ import annotations

from microclaw.config import get_tools_config

import html2text
from typing import Type 
import requests 
from langchain_core.tools import BaseTool 
from pydantic import BaseModel, Field

class FetchURLInput(BaseModel):
    url: str = Field(description="The URL to fetch content from") 

class FetchURLTool(BaseTool): 
    name: str = "fetch_url"
    description: str = (
        "Fetch content from a web page and return it as a cleaned Markdown text. "
        "Use this tool to retrieve information from the internet. "
        "Input should be a valid URL (starting with http:// or https://)."
    )
    args_schema: Type[BaseModel] = FetchURLInput

    def _run(self, url: str) -> str:
        try: 
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; TestAgent/0.1)"
            }
            resp = requests.get(url, headers=headers, timeout=15) 
            resp.raise_for_status() 
            content_type = resp.headers.get("content-type", "").lower() 

            # If JSON, return directly
            if "application/json" in content_type:
                text = resp.text 
                if len(text) > 5000:
                    text = text[:5000] + "\n...[truncated]"
                return text 
            
            # If HTML, convert to Markdown
            converter = html2text.HTML2Text() 
            converter.ignore_links = False # keep links
            converter.ignore_images = True # ignore images 
            converter.body_width = 0 # no line wrapping
            markdown = converter.handle(resp.text)

            if len(markdown) > 5000:
                markdown = markdown[:5000] + "\n...[truncated]"
            return markdown 
        except requests.Timeout:
            return "Request timed out (15 seconds limit)" 
        except requests.RequestException as e:
            return f"Fetch error: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    async def _arun(self, url: str) -> str:
        return self._run(url)

def create_fetch_url_tool() -> FetchURLTool | None:
    tools_cfg = get_tools_config() or {}
    status = str((tools_cfg.get("fetch_url_tool") or {}).get("status", "off")).lower()
    if status == "on":
        return FetchURLTool()
    return None

# test
if __name__ == "__main__":
    print(TOOL_STATUS)
    tool = create_fetch_url_tool()
    if tool:
        out = tool.invoke({"url": "https://bilibili.com"})
        assert isinstance(out, str) and len(out) > 0
        print(out[:800] + ("..." if len(out) > 800 else ""))
        print("fetch_url ok")