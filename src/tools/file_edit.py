"""FileEdit tool - Edit existing files"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from .base import Tool, ToolResult, PermissionResult, ToolContext


class EditOperation(BaseModel):
    """编辑操作
    
    Attributes:
        old_text: 要替换的旧文本（可选，如果指定 range 则不需要）
        new_text: 新文本
        range: 行范围，如 "10-20"（可选）
    """

    old_text: Optional[str] = Field(default=None, description="要替换的旧文本")
    new_text: str = Field(description="新文本")
    range: Optional[str] = Field(default=None, description="行范围，如 '10-20'")


class FileEditInput(BaseModel):
    """文件编辑输入
    
    Attributes:
        path: 文件路径
        edits: 编辑操作列表
        new_file: 是否创建新文件
    """

    path: str = Field(description="文件路径")
    edits: list[EditOperation] = Field(description="编辑操作列表", min_length=1)
    new_file: bool = Field(default=False, description="是否创建新文件")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        """验证路径不包含危险组件"""
        if ".." in v:
            raise ValueError("Relative paths with '..' are not allowed")
        return v


@dataclass
class FileEditOutput:
    """文件编辑输出
    
    Attributes:
        path: 编辑的文件路径
        success: 是否成功
        new_file_created: 是否创建了新文件
        error: 错误信息
    """

    path: str
    success: bool
    new_file_created: bool = False
    error: Optional[str] = None


class FileEditTool(Tool[FileEditInput, FileEditOutput, None]):
    """文件编辑工具
    
    用于编辑现有文件，支持：
    - 文本替换
    - 行范围编辑
    - 多次编辑操作
    
    安全特性:
        - 路径遍历保护
        - 工作目录限制
        - 旧文本匹配验证
    
    示例:
        tool = FileEditTool()
        result = await tool.call(
            FileEditInput(
                path="src/main.py",
                edits=[
                    EditOperation(
                        old_text="def hello():",
                        new_text="def hello_world():"
                    )
                ]
            ),
            context
        )
    """

    name = "FileEdit"
    aliases = ["edit", "modify"]
    description_text = "Edit file contents"
    max_result_size_chars = 1_000_000
    input_schema = FileEditInput

    def get_description(self, input: Optional[FileEditInput] = None) -> str:
        """获取工具描述"""
        return """Edit an existing file.

Supports:
- Text replacement (specify old_text and new_text)
- Line range editing (specify range like "10-20")
- Multiple edits in one operation

Use this tool to:
- Fix bugs in code
- Update configurations
- Modify documentation
- Refactor code

For creating new files, use FileWrite instead."""

    def is_read_only(self, input: FileEditInput) -> bool:
        """判断是否为只读操作"""
        return False

    def is_destructive(self, input: FileEditInput) -> bool:
        """判断是否为破坏性操作"""
        return True

    def is_concurrency_safe(self, input: FileEditInput) -> bool:
        """判断是否可以并发执行"""
        return False  # 需要文件锁

    async def check_permissions(
        self,
        input: FileEditInput,
        context: ToolContext,
    ) -> PermissionResult:
        """检查权限"""
        return PermissionResult(behavior="allow")

    async def call(
        self,
        args: FileEditInput,
        context: ToolContext,
        can_use_tool: callable,
        parent_message: Optional[str] = None,
        on_progress: Optional[callable] = None,
    ) -> ToolResult[FileEditOutput]:
        """编辑文件"""
        try:
            # 解析路径
            file_path = Path(args.path)
            if not file_path.is_absolute():
                file_path = context.working_directory / file_path

            # 安全检查
            resolved = file_path.resolve()
            if not context.is_path_allowed(resolved):
                return ToolResult(
                    output=FileEditOutput(
                        path=args.path,
                        success=False,
                        error="File is outside allowed directories",
                    ),
                )

            # 创建新文件（如果指定）
            if args.new_file and not file_path.exists():
                file_path.touch()
                new_file_created = True
            else:
                new_file_created = False

            # 读取当前内容
            if not file_path.exists():
                return ToolResult(
                    output=FileEditOutput(
                        path=args.path,
                        success=False,
                        error=f"File does not exist: {args.path}",
                    ),
                )

            content = file_path.read_text(encoding="utf-8")
            original_content = content

            # 应用编辑
            for i, edit in enumerate(args.edits):
                if edit.range:
                    # 按范围编辑
                    try:
                        start, end = map(int, edit.range.split("-"))
                        lines = content.splitlines()
                        lines[start - 1 : end] = [edit.new_text]
                        content = "\n".join(lines)
                    except ValueError:
                        return ToolResult(
                            output=FileEditOutput(
                                path=args.path,
                                success=False,
                                error=f"Invalid range format: {edit.range}",
                            ),
                        )
                elif edit.old_text:
                    # 文本替换
                    if edit.old_text not in content:
                        return ToolResult(
                            output=FileEditOutput(
                                path=args.path,
                                success=False,
                                error=f"Old text not found: {edit.old_text[:50]}...",
                            ),
                        )
                    content = content.replace(edit.old_text, edit.new_text, 1)
                else:
                    return ToolResult(
                        output=FileEditOutput(
                            path=args.path,
                            success=False,
                            error="Either old_text or range must be specified",
                        ),
                    )

                # 进度回调
                if on_progress:
                    on_progress(f"Applied edit {i + 1}/{len(args.edits)}")

            # 写回文件
            file_path.write_text(content, encoding="utf-8")

            return ToolResult(
                output=FileEditOutput(
                    path=args.path,
                    success=True,
                    new_file_created=new_file_created,
                ),
            )

        except Exception as e:
            return ToolResult(
                output=FileEditOutput(
                    path=args.path,
                    success=False,
                    error=str(e),
                ),
            )

    def render_tool_use(self, input: FileEditInput) -> str:
        """渲染工具使用消息"""
        return f"✏️ Editing: `{input.path}` ({len(input.edits)} edits)"

    def render_tool_result(self, output: FileEditOutput) -> str:
        """渲染工具结果"""
        if output.success:
            msg = f"✅ Successfully edited `{output.path}`"
            if output.new_file_created:
                msg += " (new file created)"
            return msg
        return f"❌ Failed to edit `{output.path}`: {output.error}"
