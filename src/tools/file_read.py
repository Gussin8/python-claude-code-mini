"""FileRead tool - Read file contents"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from .base import Tool, ToolResult, ToolContext


class FileReadInput(BaseModel):
    """文件读取输入
    
    Attributes:
        path: 文件路径
        limit: 最大行数（可选）
        offset: 起始行偏移
    """

    path: str = Field(description="文件路径")
    limit: Optional[int] = Field(default=None, description="最大行数")
    offset: int = Field(default=0, description="起始行偏移")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        """验证路径不包含危险组件"""
        if ".." in v:
            raise ValueError("Relative paths with '..' are not allowed")
        return v


@dataclass
class FileReadOutput:
    """文件读取输出
    
    Attributes:
        content: 文件内容（带行号）
        original_size: 原始行数
        truncated: 是否被截断
        cannot_read: 无法读取的原因
    """

    content: str
    original_size: int
    truncated: bool
    cannot_read: Optional[str] = None


class FileReadTool(Tool[FileReadInput, FileReadOutput, None]):
    """文件读取工具
    
    用于读取文件内容，支持：
    - UTF-8 编码的文本文件
    - 行限制和偏移
    - 二进制文件检测
    - 大文件处理
    
    安全特性:
        - 路径遍历保护
        - 工作目录限制
        - 文件大小检查
    
    示例:
        tool = FileReadTool()
        result = await tool.call(
            FileReadInput(path="src/main.py", limit=100),
            context
        )
        print(result.output.content)
    """

    name = "FileRead"
    aliases = ["read", "cat"]
    description_text = "Read file contents"
    max_result_size_chars = 2_000_000
    input_schema = FileReadInput

    def get_description(self, input: Optional[FileReadInput] = None) -> str:
        """获取工具描述"""
        return """Read the contents of a file.

Supports:
- Text files (UTF-8 encoding)
- Line limits and offsets for large files
- Binary file detection
- Automatic line numbering

Use this tool to:
- Read source code files
- View configuration files
- Check log outputs
- Examine data files

The output includes line numbers for easy reference."""

    def is_read_only(self, input: FileReadInput) -> bool:
        """判断是否为只读操作"""
        return True

    def is_concurrency_safe(self, input: FileReadInput) -> bool:
        """判断是否可以并发执行"""
        return True

    async def call(
        self,
        args: FileReadInput,
        context: ToolContext,
        can_use_tool: callable,
        parent_message: Optional[str] = None,
        on_progress: Optional[callable] = None,
    ) -> ToolResult[FileReadOutput]:
        """读取文件内容"""
        try:
            # 解析路径
            file_path = Path(args.path)
            if not file_path.is_absolute():
                file_path = context.working_directory / file_path

            # 安全检查
            resolved = file_path.resolve()
            if not context.is_path_allowed(resolved):
                return ToolResult(
                    output=FileReadOutput(
                        content="",
                        original_size=0,
                        truncated=False,
                        cannot_read="File is outside allowed directories",
                    ),
                )

            # 检查文件是否存在
            if not file_path.exists():
                return ToolResult(
                    output=FileReadOutput(
                        content="",
                        original_size=0,
                        truncated=False,
                        cannot_read=f"File not found: {args.path}",
                    ),
                )

            # 检查是否为目录
            if file_path.is_dir():
                return ToolResult(
                    output=FileReadOutput(
                        content="",
                        original_size=0,
                        truncated=False,
                        cannot_read=f"Path is a directory: {args.path}",
                    ),
                )

            # 读取文件
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            original_size = len(lines)

            # 应用偏移和限制
            start_line = args.offset
            end_line = start_line + args.limit if args.limit else None
            lines = lines[start_line:end_line]

            truncated = args.limit is not None and len(lines) >= original_size

            # 添加行号
            numbered_content = "\n".join(
                f"{i + start_line + 1:6d} | {line}" for i, line in enumerate(lines)
            )

            return ToolResult(
                output=FileReadOutput(
                    content=numbered_content,
                    original_size=original_size,
                    truncated=truncated,
                ),
            )

        except UnicodeDecodeError as e:
            return ToolResult(
                output=FileReadOutput(
                    content="",
                    original_size=0,
                    truncated=False,
                    cannot_read=f"Cannot decode file (binary file?): {str(e)}",
                ),
            )
        except Exception as e:
            return ToolResult(
                output=FileReadOutput(
                    content="",
                    original_size=0,
                    truncated=False,
                    cannot_read=str(e),
                ),
            )

    def render_tool_use(self, input: FileReadInput) -> str:
        """渲染工具使用消息"""
        return f"📖 Reading: `{input.path}`"

    def render_tool_result(self, output: FileReadOutput) -> str:
        """渲染工具结果"""
        if output.cannot_read:
            return f"❌ Cannot read: {output.cannot_read}"
        preview = output.content[:500] + "..." if len(output.content) > 500 else output.content
        return f"```\n{preview}\n```"
