"""Post /api/chat - SSE streaming chat with agent"""
# TODO


"""
NOTE: This script can't be run now!!!
NOTE: This script can't be run now!!!
NOTE: This script can't be run now!!!
"""



import json
import os
import traceback
from typing import AsyncGenerator, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage as HM
import sys
sys.path.append("..")
from config import get_llm_config, get_base_dir

from graph.agent import agent_manager
from graph.session_manager import session_manager

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    stream: bool = True

async def _generate_title(session_id: str) -> str | None:
    try:
        messages = session_manager.load_session(session_id)
        first_user = ""
        first_assistant = ""
        for msg in messages:
            if msg["role"] == "user" and not first_user:
                first_user = msg["content"][:200]
            elif msg["role"] == "assistant" and not first_assistant:
                first_assistant = msg["content"][:200]
            if first_user and first_assistant:
                break
        
        if not first_user:
            return None
        
        llm_info = get_llm_config().get("info") or {}
        
        llm = ChatOpenAI(
            model=llm_info.get("model"),
            base_url=llm_info.get("base_url"),
            api_key=llm_info.get("api_key"),
            temperature=0
        )

        prompt = (
            f"请根据以下对话内容, 生成一个简洁的, 不超过15个字的标题, 只输出标题文本, 不要加引号或标点。 \n\n"
            f"用户: {first_user} \n"
            f"助手: {first_assistant}"
        )

        result = await llm.ainvoke([HM(content=prompt)])
        title = result.content.strip().strip('"\'""''')[:15]
        session_manager.update_title(session_id, title)
        return title
    except Exception as e:
        traceback.print_exc()
        return None

async def event_generator(message: str, session_id: str) -> AsyncGenerator[dict[str, Any], None]:
    try:

        # 加载会话历史
        history = session_manager.load_session_for_agent(session_id)
        if not isinstance(history, list):
            history = []
        
        # 保存用户消息到会话
        session_manager.save_message(
            session_id, 
            role="user", 
            content=message
        )
        
        # 流式获取agent响应
        async for event in agent_manager.astream(message, history):

            # 将事件序列化为JSON并yield，符合SSE格式
            yield {
                "data": json.dumps(event, ensure_ascii=False),
                "event": "message"
            }
        
        # 获取最终响应并保存到会话
        final_response = ""
        async for event in agent_manager.astream(message, history):
            if event["type"] == "all_done":
                final_response = event["content"]
                break
        
        if final_response:
            session_manager.save_message(session_id, role="assistant", content=final_response)
            await _generate_title(session_id) # Generate session title
        
        # 发送结束信号
        yield {
            "data": json.dumps({"type": "stream_ended", "content": "对话结束"}),
            "event": "end"
        }
    except Exception as e:
        traceback.print_exc()

        # 发送错误事件
        yield {
            "data": json.dumps({"type": "error", "content": str(e)}),
            "event": "error"
        }

@router.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        # 验证agent是否初始化
        if not agent_manager._model:
            base_dir = get_base_dir() if "get_base_dir" in dir(sys.modules["config"]) else None
            if not base_dir:
                raise HTTPException(
                    status_code=500, 
                    detail="Agent not initialized, missing base directory configuration"
                )
            agent_manager.initialize(base_dir)
        
        # 非流式响应处理
        if not request.stream:
            response = await agent_manager.ainvoke(request.message, request.session_id)
            # 生成会话标题
            await _generate_title(request.session_id)
            return {
                "session_id": request.session_id,
                "response": response,
                "title": "新对话"
            }
        
        # 流式响应处理（SSE）
        return EventSourceResponse(
            event_generator(request.message, request.session_id),
            media_type="text/event-stream"
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"聊天接口异常: {str(e)}"
        )

