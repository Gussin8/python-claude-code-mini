"""Grep tool - Text search in files"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from .base import Tool, ToolResult, PermissionResult, ToolContext


class GrepInput(BaseModel):
    """Grep 输入
    
    Attributes:
        pattern: 搜索模式（正则表达式或普通文本）
        path: 搜索路径（可选）
        include: 包含的文件模式（可选，如 *.py）
        exclude: 排除的文件模式（可选）
        case_sensitive: 是否区分大小写（默认 False）
        max_results: 最大结果数（默认 100）
    """

    pattern: str = Field(description="搜索模式（正则表达式或普通文本）")
    path: Optional[str] = Field(default=None, description="搜索路径")
    include: Optional[str] = Field(default="*", description="包含的文件模式")
    exclude: Optional[str] = Field(default=None, description="排除的文件模式")
    case_sensitive: bool = Field(default=False, description="是否区分大小写")
    max_results: int = Field(default=100, description="最大结果数")

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v):
        """验证模式不为空"""
        if not v or len(v) < 2:
            raise ValueError("Search pattern must be at least 2 characters")
        return v


@dataclass
class GrepMatch:
    """单个匹配结果
    
    Attributes:
        file: 文件路径
        line_number: 行号
        line: 行的内容
        match: 匹配的文本
    """

    file: str
    line_number: int
    line: str
    match: str


@dataclass
class GrepOutput:
    """Grep 输出
    
    Attributes:
        matches: 匹配列表
        total_matches: 总匹配数
        files_searched: 搜索的文件数
        error: 错误信息
    """

    matches: list[GrepMatch] = field(default_factory=list)
    total_matches: int = 0
    files_searched: int = 0
    error: Optional[str] = None


class GrepTool(Tool[GrepInput, GrepOutput, None]):
    """Grep 工具 - 文本搜索
    
    在文件中搜索文本模式，支持：
    - 正则表达式
    - 大小写控制
    - 文件过滤
    - 结果限制
    
    示例:
        tool = GrepTool()
        result = await tool.call(
            GrepInput(
                pattern="def main",
                include="*.py"
            ),
            context
        )
    """

    name = "Grep"
    aliases = ["search", "find-text"]
    description_text = "Search for text patterns in files"
    max_result_size_chars = 500_000
    input_schema = GrepInput

    def get_description(self, input: Optional[GrepInput] = None) -> str:
        """获取工具描述"""
        return """Search for text patterns in files using regular expressions.

Features:
- Regular expression support
- Case-insensitive by default
- File pattern filtering (include/exclude)
- Result limiting

Use this tool to:
- Find function definitions (def function_name)
- Search for usages of a variable
- Locate specific text in codebase
- Find TODO comments"""

    def is_read_only(self, input: GrepInput) -> bool:
        """判断是否为只读操作"""
        return True

    def is_concurrency_safe(self, input: GrepInput) -> bool:
        """判断是否可以并发执行"""
        return True

    async def call(
        self,
        args: GrepInput,
        context: ToolContext,
        can_use_tool: callable,
        parent_message: Optional[str] = None,
        on_progress: Optional[callable] = None,
    ) -> ToolResult[GrepOutput]:
        """执行 grep 搜索"""
        import re
        import fnmatch
        
        try:
            # 确定搜索路径
            search_path = Path(args.path) if args.path else context.working_directory
            
            if not search_path.is_absolute():
                search_path = context.working_directory / search_path

            # 安全检查
            resolved = search_path.resolve()
            if not context.is_path_allowed(resolved):
                return ToolResult(
                    output=GrepOutput(
                        error="Search path is outside allowed directories",
                    ),
                )

            # 编译正则表达式
            flags = 0 if args.case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(args.pattern, flags)
            except re.error as e:
                return ToolResult(
                    output=GrepOutput(
                        error=f"Invalid regex pattern: {e}",
                    ),
                )

            matches = []
            files_searched = 0
            total_matches = 0

            # 遍历文件
            for root, dirs, files in walk_path(search_path, args.exclude):
                # 检查目录是否在允许范围内
                if not context.is_path_allowed(Path(root)):
                    continue
                
                for filename in files:
                    # 检查文件模式
                    if args.include and not fnmatch.fnmatch(filename, args.include):
                        continue
                    
                    file_path = Path(root) / filename
                    
                    # 跳过不允许的路径
                    if not context.is_path_allowed(file_path):
                        continue
                    
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        files_searched += 1
                        
                        # 逐行搜索
                        for line_num, line in enumerate(content.splitlines(), 1):
                            match = pattern.search(line)
                            if match:
                                total_matches += 1
                                
                                # 限制结果数量
                                if len(matches) < args.max_results:
                                    matches.append(GrepMatch(
                                        file=str(file_path.relative_to(context.working_directory)),
                                        line_number=line_num,
                                        line=line.strip(),
                                        match=match.group(),
                                    ))
                                
                                # 进度回调
                                if on_progress and total_matches % 10 == 0:
                                    on_progress(f"Found {total_matches} matches...")
                                    
                    except (IOError, OSError):
                        # 跳过无法读取的文件
                        continue

            return ToolResult(
                output=GrepOutput(
                    matches=matches,
                    total_matches=total_matches,
                    files_searched=files_searched,
                ),
            )

        except Exception as e:
            return ToolResult(
                output=GrepOutput(
                    error=str(e),
                ),
            )

    def render_tool_use(self, input: GrepInput) -> str:
        """渲染工具使用消息"""
        path_str = f" in {input.path}" if input.path else ""
        include_str = f" (*{input.include})" if input.include and input.include != "*" else ""
        return f"🔍 Searching: `{input.pattern}`{path_str}{include_str}"

    def render_tool_result(self, output: GrepOutput) -> str:
        """渲染工具结果"""
        if output.error:
            return f"❌ Error: {output.error}"
        
        if output.total_matches == 0:
            return "No matches found"
        
        lines = [f"Found {output.total_matches} match(es) in {output.files_searched} file(s):"]
        
        for match in output.matches[:20]:  # 限制显示数量
            lines.append(f"\n{match.file}:{match.line_number}")
            lines.append(f"  {match.line}")
        
        if output.total_matches > 20:
            lines.append(f"\n... and {output.total_matches - 20} more matches")
        
        return "\n".join(lines)


def walk_path(path: Path, exclude: Optional[str] = None):
    """遍历目录树
    
    Args:
        path: 起始路径
        exclude: 排除的模式
    
    Yields:
        (root, dirs, files) 元组
    """
    import fnmatch
    
    excluded_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.idea', '.vscode'}
    
    if exclude:
        excluded_dirs.add(exclude)
    
    for root, dirs, files in path.walk(top_down=True):
        # 过滤排除的目录
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        
        yield root, dirs, files
