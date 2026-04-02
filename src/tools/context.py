"""Tool execution context"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from pathlib import Path


@dataclass
class ToolContext:
    """工具执行上下文
    
    包含工具执行所需的所有状态和信息。
    
    Attributes:
        working_directory: 当前工作目录
        additional_directories: 额外允许访问的目录列表
        permission_mode: 权限模式 (default, auto, bypass, dontAsk)
        settings: 配置设置
        messages: 会话消息历史
        session_id: 会话 ID
        file_state_cache: 文件状态缓存
        add_notification: 通知回调
        tool_decisions: 权限决策追踪
    """

    # === 状态管理 ===
    working_directory: Path
    additional_directories: list[Path] = field(default_factory=list)

    # === 配置 ===
    permission_mode: str = "default"  # default, auto, bypass, dontAsk
    settings: dict[str, Any] = field(default_factory=dict)

    # === 会话信息 ===
    messages: list[dict] = field(default_factory=list)
    session_id: Optional[str] = None

    # === 缓存 ===
    file_state_cache: dict[str, Any] = field(default_factory=dict)

    # === 回调 ===
    add_notification: Optional[Callable] = None

    # === 权限追踪 ===
    tool_decisions: dict[str, Any] = field(default_factory=dict)

    def get_app_state(self) -> dict[str, Any]:
        """获取应用状态
        
        Returns:
            包含关键状态的字典
        """
        return {
            "working_directory": str(self.working_directory),
            "permission_mode": self.permission_mode,
            "settings": self.settings,
        }

    def is_path_allowed(self, path: Path) -> bool:
        """检查路径是否允许访问
        
        Args:
            path: 要检查的路径
        
        Returns:
            True 如果允许访问
        """
        resolved = path.resolve()
        
        # 检查工作目录
        if str(resolved).startswith(str(self.working_directory)):
            return True
        
        # 检查额外允许的目录
        for directory in self.additional_directories:
            if str(resolved).startswith(str(directory)):
                return True
        
        return False

    def record_tool_decision(self, tool_name: str, decision: str):
        """记录工具决策
        
        Args:
            tool_name: 工具名称
            decision: 决策 (allow/deny/ask)
        """
        if tool_name not in self.tool_decisions:
            self.tool_decisions[tool_name] = []
        self.tool_decisions[tool_name].append(decision)
