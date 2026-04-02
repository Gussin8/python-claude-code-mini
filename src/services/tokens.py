"""
Token 计算工具

参考 TypeScript 版本：src/utils/tokens.ts

核心功能：
1. token_count_with_estimation - 使用估算计算 token 数
2. rough_token_count_estimation - 粗略 token 估算
3. get_token_usage - 获取 token 使用情况
"""

from typing import List, Dict, Any, Optional
from .context import Message, TokenUsage


# tiktoken 用于精确 token 计算（可选依赖）
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


# 每个消息的基础开销（估计值）
MESSAGE_BASE_OVERHEAD = 4

# 每个内容块的开销
CONTENT_BLOCK_OVERHEAD = 2


def token_count_with_estimation(messages: List[Message | Dict[str, Any]]) -> int:
    """
    使用估算计算 token 数
    
    结合精确计算（如果可用）和启发式估算。
    
    Args:
        messages: 消息列表
    
    Returns:
        int: 估算的 token 数
    """
    if not messages:
        return 0
    
    total_tokens = 0
    
    for msg in messages:
        # 转换为 Message 对象（如果是 dict）
        if isinstance(msg, dict):
            msg_obj = _dict_to_message(msg)
        else:
            msg_obj = msg
        
        # 计算消息 token
        msg_tokens = _count_message_tokens(msg_obj)
        total_tokens += msg_tokens
    
    return total_tokens


def _dict_to_message(msg_dict: Dict[str, Any]) -> Message:
    """将字典转换为 Message 对象"""
    return Message(
        role=msg_dict.get('role', 'user'),
        content=msg_dict.get('content', ''),
        type=msg_dict.get('type', 'message'),
        message=msg_dict.get('message'),
        uuid=msg_dict.get('uuid'),
        is_meta=msg_dict.get('is_meta', False),
        is_compact_summary=msg_dict.get('is_compact_summary', False),
        subtype=msg_dict.get('subtype'),
    )


def _count_message_tokens(msg: Message) -> int:
    """
    计算单个消息的 token 数
    
    Args:
        msg: Message 对象
    
    Returns:
        int: token 数
    """
    tokens = MESSAGE_BASE_OVERHEAD
    
    # 计算角色 token
    tokens += _count_text_tokens(msg.role)
    
    # 计算内容 token
    if isinstance(msg.content, str):
        tokens += _count_text_tokens(msg.content)
    elif isinstance(msg.content, list):
        for block in msg.content:
            if isinstance(block, dict):
                block_type = block.get('type', '')
                if block_type == 'text':
                    tokens += _count_text_tokens(block.get('text', ''))
                elif block_type == 'tool_use':
                    tokens += _count_tool_use_tokens(block)
                elif block_type == 'tool_result':
                    tokens += _count_tool_result_tokens(block)
    
    # 如果有完整的 message 对象，计算额外的 token
    if msg.message:
        msg_content = msg.message.get('content', [])
        if isinstance(msg_content, list):
            for block in msg_content:
                if isinstance(block, dict):
                    block_type = block.get('type', '')
                    if block_type == 'text':
                        tokens += _count_text_tokens(block.get('text', ''))
                    elif block_type == 'tool_use':
                        tokens += _count_tool_use_tokens(block)
    
    return tokens


def _count_text_tokens(text: str) -> int:
    """
    计算文本的 token 数
    
    使用 tiktoken（如果可用）或启发式估算。
    
    Args:
        text: 文本字符串
    
    Returns:
        int: token 数
    """
    if not text:
        return 0
    
    # 优先使用 tiktoken
    if TIKTOKEN_AVAILABLE:
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            pass
    
    # 回退到启发式估算
    # 英文：约 4 字符/token
    # 中文：约 1.5 字符/token
    # 混合：取平均值
    
    # 检测中文字符比例
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text)
    
    if total_chars == 0:
        return 0
    
    chinese_ratio = chinese_chars / total_chars
    
    # 加权平均
    avg_chars_per_token = (
        4 * (1 - chinese_ratio) +  # 英文部分
        1.5 * chinese_ratio  # 中文部分
    )
    
    return int(total_chars / avg_chars_per_token) + CONTENT_BLOCK_OVERHEAD


