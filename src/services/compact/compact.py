"""
Compact 主逻辑

参考 TypeScript 版本：src/services/compact/compact.ts

核心功能：
1. compact_conversation - 创建对话的压缩版本
2. partial_compact_conversation - 部分压缩
3. auto_compact_if_needed - 自动压缩触发
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from ..api import APIService
from .prompt import (
    get_compact_prompt,
    get_partial_compact_prompt,
    format_compact_summary,
    get_compact_user_summary_message,
)
from .grouping import group_messages_by_api_round
from ..context import (
    ConversationContext,
    Message,
    TokenUsage,
    token_count_with_estimation,
    rough_token_count_estimation_for_messages,
)


# === 常量定义 ===

POST_COMPACT_MAX_FILES_TO_RESTORE = 5
POST_COMPACT_TOKEN_BUDGET = 50_000
POST_COMPACT_MAX_TOKENS_PER_FILE = 5_000
POST_COMPACT_MAX_TOKENS_PER_SKILL = 5_000
POST_COMPACT_SKILLS_TOKEN_BUDGET = 25_000
MAX_COMPACT_STREAMING_RETRIES = 2

# 错误消息
ERROR_MESSAGE_NOT_ENOUGH_MESSAGES = "Not enough messages to compact."
ERROR_MESSAGE_PROMPT_TOO_LONG = (
    "Conversation too long. Press esc twice to go up a few messages and try again."
)
ERROR_MESSAGE_USER_ABORT = "API Error: Request was aborted."
ERROR_MESSAGE_INCOMPLETE_RESPONSE = (
    "Compaction interrupted · This may be due to network issues — please try again."
)

# 自动压缩配置
AUTOCOMPACT_BUFFER_TOKENS = 13_000
WARNING_THRESHOLD_BUFFER_TOKENS = 20_000
ERROR_THRESHOLD_BUFFER_TOKENS = 20_000
MANUAL_COMPACT_BUFFER_TOKENS = 3_000
MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3
MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000

# PTL 重试
MAX_PTL_RETRIES = 3
PTL_RETRY_MARKER = "[earlier conversation truncated for compaction retry]"


class CompactType(str, Enum):
    """压缩类型"""
    FULL = "full"
    PARTIAL = "partial"
    UP_TO = "up_to"


class CompactTrigger(str, Enum):
    """压缩触发方式"""
    MANUAL = "manual"
    AUTO = "auto"


@dataclass
class CompactionResult:
    """压缩操作结果"""
    
    boundary_marker: Message
    """压缩边界标记"""
    
    summary_messages: List[Message]
    """总结消息列表"""
    
    attachments: List[Message] = field(default_factory=list)
    """附件消息列表"""
    
    hook_results: List[Message] = field(default_factory=list)
    """钩子结果消息列表"""
    
    messages_to_keep: Optional[List[Message]] = None
    """需要保留的消息（部分压缩）"""
    
    user_display_message: Optional[str] = None
    """用户显示消息"""
    
    pre_compact_token_count: Optional[int] = None
    """压缩前 token 数"""
    
    post_compact_token_count: Optional[int] = None
    """压缩后 token 数（API 调用总用量）"""
    
    true_post_compact_token_count: Optional[int] = None
    """真实的压缩后上下文 token 数"""
    
    compaction_usage: Optional[TokenUsage] = None
    """压缩 API 调用的用量详情"""


@dataclass
class RecompactionInfo:
    """重新压缩信息"""
    
    is_recompaction_in_chain: bool
    """是否是链中的重新压缩"""
    
    turns_since_previous_compact: int
    """距离上次压缩的轮数"""
    
    previous_compact_turn_id: Optional[str] = None
    """上次压缩的轮 ID"""
    
    auto_compact_threshold: int = 0
    """自动压缩阈值"""
    
    query_source: Optional[str] = None
    """查询来源"""


@dataclass
class AutoCompactTrackingState:
    """自动压缩跟踪状态"""
    
    compacted: bool = False
    """是否已压缩"""
    
    turn_counter: int = 0
    """轮计数器"""
    
    turn_id: str = ""
    """当前轮 ID"""
    
    consecutive_failures: int = 0
    """连续失败次数"""


def get_effective_context_window_size(model: str) -> int:
    """
    获取有效上下文窗口大小
    
    返回模型的上下文窗口减去最大输出 token 数
    """
    from ..context import (
        MODEL_CONTEXT_WINDOW_DEFAULT,
        get_model_max_output_tokens,
    )
    
    # 获取模型的最大输出 token 数
    model_tokens = get_model_max_output_tokens(model)
    reserved_tokens = min(
        model_tokens.get('default', MAX_OUTPUT_TOKENS_FOR_SUMMARY),
        MAX_OUTPUT_TOKENS_FOR_SUMMARY,
    )
    
    # 获取上下文窗口
    context_window = MODEL_CONTEXT_WINDOW_DEFAULT
    
    # 支持环境变量覆盖
    import os
    auto_compact_window = os.environ.get('CLAUDE_CODE_AUTO_COMPACT_WINDOW')
    if auto_compact_window:
        parsed = int(auto_compact_window)
        if parsed > 0:
            context_window = min(context_window, parsed)
    
    return context_window - reserved_tokens


def get_auto_compact_threshold(model: str) -> int:
    """
    获取自动压缩阈值
    
    基于有效上下文窗口减去缓冲区
    """
    effective_window = get_effective_context_window_size(model)
    threshold = effective_window - AUTOCOMPACT_BUFFER_TOKENS
    
    # 支持环境变量覆盖（用于测试）
    import os
    env_percent = os.environ.get('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE')
    if env_percent:
        parsed = float(env_percent)
        if 0 < parsed <= 100:
            percentage_threshold = int(effective_window * (parsed / 100))
            return min(percentage_threshold, threshold)
    
    return threshold


def calculate_token_warning_state(
    token_usage: int,
    model: str,
) -> Dict[str, Any]:
    """
    计算 token 警告状态
    
    Returns:
        dict: {
            'percent_left': int,
            'is_above_warning_threshold': bool,
            'is_above_error_threshold': bool,
            'is_above_auto_compact_threshold': bool,
            'is_at_blocking_limit': bool,
        }
    """
    auto_compact_threshold = get_auto_compact_threshold(model)
    threshold = auto_compact_threshold  # 假设自动压缩已启用
    
    percent_left = max(
        0,
        round(((threshold - token_usage) / threshold) * 100),
    )
    
    warning_threshold = threshold - WARNING_THRESHOLD_BUFFER_TOKENS
    error_threshold = threshold - ERROR_THRESHOLD_BUFFER_TOKENS
    
    is_above_warning = token_usage >= warning_threshold
    is_above_error = token_usage >= error_threshold
    is_above_auto = token_usage >= auto_compact_threshold
    
    # 阻塞限制
    actual_window = get_effective_context_window_size(model)
    default_blocking = actual_window - MANUAL_COMPACT_BUFFER_TOKENS
    
    import os
    blocking_override = os.environ.get('CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE')
    if blocking_override:
        parsed = int(blocking_override)
        if parsed > 0:
            blocking_limit = parsed
        else:
            blocking_limit = default_blocking
    else:
        blocking_limit = default_blocking
    
    is_at_blocking = token_usage >= blocking_limit
    
    return {
        'percent_left': percent_left,
        'is_above_warning_threshold': is_above_warning,
        'is_above_error_threshold': is_above_error,
        'is_above_auto_compact_threshold': is_above_auto,
        'is_at_blocking_limit': is_at_blocking,
    }


async def stream_compact_summary(
    messages: List[Message],
    summary_request: Message,
    context: ConversationContext,
    pre_compact_token_count: int,
    cache_safe_params: Optional[Dict[str, Any]] = None,
) -> Message:
    """
    流式压缩摘要
    
    使用 forked agent 模式进行摘要生成，重用主对话的 prompt cache。
    """
    api_service = APIService()
    
    # 准备系统提示词
    system_prompt = "You are a conversation summarizer. Respond with TEXT ONLY."
    
    # 准备消息
    api_messages = []
    for msg in messages:
        api_messages.append({
            'role': msg.role,
            'content': msg.content,
        })
    
    # 添加摘要请求
    api_messages.append({
        'role': 'user',
        'content': summary_request.content,
    })
    
    try:
        # 调用 API 进行摘要
        response = await api_service.query(
            messages=api_messages,
            system=system_prompt,
            max_tokens=COMPACT_MAX_OUTPUT_TOKENS,
            temperature=0,
        )
        
        # 创建助手消息
        assistant_msg = Message(
            role='assistant',
            content=response.get('content', ''),
            message={
                'id': response.get('id', ''),
                'type': 'message',
                'role': 'assistant',
                'content': [{'type': 'text', 'text': response.get('content', '')}],
            }
        )
        
        return assistant_msg
        
    except Exception as e:
        # 处理错误
        error_msg = f"API Error: {str(e)}"
        return Message(
            role='assistant',
            content=error_msg,
            message={
                'id': '',
                'type': 'message',
                'role': 'assistant',
                'content': [{'type': 'text', 'text': error_msg}],
            }
        )


def truncate_head_for_ptl_retry(
    messages: List[Message],
    ptl_response: Message,
) -> Optional[List[Message]]:
    """
    为 PTL 重试截断头部消息
    
    当压缩请求本身触发 prompt-too-long 错误时的最后手段。
    """
    # 移除之前的重试标记
    input_messages = messages
    if (messages and 
        messages[0].get('type') == 'user' and 
        messages[0].get('is_meta') and
        messages[0].get('content') == PTL_RETRY_MARKER):
        input_messages = messages[1:]
    
    # 按 API 轮次分组
    groups = group_messages_by_api_round(input_messages)
    
    if len(groups) < 2:
        return None
    
    # 计算 token gap
    token_gap = _get_prompt_too_long_token_gap(ptl_response)
    
    if token_gap is not None:
        # 累加直到覆盖 gap
        acc = 0
        drop_count = 0
        for group in groups:
            acc += rough_token_count_estimation_for_messages(group)
            drop_count += 1
            if acc >= token_gap:
                break
    else:
        # 回退到丢弃 20%
        drop_count = max(1, int(len(groups) * 0.2))
    
    # 确保至少保留一组
    drop_count = min(drop_count, len(groups) - 1)
    
    if drop_count < 1:
        return None
    
    # 截取剩余组
    sliced = groups[drop_count:]
    flattened = [msg for group in sliced for msg in group]
    
    # 如果第一个消息是助手，添加用户标记
    if flattened and flattened[0].get('type') == 'assistant':
        marker_msg = {
            'type': 'user',
            'is_meta': True,
            'content': PTL_RETRY_MARKER,
            'message': {
                'type': 'message',
                'role': 'user',
                'content': [{'type': 'text', 'text': PTL_RETRY_MARKER}],
            }
        }
        return [marker_msg] + flattened
    
    return flattened


def _get_prompt_too_long_token_gap(response: Message) -> Optional[int]:
    """从 prompt-too-long 响应中提取 token gap"""
    # TODO: 解析响应内容提取 gap
    # 示例："Prompt too long by 5000 tokens"
    content = response.get('content', '')
    import re
    match = re.search(r'(\d+)\s*tokens?', content)
    if match:
        return int(match.group(1))
    return None


async def compact_conversation(
    messages: List[Message],
    context: ConversationContext,
    cache_safe_params: Optional[Dict[str, Any]] = None,
    suppress_follow_up_questions: bool = False,
    custom_instructions: Optional[str] = None,
    is_auto_compact: bool = False,
    recompaction_info: Optional[RecompactionInfo] = None,
) -> CompactionResult:
    """
    压缩对话
    
    创建对话的压缩版本，通过总结旧消息并保留最近的对话历史。
    
    Args:
        messages: 要压缩的消息列表
        context: 工具使用上下文
        cache_safe_params: 缓存安全参数
        suppress_follow_up_questions: 是否抑制后续问题
        custom_instructions: 自定义指令
        is_auto_compact: 是否为自动压缩
        recompaction_info: 重新压缩信息
    
    Returns:
        CompactionResult: 压缩结果
    
    Raises:
        ValueError: 当消息数量不足时
        RuntimeError: 当压缩失败时
    """
    if not messages:
        raise ValueError(ERROR_MESSAGE_NOT_ENOUGH_MESSAGES)
    
    # 计算压缩前的 token 数
    pre_compact_token_count = token_count_with_estimation(messages)
    
    # 获取压缩提示词
    compact_prompt = get_compact_prompt(custom_instructions)
    
    # 创建摘要请求
    summary_request = Message(
        role='user',
        content=compact_prompt,
    )
    
    # 重试循环
    messages_to_summarize = messages
    retry_cache_params = cache_safe_params or {}
    ptl_attempts = 0
    
    while True:
        # 流式压缩摘要
        summary_response = await stream_compact_summary(
            messages=messages_to_summarize,
            summary_request=summary_request,
            context=context,
            pre_compact_token_count=pre_compact_token_count,
            cache_safe_params=retry_cache_params,
        )
        
        summary = summary_response.get('content', '')
        
        # 检查是否 prompt too long
        if not summary.startswith("Prompt too long"):
            break
        
        # PTL 重试
        ptl_attempts += 1
        if ptl_attempts <= MAX_PTL_RETRIES:
            truncated = truncate_head_for_ptl_retry(
                messages_to_summarize,
                summary_response,
            )
        else:
            truncated = None
        
        if not truncated:
            raise RuntimeError(ERROR_MESSAGE_PROMPT_TOO_LONG)
        
        messages_to_summarize = truncated
        retry_cache_params = {
            **retry_cache_params,
            'fork_context_messages': truncated,
        }
    
    # 验证摘要
    if not summary:
        raise RuntimeError("Failed to generate conversation summary")
    
    if summary.startswith("API Error:"):
        raise RuntimeError(summary)
    
    # 创建压缩边界标记
    boundary_marker = _create_compact_boundary_message(
        CompactTrigger.AUTO if is_auto_compact else CompactTrigger.MANUAL,
        pre_compact_token_count,
        messages[-1] if messages else None,
    )
    
    # 创建总结消息
    transcript_path = _get_transcript_path()
    summary_content = get_compact_user_summary_message(
        summary,
        suppress_follow_up_questions,
        transcript_path,
    )
    
    summary_messages = [Message(
        role='user',
        content=summary_content,
        is_compact_summary=True,
        is_visible_in_transcript_only=True,
    )]
    
    # 计算 token 使用
    compaction_call_total_tokens = _token_count_from_last_api_response([summary_response])
    
    # 估算真实的压缩后上下文大小
    true_post_compact_token_count = rough_token_count_estimation_for_messages([
        boundary_marker,
        *summary_messages,
    ])
    
    # 提取用量指标
    compaction_usage = _get_token_usage(summary_response)
    
    # 构建结果
    result = CompactionResult(
        boundary_marker=boundary_marker,
        summary_messages=summary_messages,
        attachments=[],
        hook_results=[],
        user_display_message=None,
        pre_compact_token_count=pre_compact_token_count,
        post_compact_token_count=compaction_call_total_tokens,
        true_post_compact_token_count=true_post_compact_token_count,
        compaction_usage=compaction_usage,
    )
    
    return result


def _create_compact_boundary_message(
    trigger: CompactTrigger,
    pre_compact_tokens: int,
    last_message: Optional[Message],
) -> Message:
    """创建压缩边界标记消息"""
    return Message(
        type='system',
        subtype='compact_boundary',
        content=f'__COMPACT_BOUNDARY:{trigger.value}__',
        compact_metadata={
            'trigger': trigger.value,
            'pre_compact_tokens': pre_compact_tokens,
            'last_message_uuid': last_message.get('uuid') if last_message else None,
        }
    )


def _get_transcript_path() -> Optional[str]:
    """获取转录本路径"""
    # TODO: 实现会话存储路径获取
    return None


def _token_count_from_last_api_response(messages: List[Message]) -> int:
    """从最后一个 API 响应中计算 token 数"""
    if not messages:
        return 0
    return token_count_with_estimation(messages)


def _get_token_usage(response: Message) -> Optional[TokenUsage]:
    """从响应中提取 token 使用情况"""
    # TODO: 解析响应中的 usage 字段
    usage_data = response.get('usage', {})
    if not usage_data:
        return None
    
    return TokenUsage(
        input_tokens=usage_data.get('input_tokens', 0),
        output_tokens=usage_data.get('output_tokens', 0),
        cache_creation_input_tokens=usage_data.get('cache_creation_input_tokens', 0),
        cache_read_input_tokens=usage_data.get('cache_read_input_tokens', 0),
    )


async def partial_compact_conversation(
    all_messages: List[Message],
    pivot_index: int,
    context: ConversationContext,
    cache_safe_params: Optional[Dict[str, Any]] = None,
    user_feedback: Optional[str] = None,
    direction: str = 'from',
) -> CompactionResult:
    """
    部分压缩对话
    
    围绕选定的消息索引进行部分压缩。
    
    Args:
        all_messages: 所有消息
        pivot_index: 枢轴索引
        context: 工具使用上下文
        cache_safe_params: 缓存安全参数
        user_feedback: 用户反馈
        direction: 压缩方向 ('from' 或 'up_to')
    
    Returns:
        CompactionResult: 压缩结果
    """
    # 确定要总结和保留的消息
    if direction == 'up_to':
        messages_to_summarize = all_messages[:pivot_index]
        messages_to_keep = [
            m for m in all_messages[pivot_index:]
            if m.get('type') != 'progress'
        ]
    else:  # 'from'
        messages_to_summarize = all_messages[pivot_index:]
        messages_to_keep = all_messages[:pivot_index]
    
    # 获取部分压缩提示词
    custom_instructions = user_feedback if user_feedback else None
    compact_prompt = get_partial_compact_prompt(
        custom_instructions,
        direction=direction,
    )
    
    # 创建摘要请求
    summary_request = Message(
        role='user',
        content=compact_prompt,
    )
    
    # 执行压缩
    summary_response = await stream_compact_summary(
        messages=messages_to_summarize,
        summary_request=summary_request,
        context=context,
        pre_compact_token_count=token_count_with_estimation(messages_to_summarize),
        cache_safe_params=cache_safe_params,
    )
    
    summary = summary_response.get('content', '')
    
    # 创建边界和总结消息
    boundary_marker = _create_compact_boundary_message(
        CompactTrigger.MANUAL,
        token_count_with_estimation(messages_to_summarize),
        messages_to_summarize[-1] if messages_to_summarize else None,
    )
    
    summary_messages = [Message(
        role='user',
        content=get_compact_user_summary_message(summary, False),
        is_compact_summary=True,
        is_visible_in_transcript_only=True,
    )]
    
    # 构建结果
    return CompactionResult(
        boundary_marker=boundary_marker,
        summary_messages=summary_messages,
        attachments=[],
        hook_results=[],
        messages_to_keep=messages_to_keep,
        pre_compact_token_count=token_count_with_estimation(all_messages),
        post_compact_token_count=token_count_with_estimation([
            boundary_marker,
            *summary_messages,
            *(messages_to_keep or []),
        ]),
    )


async def auto_compact_if_needed(
    messages: List[Message],
    context: ConversationContext,
    tracking_state: AutoCompactTrackingState,
) -> Tuple[bool, Optional[CompactionResult]]:
    """
    自动压缩（如需要）
    
    检查是否需要自动压缩，并在需要时执行。
    
    Args:
        messages: 当前消息列表
        context: 工具使用上下文
        tracking_state: 跟踪状态
    
    Returns:
        Tuple[bool, Optional[CompactionResult]]: (是否执行了压缩，压缩结果)
    """
    # 检查连续失败次数
    if tracking_state.consecutive_failures >= MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES:
        return False, None
    
    # 计算当前 token 使用
    current_usage = token_count_with_estimation(messages)
    model = context.model or 'claude-sonnet-4-20250514'
    
    # 检查是否超过自动压缩阈值
    warning_state = calculate_token_warning_state(current_usage, model)
    
    if not warning_state['is_above_auto_compact_threshold']:
        return False, None
    
    # 增加失败计数
    tracking_state.consecutive_failures += 1
    
    try:
        # 执行压缩
        result = await compact_conversation(
            messages=messages,
            context=context,
            is_auto_compact=True,
            recompaction_info=RecompactionInfo(
                is_recompaction_in_chain=False,
                turns_since_previous_compact=tracking_state.turn_counter,
                previous_compact_turn_id=tracking_state.turn_id,
                auto_compact_threshold=get_auto_compact_threshold(model),
            ),
        )
        
        # 重置失败计数
        tracking_state.consecutive_failures = 0
        tracking_state.compacted = True
        
        return True, result
        
    except Exception as e:
        # 记录错误但不抛出
        print(f"[auto_compact] Failed: {e}")
        return False, None
