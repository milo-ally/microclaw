# TODO
from pathlib import Path 

import sys
import asyncio
import concurrent.futures  # 新增：补全缺失的导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_mcps_config
MCP_CONFIG = get_mcps_config()

# 保留：禁用MCP会话关闭时的终止请求（消除400提示）
import mcp
mcp.ClientSession.terminate = lambda self: asyncio.sleep(0)

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# 函数名完全不变！
def get_mcp_tools() -> list:
    """
    获取MCP工具（同步接口，适配Python3.12运行中的事件循环 + 本地调试）
    """
    # 原有异步逻辑（完全保留）
    async def _async_get_mcp_tools():
        client = MultiServerMCPClient(MCP_CONFIG)
        try:
            async with client.session("chrome-mcp-server") as session:            
                tools = await load_mcp_tools(
                    session,
                    server_name="chrome-mcp-server",
                    tool_name_prefix=client.tool_name_prefix,
                    tool_interceptors=client.tool_interceptors,
                    callbacks=client.callbacks
                )
            print(f"✅ 成功获取 {len(tools)} 个MCP工具")
            return tools
        except Exception as e:
            error_msg = str(e)
            print(f"获取Tools失败: {error_msg}")
            return []
    
    # 核心修复：补全导入 + 调整异常捕获逻辑
    try:
        loop = asyncio.get_running_loop()
        # 适配运行中的事件循环（Python3.12兼容）
        future = asyncio.run_coroutine_threadsafe(_async_get_mcp_tools(), loop)
        return future.result(timeout=30)
    except RuntimeError:  # 无运行中循环（本地调试）
        return asyncio.run(_async_get_mcp_tools())
    except concurrent.futures.TimeoutError:  # 单独捕获超时异常
        print(f"⚠️ MCP工具获取超时（30秒），仅使用本地工具")
        return []
    except Exception as e:  # 兜底捕获所有异常
        print(f"⚠️ MCP工具获取异常: {e}")
        return []

if __name__ == "__main__":
    print(get_mcp_tools())