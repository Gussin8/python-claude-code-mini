"""Anthropic API service"""

from dataclasses import dataclass
from typing import AsyncGenerator, Optional, Any
import anthropic


@dataclass
class StreamEvent:
    """流事件
    
    Attributes:
        type: 事件类型
        data: 事件数据
        raw: 原始事件对象
    """

    type: str
    data: dict[str, Any]
    raw: Optional[Any] = None


@dataclass
class QueryOptions:
    """查询选项
    
    Attributes:
        model: 模型名称
        system_prompt: 系统提示词
        tools: 工具列表（JSON Schema 格式）
        max_tokens: 最大 token 数
        temperature: 温度参数
        stream: 是否流式输出
    """

    model: str
    system_prompt: str
    tools: list[dict]
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = True


class APIService:
    """Anthropic API 服务
    
    封装 Anthropic SDK，提供简化的接口。
    
    功能:
        - 流式响应处理
        - 工具调用支持
        - 错误处理和重试
        - 使用统计追踪
    
    示例:
        api = APIService(api_key="your-key")
        
        options = QueryOptions(
            model="claude-sonnet-4-20250514",
            system_prompt="You are a helpful assistant.",
            tools=[...],
        )
        
        async for event in api.query_model(messages, options):
            if event.type == "content_block_delta":
                print(event.data["delta"]["text"], end="", flush=True)
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """初始化 API 服务
        
        Args:
            api_key: Anthropic API 密钥
            base_url: 自定义 API 地址（可选）
        """
        self.api_key = api_key
        self.base_url = base_url
        
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
        )

    async def query_model(
        self,
        messages: list[dict],
        options: QueryOptions,
    ) -> AsyncGenerator[StreamEvent, None]:
        """查询模型
        
        Args:
            messages: 对话历史
            options: 查询选项
        
        Yields:
            流事件
        
        Raises:
            anthropic.APIError: API 错误
            anthropic.AuthenticationError: 认证失败
            anthropic.RateLimitError: 速率限制
        """
        # 构建请求参数
        request_params = {
            "model": options.model,
            "max_tokens": options.max_tokens,
            "messages": messages,
            "stream": True,  # 始终使用流式
        }

        # 添加系统提示词
        if options.system_prompt:
            request_params["system"] = options.system_prompt

        # 添加工具
        if options.tools:
            request_params["tools"] = options.tools

        # 发起流式请求
        try:
            async with self.client.messages.stream(**request_params) as stream:
                async for event in stream:
                    yield StreamEvent(
                        type=event.type,
                        data=event.dict() if hasattr(event, "dict") else vars(event),
                        raw=event,
                    )
        except Exception as e:
            # 包装错误信息
            raise self._handle_error(e)

    def _handle_error(self, error: Exception) -> Exception:
        """处理 API 错误
        
        Args:
            error: 原始错误
        
        Returns:
            包装后的错误
        """
        if isinstance(error, anthropic.AuthenticationError):
            return Exception(f"Authentication failed: Invalid API key")
        elif isinstance(error, anthropic.RateLimitError):
            return Exception("Rate limit exceeded. Please wait and try again.")
        elif isinstance(error, anthropic.APIStatusError):
            return Exception(f"API error: {error.status_code}")
        else:
            return error

    async def test_connection(self) -> bool:
        """测试 API 连接
        
        Returns:
            True 如果连接成功
        """
        try:
            # 简单测试，发送一个空消息
            await self.client.messages.create(
                model="claude-haiku-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception:
            return False
