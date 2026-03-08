from pathlib import Path 

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_tools_config

TOOL_CONFIG = get_tools_config() 
TOOL_STATUS = TOOL_CONFIG["tavily_search_tool"]["status"]
TAVILY_API_KEY = TOOL_CONFIG["tavily_search_tool"]["tavily_api_key"]

from langchain_tavily.tavily_search import TavilySearch

def create_tavily_search_tool() -> TavilySearch | None:
    if not TAVILY_API_KEY or not TAVILY_API_KEY.startswith("tvly-"):
        return None
    if TOOL_STATUS == "on":
        tool = TavilySearch(
            tavily_api_key=TAVILY_API_KEY
        )
        return tool
    return None

# test
if __name__ == "__main__":
    print(f"工具状态: {TOOL_STATUS}")
    tool = create_tavily_search_tool()
    if tool:
        try:
            out = tool.invoke({
                "query": "What happened at the last wimbledon"
            })
            assert isinstance(out, str) and len(out) > 0
            print(out[:800] + ("..." if len(out) > 800 else ""))
            print("Tavily 搜索工具调用成功！")
        except Exception as e:
            print(f"调用失败：{e}")
    else:
        print("工具未启用或 API Key 配置错误")
