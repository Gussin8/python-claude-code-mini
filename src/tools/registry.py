"""Tool registry - Manage and retrieve tools"""

from typing import Type, Optional
from .base import Tool


# 全局工具注册表
_registered_tools: list[Tool] = []


def register_tool(tool_class: Type[Tool]) -> None:
    """注册一个工具
    
    Args:
        tool_class: 工具类（会自动实例化）
    """
    tool = tool_class()
    _registered_tools.append(tool)


def get_all_tools() -> list[Tool]:
    """获取所有已注册的工具
    
    Returns:
        工具列表
    """
    if not _registered_tools:
        # 首次加载时自动注册所有内置工具
        _register_builtin_tools()
    
    return _registered_tools.copy()


def get_tool_by_name(name: str) -> Optional[Tool]:
    """根据名称获取工具
    
    Args:
        name: 工具名称或别名
    
    Returns:
        工具实例，如果未找到则返回 None
    """
    if not _registered_tools:
        _register_builtin_tools()
    
    for tool in _registered_tools:
        if tool.name == name or name in tool.aliases:
            return tool
    return None


def _register_builtin_tools() -> None:
    """注册所有内置工具"""
    # 延迟导入以避免循环依赖
    from .bash import BashTool
    from .file_read import FileReadTool
    from .file_write import FileWriteTool
    from .file_edit import FileEditTool
    from .glob import GlobTool
    from .grep import GrepTool
    
    register_tool(BashTool)
    register_tool(FileReadTool)
    register_tool(FileWriteTool)
    register_tool(FileEditTool)
    register_tool(GlobTool)
    register_tool(GrepTool)


def clear_registry() -> None:
    """清除工具注册表（主要用于测试）"""
    _registered_tools.clear()
