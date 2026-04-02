"""Tool base classes and interfaces"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, Optional, Callable
from pydantic import BaseModel


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT")
ProgressT = TypeVar("ProgressT")


@dataclass
class ToolResult(Generic[OutputT]):
    """工具执行结果"""

    output: OutputT
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class PermissionResult:
    """权限检查结果"""

    behavior: str  # 'allow' | 'deny' | 'ask'
    updated_input: Optional[dict] = None
    reason: Optional[str] = None


class Tool(ABC, Generic[InputT, OutputT, ProgressT]):
    """工具基类
    
    所有工具都必须继承这个基类并实现其抽象方法。
    
    类型参数:
        InputT: 输入类型，必须是 Pydantic BaseModel
        OutputT: 输出类型
        ProgressT: 进度类型（可选）
    
    示例:
        class BashInput(BaseModel):
            command: str
        
        class BashOutput:
            stdout: str
            stderr: str
            exit_code: int
        
        class BashTool(Tool[BashInput, BashOutput, str]):
            name = 'Bash'
            
            async def call(self, args, context, ...):
                # 实现
                pass
    """

    # === 基础信息 ===
    name: str
    aliases: list[str] = None

    # === Schema 定义 ===
    input_schema: type[BaseModel]
    output_schema: Optional[type[BaseModel]] = None

    # === 元数据 ===
    description_text: str = ""
    max_result_size_chars: int = 1_000_000

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []

    @abstractmethod
    async def call(
        self,
        args: InputT,
        context: "ToolContext",
        can_use_tool: Callable,
        parent_message: Optional[str] = None,
        on_progress: Optional[Callable[[ProgressT], None]] = None,
    ) -> ToolResult[OutputT]:
        """执行工具
        
        Args:
            args: 工具输入参数
            context: 工具执行上下文
            can_use_tool: 权限检查回调
            parent_message: 父消息（可选）
            on_progress: 进度回调（可选）
        
        Returns:
            工具执行结果
        """
        pass

    @abstractmethod
    def get_description(self, input: Optional[InputT] = None) -> str:
        """获取工具描述
        
        这个描述会发送给 AI 模型，帮助它理解何时使用这个工具。
        
        Args:
            input: 可选的输入参数，用于生成动态描述
        
        Returns:
            工具描述文本
        """
        pass

    # === 安全检查 ===

    def is_read_only(self, input: InputT) -> bool:
        """判断是否为只读操作
        
        只读操作通常会自动被允许，因为它们不会修改系统状态。
        
        Args:
            input: 工具输入
        
        Returns:
            True 如果是只读操作
        """
        return False

    def is_destructive(self, input: InputT) -> bool:
        """判断是否为破坏性操作
        
        破坏性操作需要额外的确认和警告。
        
        Args:
            input: 工具输入
        
        Returns:
            True 如果是破坏性操作
        """
        return False

    def is_concurrency_safe(self, input: InputT) -> bool:
        """判断是否可以并发执行
        
        并发安全的工具可以同时运行多个实例。
        
        Args:
            input: 工具输入
        
        Returns:
            True 如果可以并发执行
        """
        return False

    async def check_permissions(
        self,
        input: InputT,
        context: "ToolContext",
    ) -> PermissionResult:
        """检查权限
        
        子类可以重写这个方法来实现特定的权限逻辑。
        
        Args:
            input: 工具输入
            context: 工具上下文
        
        Returns:
            权限检查结果
        """
        return PermissionResult(behavior="allow")

    # === 验证 ===

    async def validate_input(
        self,
        input: dict[str, Any],
        context: "ToolContext",
    ) -> tuple[bool, Optional[str]]:
        """验证输入
        
        使用 Pydantic schema 验证输入数据。
        
        Args:
            input: 输入字典
            context: 工具上下文
        
        Returns:
            (是否有效，错误消息)
        """
        try:
            validated = self.input_schema.model_validate(input)
            return True, None
        except Exception as e:
            return False, str(e)

    # === UI 渲染 ===

    def render_tool_use(self, input: InputT) -> str:
        """渲染工具使用消息
        
        在终端显示工具正在被执行的消息。
        
        Args:
            input: 工具输入
        
        Returns:
            格式化的消息文本
        """
        return f"Using {self.name}: {input}"

    def render_tool_result(self, output: OutputT) -> str:
        """渲染工具结果
        
        在终端显示工具执行的结果。
        
        Args:
            output: 工具输出
        
        Returns:
            格式化的结果文本
        """
        return str(output)

    def to_json_schema(self) -> dict:
        """转换为 JSON Schema
        
        用于发送给 Anthropic API。
        
        Returns:
            JSON Schema 字典
        """
        return self.input_schema.model_json_schema()
