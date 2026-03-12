from __future__ import annotations

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from deepagents import create_deep_agent

from typing import AsyncGenerator, Any, Optional
from pathlib import Path

from tools import get_all_tools


from microclaw.config import get_llm_config, get_base_dir, get_rag_mode
from microclaw.config import get_deepagent

from .model import (
    DeepSeekChatModel, 
    DeepSeekReasoningModel, 
    DoubaoChatModel, 
    DoubaoReasoningModel
)
from .session_manager import session_manager
from .prompt_builder import build_system_prompt
from .memory_indexer import get_memory_indexer
import asyncio


def get_model(*, model_name: str, is_reasoning_model: bool) -> ChatOpenAI:

    if model_name == "deepseek-chat":
        llm_info = (get_llm_config().get("info") or {})
        return DeepSeekChatModel(
            model=model_name,
            api_key=llm_info.get("api_key"),
            base_url=llm_info.get("base_url", "https://api.deepseek.com"),
            temperature=llm_info.get("temperature"),
        )

    elif model_name == "deepseek-reasoner":
        llm_info = (get_llm_config().get("info") or {})
        return DeepSeekReasoningModel(
            model=model_name,
            api_key=llm_info.get("api_key"),
            base_url=llm_info.get("base_url", "https://api.deepseek.com"),
            temperature=llm_info.get("temperature"),
        )

    elif model_name == "doubao-seed-2-0-pro-260215":
        llm_info = (get_llm_config().get("info") or {})
        # Keep config surface stable: same model string, choose class by is_reasoning_model flag.
        if is_reasoning_model:
            
            return DoubaoReasoningModel(
                model=model_name,
                api_key=llm_info.get("api_key"),
                base_url=llm_info.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"),
                temperature=llm_info.get("temperature"),
            )

        return DoubaoChatModel(
            model=model_name,
            api_key=llm_info.get("api_key"),
            base_url=llm_info.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"),
            temperature=llm_info.get("temperature"),
        )

    raise RuntimeError(
        f"Unsupported llm.info.model '{model_name}'. "
        "Expected one of: 'deepseek-chat', 'deepseek-reasoner', "
        "'doubao-seed-2-0-pro-260215' (chat/reasoning variants). "
        "Please check config.llm.info.model."
    )


