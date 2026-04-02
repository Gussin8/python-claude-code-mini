"""FileWrite tool - Write files"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from .base import Tool, ToolResult, PermissionResult, ToolContext


class FileWriteInput(BaseModel):
    """文件写入输入
    
    Attributes:
        path: 文件路径
        content: 文件内容
        append: 是否追加模式（默认 False，覆盖写入）
    """

    path: str = Field(description="文件路径")
    content: str = Field(description="文件内容")
    append: bool = Field(default=False, description="是否追加模式")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        """验证路径不包含危险组件"""
        if ".." in v:
            raise ValueError("Relative paths with '..' are not allowed")
        return v


@dataclass
class FileWriteOutput:
    """文件写入输出
    
    Attributes:
        path: 写入的文件路径
        success: 是否成功
        bytes_written: 写入的字节数
        error: 错误信息
    """

    path: str
    success: bool
    bytes_written: int = 0
    error: Optional[str] = None


class FileWriteTool(Tool[FileWriteInput, FileWriteOutput, None]):
    """文件写入工具
    
    用于创建新文件或覆盖现有文件。
    
    安全特性:
        - 路径遍历保护
        - 工作目录限制
        - 危险文件类型警告
    
    示例:
        tool = FileWriteTool()
        result = await tool.call(
            FileWriteInput(
                path="output.txt",
                content="Hello, World!"
            ),
            context
        )
    """

    name = "FileWrite"
    aliases = ["write", "create"]
    description_text = "Write content to a file"
    max_result_size_chars = 1_000_000
    input_schema = FileWriteInput

    def get_description(self, input: Optional[FileWriteInput] = None) -> str:
        """获取工具描述"""
        return """Write content to a new file or overwrite an existing file.

Use this tool to:
- Create new source code files
- Generate configuration files
- Write output data
- Save results

For modifying existing files, consider using FileEdit instead."""

    def is_read_only(self, input: FileWriteInput) -> bool:
        """判断是否为只读操作"""
        return False

    def is_destructive(self, input: FileWriteInput) -> bool:
        """判断是否为破坏性操作"""
        return True  # 写入操作都是破坏性的（可能覆盖文件）

    def is_concurrency_safe(self, input: FileWriteInput) -> bool:
        """判断是否可以并发执行"""
        return False  # 需要文件锁

    async def check_permissions(
        self,
        input: FileWriteInput,
        context: ToolContext,
    ) -> PermissionResult:
        """检查权限"""
        # 检查危险文件类型
        dangerous_extensions = [".exe", ".dll", ".so", ".bin", ".sh", ".bat"]
        path = Path(input.path)
        
        if path.suffix.lower() in dangerous_extensions:
            return PermissionResult(
                behavior="deny",
                reason=f"Dangerous file type: {path.suffix}",
            )

        return PermissionResult(behavior="allow")

    async def call(
        self,
        args: FileWriteInput,
        context: ToolContext,
        can_use_tool: callable,
        parent_message: Optional[str] = None,
        on_progress: Optional[callable] = None,
    ) -> ToolResult[FileWriteOutput]:
        """写入文件"""
        try:
            # 解析路径
            file_path = Path(args.path)
            if not file_path.is_absolute():
                file_path = context.working_directory / file_path

            # 安全检查
            resolved = file_path.resolve()
            if not context.is_path_allowed(resolved):
                return ToolResult(
                    output=FileWriteOutput(
                        path=args.path,
                        success=False,
                        error="Path is outside allowed directories",
                    ),
                )

            # 创建父目录（如果不存在）
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            mode = "a" if args.append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(args.content)

            bytes_written = len(args.content.encode("utf-8"))

            return ToolResult(
                output=FileWriteOutput(
                    path=args.path,
                    success=True,
                    bytes_written=bytes_written,
                ),
            )

        except Exception as e:
            return ToolResult(
                output=FileWriteOutput(
                    path=args.path,
                    success=False,
                    error=str(e),
                ),
            )

    def render_tool_use(self, input: FileWriteInput) -> str:
        """渲染工具使用消息"""
        action = "Appending to" if input.append else "Writing"
        return f"✍️ {action}: `{input.path}` ({len(input.content)} bytes)"

    def render_tool_result(self, output: FileWriteOutput) -> str:
        """渲染工具结果"""
        if output.success:
            return f"✅ Successfully wrote {output.bytes_written} bytes to `{output.path}`"
        return f"❌ Failed to write `{output.path}`: {output.error}"
