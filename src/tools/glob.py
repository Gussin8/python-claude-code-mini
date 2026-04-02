"""Glob tool - Pattern-based file matching"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from .base import Tool, ToolResult, ToolContext


class GlobInput(BaseModel):
    """Glob 输入
    
    Attributes:
        pattern: 文件模式（如 *.py, **/*.txt）
        path: 搜索路径（可选，默认为当前工作目录）
    """

    pattern: str = Field(description="文件模式（如 *.py, **/*.txt）")
    path: Optional[str] = Field(default=None, description="搜索路径")

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v):
        """验证模式不包含危险组件"""
        if ".." in v:
            raise ValueError("Pattern cannot contain '..'")
        return v


@dataclass
class GlobOutput:
    """Glob 输出
    
    Attributes:
        matches: 匹配的文件路径列表
        count: 匹配数量
    """

    matches: list[str]
    count: int


class GlobTool(Tool[GlobInput, GlobOutput, None]):
    """Glob 工具 - 文件模式匹配
    
    使用 glob 模式查找匹配的文件。
    
    支持的模式:
        - * : 匹配任意非路径分隔符字符
        - ** : 递归匹配所有子目录
        - ? : 匹配单个字符
        - [seq] : 匹配序列中的任意字符
        - [!seq] : 匹配不在序列中的字符
    
    示例:
        tool = GlobTool()
        result = await tool.call(
            GlobInput(pattern="**/*.py"),
            context
        )
        print(result.output.matches)
    """

    name = "Glob"
    aliases = ["match", "find-files"]
    description_text = "Pattern-based file matching"
    max_result_size_chars = 100_000
    input_schema = GlobInput

    def get_description(self, input: Optional[GlobInput] = None) -> str:
        """获取工具描述"""
        return """Find files matching a glob pattern.

Supported patterns:
- * : Matches any characters except path separators
- ** : Recursively matches all subdirectories
- ? : Matches a single character
- [seq] : Matches any character in seq
- [!seq] : Matches any character not in seq

Use this tool to:
- Find all Python files (*.py)
- Search recursively (**/*.txt)
- Match specific naming patterns (test_*.py)"""

    def is_read_only(self, input: GlobInput) -> bool:
        """判断是否为只读操作"""
        return True

    def is_concurrency_safe(self, input: GlobInput) -> bool:
        """判断是否可以并发执行"""
        return True

    async def call(
        self,
        args: GlobInput,
        context: ToolContext,
        can_use_tool: callable,
        parent_message: Optional[str] = None,
        on_progress: Optional[callable] = None,
    ) -> ToolResult[GlobOutput]:
        """执行 glob 匹配"""
        try:
            # 确定搜索路径
            search_path = Path(args.path) if args.path else context.working_directory
            
            if not search_path.is_absolute():
                search_path = context.working_directory / search_path

            # 安全检查
            resolved = search_path.resolve()
            if not context.is_path_allowed(resolved):
                return ToolResult(
                    output=GlobOutput(
                        matches=[],
                        count=0,
                    ),
                    error="Search path is outside allowed directories",
                )

            # 执行 glob 匹配
            import glob as glob_module
            
            pattern = str(search_path / args.pattern)
            matches = glob_module.glob(pattern, recursive=True)
            
            # 过滤结果，确保在允许的目录内
            allowed_matches = [
                match for match in matches
                if context.is_path_allowed(Path(match))
            ]
            
            # 转换为相对路径
            relative_matches = [
                str(Path(match).relative_to(context.working_directory))
                for match in allowed_matches
            ]

            return ToolResult(
                output=GlobOutput(
                    matches=relative_matches,
                    count=len(relative_matches),
                ),
            )

        except Exception as e:
            return ToolResult(
                output=GlobOutput(
                    matches=[],
                    count=0,
                ),
                error=str(e),
            )

    def render_tool_use(self, input: GlobInput) -> str:
        """渲染工具使用消息"""
        path_str = f" in {input.path}" if input.path else ""
        return f"🔍 Finding: `{input.pattern}`{path_str}"

    def render_tool_result(self, output: GlobOutput) -> str:
        """渲染工具结果"""
        if output.count == 0:
            return "No files found"
        
        lines = [f"Found {output.count} file(s):"]
        for match in output.matches[:50]:  # 限制显示数量
            lines.append(f"  - {match}")
        
        if output.count > 50:
            lines.append(f"  ... and {output.count - 50} more")
        
        return "\n".join(lines)
