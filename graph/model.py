"""Chat model that preserves reasoning_content from Doubao/Volcengine and other providers."""

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.language_models.chat_models import ChatResult
from langchain_openai import ChatOpenAI



class DeepSeekChatModel(ChatOpenAI):
    
    def __init__(
        self, 
        model: str, 
        api_key: str, 
        base_url: str = "https://api.deepseek.com", 
        temperature: float = 0.7,  # 增加默认值，和父类一致
        **kwargs  # 兼容父类的其他参数（如 max_tokens、timeout 等）
    ):
        # 调用父类初始化，传递所有参数
        super().__init__(
            model=model, 
            api_key=api_key, 
            base_url=base_url, 
            temperature=temperature,
            **kwargs  # 传递其他参数，保证兼容性
        )

class DeepSeekReasoningModel(ChatOpenAI):

    def __init__(
        self, 
        model: str, 
        api_key: str, 
        base_url: str = "https://api.deepseek.com", 
        temperature: float = 0.7,  # 增加默认值，和父类一致
        **kwargs  # 兼容父类的其他参数（如 max_tokens、timeout 等）
    ):
        # 调用父类初始化，传递所有参数
        super().__init__(
            model=model, 
            api_key=api_key, 
            base_url=base_url, 
            temperature=temperature,
            **kwargs  # 传递其他参数，保证兼容性
        )
    
    def _get_request_payload(
        self, 
        input_, 
        *, 
        stop=None, 
        **kwargs
    ):
        """Ensure assistant messages include reasoning_content for DeepSeek thinking+tool_calls API."""
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        messages = self._convert_input(input_).to_messages()
        for i, m in enumerate(messages):
            if i < len(payload.get("messages", [])) and isinstance(m, AIMessage):
                # DeepSeek requires reasoning_content on assistant messages in thinking mode
                payload["messages"][i]["reasoning_content"] = (
                    (m.additional_kwargs or {}).get("reasoning_content") or ""
                )
        return payload

    def _create_chat_result(
        self,
        response,
        generation_info: dict | None = None,
    ) -> ChatResult:
        """处理非流式响应，提取 reasoning_content"""
        result = super()._create_chat_result(response, generation_info)
        if not result.generations:
            return result
        if hasattr(response, "choices") and response.choices:
            msg = response.choices[0].message
            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                result.generations[0].message.additional_kwargs["reasoning_content"] = (
                    msg.reasoning_content
                )
        return result

    def _convert_chunk_to_generation_chunk(
        self, chunk, default_chunk_class, base_generation_info
    ):
        """流式时从 delta 提取 reasoning_content"""
        gen = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        if gen is None:
            return None
        choices = chunk.get("choices", []) or chunk.get("chunk", {}).get("choices", [])
        if choices:
            delta = choices[0].get("delta") or {}
            if delta.get("reasoning_content"):
                msg = gen.message
                if isinstance(msg, AIMessageChunk):
                    msg.additional_kwargs["reasoning_content"] = delta["reasoning_content"]
        return gen

class DoubaoChatModel(ChatOpenAI):
    def __init__(
        self, 
        model: str, 
        api_key: str, 
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3", 
        temperature: float = 0.7,  # 增加默认值，和父类一致
        **kwargs  # 兼容父类的其他参数（如 max_tokens、timeout 等）
    ):
        # 调用父类初始化，传递所有参数
        super().__init__(
            model=model, 
            api_key=api_key, 
            base_url=base_url, 
            temperature=temperature,
            **kwargs  # 传递其他参数，保证兼容性
        )

class DoubaoReasoningModel(DeepSeekReasoningModel):
    def __init__(
        self, 
        model: str, 
        api_key: str, 
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3", 
        temperature: float = 0.7,  # 增加默认值，和父类一致
        **kwargs  # 兼容父类的其他参数（如 max_tokens、timeout 等）
    ):
        # 调用父类初始化，传递所有参数
        super().__init__(
            model=model, 
            api_key=api_key, 
            base_url=base_url, 
            temperature=temperature,
            **kwargs  # 传递其他参数，保证兼容性
        )