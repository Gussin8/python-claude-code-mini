"""
上下文管理

参考 TypeScript 版本：src/utils/context.ts

核心常量：
- MODEL_CONTEXT_WINDOW_DEFAULT: 模型上下文窗口大小（200k tokens）
- COMPACT_MAX_OUTPUT_TOKENS: Compact 操作的最大输出 token 数
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List

# === 上下文窗口常量 ===

# 模型上下文窗口大小（所有模型目前都是 200k tokens）
MODEL_CONTEXT_WINDOW_DEFAULT = 200_000

# Compact 操作的最大输出 token 数
COMPACT_MAX_OUTPUT_TOKENS = 20_000

# 默认最大输出 token 数
MAX_OUTPUT_TOKENS_DEFAULT = 32_000

# 最大输出 token 数上限
MAX_OUTPUT_TOKENS_UPPER_LIMIT = 64_000

# Capped default for slot-reservation optimization
CAPPED_DEFAULT_MAX_TOKENS = 8_000

# Escalated max tokens for retry
ESCALATED_MAX_TOKENS = 64_000


@dataclass
class TokenUsage:
    """Token 使用情况"""
    
    input_tokens: int = 0
    """输入 token 数"""
    
    output_tokens: int = 0
    """输出 token 数"""
    
    cache_creation_input_tokens: int = 0
    """缓存创建输入 token 数"""
    
    cache_read_input_tokens: int = 0
    """缓存读取输入 token 数"""
    
    @property
    def total_tokens(self) -> int:
        """总 token 数"""
        return (
            self.input_tokens +
            self.cache_creation_input_tokens +
            self.cache_read_input_tokens +
            self.output_tokens
        )


@dataclass
class Message:
    """消息对象"""
    
    role: str
    """消息角色 ('user', 'assistant', 'system')"""
    
    content: str | List[Dict[str, Any]]
    """消息内容"""
    
    type: str = 'message'
    """消息类型"""
    
    message: Optional[Dict[str, Any]] = None
    """完整消息对象（用于 assistant 消息）"""
    
    uuid: Optional[str] = None
    """消息 UUID"""
    
    is_meta: bool = False
    """是否为元消息"""
    
    is_compact_summary: bool = False
    """是否为压缩总结消息"""
    
    is_visible_in_transcript_only: bool = False
    """是否仅在转录本中可见"""
    
    subtype: Optional[str] = None
    """子类型（用于 system 消息）"""
    
    compact_metadata: Optional[Dict[str, Any]] = None
    """压缩元数据"""


@dataclass
class ConversationContext:
    """对话上下文"""
    
    model: Optional[str] = None
    """使用的模型"""
    
    agent_id: Optional[str] = None
    """Agent ID"""
    
    working_directory: Optional[str] = None
    """工作目录"""
    
    # 回调函数
    on_compact_progress: Optional[callable] = None
    """压缩进度回调"""
    
    set_stream_mode: Optional[callable] = None
    """设置流模式"""
    
    set_response_length: Optional[callable] = None
    """设置响应长度"""
    
    set_sdk_status: Optional[callable] = None
    """设置 SDK 状态"""
    
    abort_controller: Optional[Any] = None
    """中止控制器"""
    
    query_tracking: Optional[Dict[str, Any]] = None
    """查询跟踪信息"""
    
    options: Optional[Dict[str, Any]] = None
    """选项配置"""
    
    read_file_state: Optional[Any] = None
    """文件读取状态"""
    
    tool_permission_context: Optional[Any] = None
    """工具权限上下文"""
    
    def get_app_state(self) -> Dict[str, Any]:
        """获取应用状态"""
        return {
            'model': self.model,
            'agent_id': self.agent_id,
            'working_directory': self.working_directory,
        }


def get_model_max_output_tokens(model: str) -> Dict[str, int]:
    """
    获取模型的最大输出 token 数
    
    参考 TypeScript 版本的 getModelMaxOutputTokens
    
    Returns:
        dict: {'default': int, 'upperLimit': int}
    """
    model_lower = model.lower()
    
    if 'opus-4-6' in model_lower:
        return {'default': 64_000, 'upperLimit': 128_000}
    elif 'sonnet-4-6' in model_lower:
        return {'default': 32_000, 'upperLimit': 128_000}
    elif any(x in model_lower for x in ['opus-4-5', 'sonnet-4', 'haiku-4']):
        return {'default': 32_000, 'upperLimit': 64_000}
    elif 'opus-4-1' in model_lower or 'opus-4' in model_lower:
        return {'default': 32_000, 'upperLimit': 32_000}
    elif 'claude-3-opus' in model_lower:
        return {'default': 4_096, 'upperLimit': 4_096}
    elif 'claude-3-sonnet' in model_lower:
        return {'default': 8_192, 'upperLimit': 8_192}
    elif 'claude-3-haiku' in model_lower:
        return {'default': 4_096, 'upperLimit': 4_096}
    elif '3-5-sonnet' in model_lower or '3-5-haiku' in model_lower:
        return {'default': 8_192, 'upperLimit': 8_192}
    elif '3-7-sonnet' in model_lower:
        return {'default': 32_000, 'upperLimit': 64_000}
    else:
        return {'default': MAX_OUTPUT_TOKENS_DEFAULT, 'upperLimit': MAX_OUTPUT_TOKENS_UPPER_LIMIT}


def get_context_window_for_model(model: str, sdk_betas: Optional[List[str]] = None) -> int:
    """
    获取模型的上下文窗口大小
    
    Args:
        model: 模型名称
        sdk_betas: SDK beta 功能列表
    
    Returns:
        int: 上下文窗口大小（tokens）
    """
    # 默认 200K
    return MODEL_CONTEXT_WINDOW_DEFAULT


def calculate_context_percentages(
    current_usage: Dict[str, int],
    context_window_size: int,
) -> Dict[str, Optional[int]]:
    """
    计算上下文窗口使用百分比
    
    参考 TypeScript 版本的 calculateContextPercentages
    
    Args:
        current_usage: {'input_tokens': int, 'cache_creation_input_tokens': int, 'cache_read_input_tokens': int}
        context_window_size: 上下文窗口大小
    
    Returns:
        {'used': int, 'remaining': int} 或 {'used': None, 'remaining': None}
    """
    if not current_usage:
        return {'used': None, 'remaining': None}
    
    total_input_tokens = (
        current_usage.get('input_tokens', 0) +
        current_usage.get('cache_creation_input_tokens', 0) +
        current_usage.get('cache_read_input_tokens', 0)
    )
    
    used_percentage = round((total_input_tokens / context_window_size) * 100)
    clamped_used = min(100, max(0, used_percentage))
    
    return {
        'used': clamped_used,
        'remaining': 100 - clamped_used,
    }