def _count_tool_use_tokens(tool_block: Dict[str, Any]) -> int:
    """
    计算 tool_use 块的 token 数
    
    Args:
        tool_block: tool_use 内容块
    
    Returns:
        int: token 数
    """
    tokens = CONTENT_BLOCK_OVERHEAD
    
    # ID
    if 'id' in tool_block:
        tokens += _count_text_tokens(tool_block['id'])
    
    # Name
    if 'name' in tool_block:
        tokens += _count_text_tokens(tool_block['name'])
    
    # Input
    if 'input' in tool_block:
        import json
        try:
            input_str = json.dumps(tool_block['input'])
            tokens += _count_text_tokens(input_str)
        except Exception:
            tokens += 10  # 默认估算
    
    return tokens


def _count_tool_result_tokens(result_block: Dict[str, Any]) -> int:
    """
    计算 tool_result 块的 token 数
    
    Args:
        result_block: tool_result 内容块
    
    Returns:
        int: token 数
    """
    tokens = CONTENT_BLOCK_OVERHEAD
    
    # Tool use ID
    if 'tool_use_id' in result_block:
        tokens += _count_text_tokens(result_block['tool_use_id'])
    
    # Content
    content = result_block.get('content', '')
    if isinstance(content, str):
        tokens += _count_text_tokens(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                tokens += _count_text_tokens(item.get('text', ''))
    
    return tokens


def rough_token_count_estimation(messages: List[Message | Dict[str, Any]]) -> int:
    """
    粗略 token 估算
    
    更快的估算方法，适用于大量消息的快速估算。
    
    Args:
        messages: 消息列表
    
    Returns:
        int: 估算的 token 数
    """
    if not messages:
        return 0
    
    total_chars = 0
    
    for msg in messages:
        # 基础开销
        total_chars += MESSAGE_BASE_OVERHEAD * 4  # 假设每 token 4 字符
        
        # 角色
        if isinstance(msg, Message):
            total_chars += len(msg.role)
            if isinstance(msg.content, str):
                total_chars += len(msg.content)
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        total_chars += len(block.get('text', ''))
        elif isinstance(msg, dict):
            total_chars += len(msg.get('role', ''))
            content = msg.get('content', '')
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        total_chars += len(block.get('text', ''))
    
    # 粗略估算：每 4 字符约 1 token
    return total_chars // 4 + len(messages) * CONTENT_BLOCK_OVERHEAD


def rough_token_count_estimation_for_messages(messages: List[Message | Dict[str, Any]]) -> int:
    """
    为消息列表进行粗略 token 估算
    
    与 rough_token_count_estimation 相同，但名称与 TS 版本保持一致。
    
    Args:
        messages: 消息列表
    
    Returns:
        int: 估算的 token 数
    """
    return rough_token_count_estimation(messages)


def get_token_usage(response: Dict[str, Any]) -> Optional[TokenUsage]:
    """
    从 API 响应中提取 token 使用情况
    
    Args:
        response: API 响应
    
    Returns:
        TokenUsage 或 None
    """
    usage_data = response.get('usage', {})
    
    if not usage_data:
        return None
    
    return TokenUsage(
        input_tokens=usage_data.get('input_tokens', 0),
        output_tokens=usage_data.get('output_tokens', 0),
        cache_creation_input_tokens=usage_data.get('cache_creation_input_tokens', 0),
        cache_read_input_tokens=usage_data.get('cache_read_input_tokens', 0),
    )


def token_count_from_last_api_response(messages: List[Message]) -> int:
    """
    从最后一个 API 响应消息中计算 token 数
    
    Args:
        messages: 消息列表
    
    Returns:
        int: token 数
    """
    if not messages:
        return 0
    
    # 找到最后一个 assistant 消息
    last_assistant_msg = None
    for msg in reversed(messages):
        if isinstance(msg, Message) and msg.role == 'assistant':
            last_assistant_msg = msg
            break
        elif isinstance(msg, dict) and msg.get('role') == 'assistant':
            last_assistant_msg = _dict_to_message(msg)
            break
    
    if not last_assistant_msg:
        return 0
    
    # 计算 token
    return _count_message_tokens(last_assistant_msg)
