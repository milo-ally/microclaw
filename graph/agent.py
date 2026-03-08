from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages import AIMessageChunk, ToolMessageChunk, ToolCallChunk
from deepagents import create_deep_agent

from typing import AsyncGenerator, Any, Optional
from pathlib import Path

from tools import get_all_tools
from mcps import get_mcp_tools

from config import get_llm_config, get_base_dir, get_rag_mode
from config import get_deepagent

from .model import ChatOpenAIWithReasoning
from .session_manager import session_manager
from .prompt_builder import build_system_prompt
from .memory_indexer import get_memory_indexer

import asyncio


class AgentManager:
    def __init__(self) -> None: 
        self._base_dir: Path | None = None 
        self._tools: list = [] 
        self._model = None 

    def initialize(self, base_dir: Path) -> None:
        """Initialize model and tools, called once at startup"""
        llm_info = get_llm_config().get("info") or {}
        self._enable_thinking = llm_info.get("enable_thinking")
        self._base_dir = base_dir
        # mcp_tools = get_mcp_tools() # TODO
        self._tools = get_all_tools(base_dir) # TODO if len(mcp_tools) == 0 else mcp_tools + get_all_tools(base_dir)
        self._model = ChatOpenAIWithReasoning(
            model=llm_info.get("model"),
            base_url=llm_info.get("base_url"),
            api_key=llm_info.get("api_key"),
            temperature=llm_info.get("temperature"),
            extra_body = {"enable_thinking": self._enable_thinking} 
        )
        session_manager.initialize(base_dir)
        # print(f"Agent initialized by using model: {llm_info.get('model')}, loaded tools number: {len(self._tools)}")


    def _build_agent(self): 
        """Build agent with model and tools"""
        assert self._model is not None 
        assert self._base_dir is not None 

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
            content = msg.get("content", "")
            
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
            
            # Assistant message
            elif role == "assistant":
                messages.append(AIMessage([
                    {"type": "text", "text": content}
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

        input_content = ""
        full_response = ""
        reasoning_content = ""
        tool_call_content = ""
        tool_response_content = ""
        tools_just_finished = False

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

            # 用于token计算
            elif mode == "updates":
                if isinstance(data, dict):
                    for node_name, node_data in data.items():

                        # 输出完整的tool_response内容
                        if node_name == "tools" and "messages" in node_data:

                            for tool_msg in node_data["messages"]:
                                if hasattr(tool_msg, "name"):
                                    output_msg = str(tool_msg.content)
                                    tool_response_content += output_msg
                                    yield {
                                        "type": "tool_response",
                                        "tool": tool_msg.name,
                                        "output": output_msg[:2000],
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
                                            "type": "tool_execute",
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