class AgentManager:
    def __init__(self) -> None: 
        self._base_dir: Path | None = None 
        self._tools: list = [] 
        self._model = None 

    def initialize(self, base_dir: Path) -> None:
        """Initialize model and tools, called once at startup"""
        llm_info = get_llm_config().get("info") or {}
        self._is_reasoning_model = bool(llm_info.get("is_reasoning_model"))
        self._base_dir = base_dir
        self._model_name = llm_info.get("model")
        self._tools = get_all_tools(base_dir) # TODO if len(mcp_tools) == 0 else mcp_tools + get_all_tools(base_dir)
        self._model = get_model(model_name=self._model_name, is_reasoning_model=self._is_reasoning_model)
        session_manager.initialize(base_dir)
        # print(f"Agent initialized by using model: {llm_info.get('model')}, loaded tools number: {len(self._tools)}")

    async def summarize_messages(self, messages: list[dict[str, Any]]) -> str:
        """
        Use LLM to summarize a list of conversation messages into a concise history summary.
        Used when compressing history (first 50% of messages when count > 50).
        """
        if not messages or not self._model:
            return ""
        parts: list[str] = []
        for m in messages:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                parts.append(f"[{role}]: {content.strip()}")
        if not parts:
            return ""
        text = "\n\n".join(parts)
        prompt = f"""Summarize the following conversation history concisely in the same language. Preserve key facts, decisions, and context. Keep it under 2000 characters.

Conversation:
{text}

Summary:"""
        try:
            resp = await self._model.ainvoke([HumanMessage(content=prompt)])
            return (resp.content or "").strip()
        except Exception:
            return ""

    def _build_agent(self): 
        """Build agent with model and tools"""
        if self._model is None:
            raise RuntimeError(
                "Agent model is not initialized. "
                "This usually means config.llm.info is missing required fields or "
                "AgentManager.initialize() was not called."
            )
        if self._base_dir is None:
            raise RuntimeError(
                "Agent base_dir is not initialized. "
                "Ensure config.base_dir is set and AgentManager.initialize() has been run."
            )

        rag_mode = get_rag_mode()
        system_prompt = build_system_prompt(self._base_dir, rag_mode=rag_mode)
        deepagent = get_deepagent()

        if not deepagent:
            agent = create_agent(
                model=self._model,
                tools=self._tools,
                system_prompt=system_prompt
            )
            # print(f"Agent类型: {type(agent)}")
            return agent 
        
        agent = create_deep_agent(
            model=self._model, 
            tools=self._tools,
            system_prompt=system_prompt
        )
        # print(f"Agent类型: {type(agent)}")
        return agent 


    def _build_messages(
        self, user_message: str, 
        image_url: Optional[str], 
        history: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:

        """Build messages with optional RAG context appended to history."""
        messages = []
        hist = history if isinstance(history, list) else []
        for msg in hist:
            role = msg.get("role", "")
            content = msg.get("content", "") or ""
            
            if not content:
                continue

            # System message (e.g. [History Summary] from compression)
            if role == "system":
                messages.append(SystemMessage(content=content))
                continue
            
            # User message
            if role == "user":
                if image_url: 
                    messages.append(HumanMessage([
                        {"type": "text", "text": content}, 
                        {"type": "image_url", "image_url": {"url": image_url}} 
                    ]))
                else:
                    messages.append(HumanMessage([
                        {"type": "text", "text": content}
                    ]))
                continue
            
            # Assistant message
            if role == "assistant":
                messages.append(AIMessage([
                    {"type": "text", "text": content}
                ]))
                continue

            # Tool-related messages and other custom roles
            if role in {"tool_call", "tool_response"}:
                messages.append(AIMessage([
                    {"type": "text", "text": f"[{role}] {content}"}
                ]))
                continue

            # 其它自定义角色：同样当作 assistant 消息，并标注原 role
            messages.append(AIMessage([
                {"type": "text", "text": f"[{role}] {content}"}
            ]))
            
        messages.append(HumanMessage([
            {"type": "text", "text": user_message}, 
            {"type": "image_url", "image_url": {"url": image_url}} 
        ])) if image_url else messages.append(HumanMessage([
            {"type": "text", "text": user_message}
        ]))
        return messages
    async def astream(
        self, 
        message: str, 
        image_url: Optional[str], 
        history: list[dict[str, Any]]
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream agent response with token-level and node-level events.

        Yields events:
          streaming: 
            {"type": "reasoning_token", "content": "..."} 
            {"type": "token", "content": "..."}
            {"type" "tool_calling", "content": "...}
          updates: 
            {"type": "tool_execute", "tool": "...", "input": "..."}
            {"type": "tool_response", "tool": "...", "output": "..."}
            {"type": "tool_execute_done", "} # indicates that the agent has started a new response after tool calls
            {
                "type": "all_done", 
                "input_content": "...",
                "content": "...", 
                "reasoning_content": "...", 
                "tool_call_content": "...", 
                "tool_response_content": "...", 
                "retrieval_content": "..."
            }
            {"type": "debug", "content": "..."}
        """

        # Memory RAG retrieval (BM25 + Dense Vector Retrieval)
        rag_mode = get_rag_mode()
        rag_context = "" 
        if rag_mode and self._base_dir:
            memory_indexer = get_memory_indexer(self._base_dir)
            results = memory_indexer.retrieve(message) # 将用户输入的message作为query，从memory中检索相关内容
            if results:
                yield {
                    "type": "retrieval", 
                    "query": message, 
                    "results": results, 
                }
                snippets = "\n\n".join(
                    f"[chunk {i+1}] (score: {r.get('score', 0)})\n{r.get('text', '')}"
                    for i, r in enumerate(results)
                )
                rag_context = f"Here is the relevant context from memory:\n{snippets}"

        # Knowledge base RAG retrieval
        # TODO: 
        # AgenticRAG: 在tools中加一个云知识库检索工具 
        # IncontextQA RAG: 需要在这里通过SummaryIndex实现 (前端会将文件进行结构化, 发送到这里)

        # Adding RAG context to history
        agent = self._build_agent()
        augmented_history = list(history)
        if rag_context:
            augmented_history.append({
                "role": "retrieval", 
                "content": rag_context, 
            })
        messages = self._build_messages(message, history=augmented_history, image_url=image_url)

        # 用于token计算和输出
        input_content = ""
        full_response = ""
        reasoning_content = ""
        tool_call_content = ""
        tool_response_content = ""
        tools_just_finished = False

        # 用于输出
        total_ai_msg = ""
        total_function_call_msg = ""
        last_ai_len = 0
        last_func_len = 0
        

        for msg in messages: 
            if isinstance(msg, (HumanMessage, AIMessage)):
                if isinstance(msg.content, list) and len(msg.content) > 0:
                    input_content += msg.content[0].get("text", "")  

        async for event in agent.astream(
            {"messages": messages},
            stream_mode=["messages", "updates"],
        ):
            # event is a tuple of (stream_mode, data) when using multiple modes
            if isinstance(event, tuple):
                mode, data = event
            else:
                mode = "messages"
                data = event


            # 用于流式输出
            if mode == "messages":
                msg, metadata = data

                # 思考事件
                if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
                    kw = msg.additional_kwargs
                    reasoning_token = None

                    if "reasoning_content" in kw:
                        reasoning_token = kw.get("reasoning_content") or ""
                    
                    if (
                        reasoning_token 
                        and isinstance(reasoning_token, str) 
                        and reasoning_token.strip()
                    ):
                        reasoning_content += reasoning_token
                        yield {
                            "type": "reasoning_token", 
                            "content": reasoning_token
                        }
                
                # 回复事件
                if hasattr(msg, "content") and msg.content:
                    if msg.type == "AIMessageChunk" or msg.type == "ai":
                        if msg.content and not getattr(msg, "tool_calls", None):
                            if tools_just_finished:
                                yield {
                                    "type": "tool_execute_done"
                                }
                                tools_just_finished = False
                            full_response += msg.content
                            yield {
                                "type": "token", 
                                "content": msg.content
                            }


                # tool_calling事件
                if hasattr(msg, "tool_call_chunks") and msg.tool_call_chunks: # tool_call_chunks: list[dict[str, Any]]
                    tool_chunks = msg.tool_call_chunks
                    chunk = tool_chunks[0]
                    args = chunk.get("args", "")
                    yield {
                        "type": "tool_calling",
                        "content": args,
                    }

            # 用于token计算和消息列表构建
            elif mode == "updates":
                if isinstance(data, dict):
                    for node_name, node_data in data.items():
                        
                        # 输出完整的正常ai消息内容
                        if node_name == "model" and "messages" in node_data: 
                            for ai_msg in node_data["messages"]: 
                                if hasattr(ai_msg, "tool_calls") and not ai_msg.tool_calls:
                                    msg_chunk = str(ai_msg.content)
                                    total_ai_msg += msg_chunk
                                    new_ai_content = total_ai_msg[last_ai_len:] # 只yield新增的内容
                                    if new_ai_content:
                                        yield {
                                            "type": "ai_message", 
                                            "content": new_ai_content  # 只传新内容，不是累加的全部
                                        }
                                        last_ai_len = len(total_ai_msg)  # 更新长度
                        
                        # 输出完整的ai发起工具调用的信息
                        if node_name == "model" and "messages" in node_data: 
                            for function_call_msg in node_data["messages"]: 
                                if hasattr(function_call_msg, "tool_calls") and function_call_msg.tool_calls:
                                    msg_chunk = str(function_call_msg.content)
                                    total_function_call_msg += msg_chunk
                                    new_func_content = total_function_call_msg[last_func_len:] # 只yield新增的内容
                                    if new_func_content:
                                        yield {
                                            "type": "toolcall_message", 
                                            "content": new_func_content  # 只传新内容，不是累加的全部
                                        }
                                        last_func_len = len(total_function_call_msg)  # 更新长度


                        # 输出完整的tool_response内容
                        if node_name == "tools" and "messages" in node_data:
                            for tool_msg in node_data["messages"]:
                                if hasattr(tool_msg, "name"):
                                    output_msg = str(tool_msg.content)
                                    tool_response_content += output_msg
                                    yield {
                                        "type": "tool_response",
                                        "tool": tool_msg.name,
                                        "output": output_msg[:1000],
                                    }
                            tools_just_finished = True
                        
                        # 输出完整的tool_execute内容
                        elif node_name in ("model", "agent") and "messages" in node_data:
                            for agent_msg in node_data["messages"]:
                                if hasattr(agent_msg, "tool_calls") and agent_msg.tool_calls:
                                    for tc in agent_msg.tool_calls:
                                        input_msg = str(tc.get("args", ""))
                                        tool_call_content += input_msg
                                        yield {
                                            "type": "tool_call",
                                            "tool": tc["name"],
                                            "input": input_msg[:1000],
                                        }

        yield {
            "type": "all_done", 
            "input_content": input_content,
            "content": full_response, 
            "reasoning_content": reasoning_content, 
            "tool_call_content": tool_call_content,
            "tool_response_content": tool_response_content,
            "retrieval_content": rag_context,
        }


agent_manager = AgentManager()