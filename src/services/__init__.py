"""Services layer"""

from .api import APIService, QueryOptions, StreamEvent
from .retry import with_retry, RetryError
from .prompt import SystemPromptBuilder, CompactPromptBuilder, CompactOptions
from .context import (
    ConversationContext,
    Message,
    TokenUsage,
    get_model_max_output_tokens,
    get_context_window_for_model,
    calculate_context_percentages,
)
from .tokens import (
    token_count_with_estimation,
    rough_token_count_estimation,
    rough_token_count_estimation_for_messages,
    get_token_usage,
    token_count_from_last_api_response,
)
from .compact import (
    # 常量
    POST_COMPACT_MAX_FILES_TO_RESTORE,
    COMPACT_MAX_OUTPUT_TOKENS,
    AUTOCOMPACT_BUFFER_TOKENS,
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
    group_messages_by_api_round,
)

__all__ = [
    # API
    "APIService",
    "QueryOptions",
    "StreamEvent",
    # Retry
    "with_retry",
    "RetryError",
    # Prompt
    "SystemPromptBuilder",
    "CompactPromptBuilder",
    "CompactOptions",
    # Context
    "ConversationContext",
    "Message",
    "TokenUsage",
    "get_model_max_output_tokens",
    "get_context_window_for_model",
    "calculate_context_percentages",
    # Tokens
    "token_count_with_estimation",
    "rough_token_count_estimation",
    "rough_token_count_estimation_for_messages",
    "get_token_usage",
    "token_count_from_last_api_response",
    # Compact
    "POST_COMPACT_MAX_FILES_TO_RESTORE",
    "COMPACT_MAX_OUTPUT_TOKENS",
    "AUTOCOMPACT_BUFFER_TOKENS",
    "CompactionResult",
    "RecompactionInfo",
    "AutoCompactTrackingState",
    "CompactType",
    "CompactTrigger",
    "compact_conversation",
    "partial_compact_conversation",
    "auto_compact_if_needed",
    "get_auto_compact_threshold",
    "calculate_token_warning_state",
    "group_messages_by_api_round",
]
