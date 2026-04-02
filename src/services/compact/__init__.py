"""Compact 模块"""

from .prompt import (
    get_compact_prompt,
    get_partial_compact_prompt,
    format_compact_summary,
    get_compact_user_summary_message,
    BASE_COMPACT_PROMPT,
    PARTIAL_COMPACT_PROMPT,
    UP_TO_COMPACT_PROMPT,
    NO_TOOLS_PREAMBLE,
)
from .compact import (
    # 常量
    POST_COMPACT_MAX_FILES_TO_RESTORE,
    POST_COMPACT_TOKEN_BUDGET,
    POST_COMPACT_MAX_TOKENS_PER_FILE,
    MAX_COMPACT_STREAMING_RETRIES,
    ERROR_MESSAGE_NOT_ENOUGH_MESSAGES,
    ERROR_MESSAGE_PROMPT_TOO_LONG,
    ERROR_MESSAGE_USER_ABORT,
    AUTOCOMPACT_BUFFER_TOKENS,
    MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES,
    # 类型
    CompactionResult,
    RecompactionInfo,
    AutoCompactTrackingState,
    CompactType,
    CompactTrigger,
    # 函数
    compact_conversation,
    partial_compact_conversation,
    auto_compact_if_needed,
    get_auto_compact_threshold,
    calculate_token_warning_state,
    get_effective_context_window_size,
)
from .grouping import (
    group_messages_by_api_round,
    ensure_tool_result_pairing,
)

__all__ = [
    # 常量
    "POST_COMPACT_MAX_FILES_TO_RESTORE",
    "POST_COMPACT_TOKEN_BUDGET",
    "POST_COMPACT_MAX_TOKENS_PER_FILE",
    "MAX_COMPACT_STREAMING_RETRIES",
    "ERROR_MESSAGE_NOT_ENOUGH_MESSAGES",
    "ERROR_MESSAGE_PROMPT_TOO_LONG",
    "ERROR_MESSAGE_USER_ABORT",
    "AUTOCOMPACT_BUFFER_TOKENS",
    "MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES",
    # 提示词
    "get_compact_prompt",
    "get_partial_compact_prompt",
    "format_compact_summary",
    "get_compact_user_summary_message",
    "BASE_COMPACT_PROMPT",
    "PARTIAL_COMPACT_PROMPT",
    "UP_TO_COMPACT_PROMPT",
    "NO_TOOLS_PREAMBLE",
    # 类型
    "CompactionResult",
    "RecompactionInfo",
    "AutoCompactTrackingState",
    "CompactType",
    "CompactTrigger",
    # 核心函数
    "compact_conversation",
    "partial_compact_conversation",
    "auto_compact_if_needed",
    "get_auto_compact_threshold",
    "calculate_token_warning_state",
    "get_effective_context_window_size",
    # 分组
    "group_messages_by_api_round",
    "ensure_tool_result_pairing",
]
