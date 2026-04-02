"""Main REPL launcher"""

from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

from .config import GlobalConfig
from .services.api import APIService, QueryOptions
from .tools import get_all_tools, get_tool_by_name
from .tools.context import ToolContext


class REPLLauncher:
    """REPL 启动器
    
    提供交互式的 Claude Code 界面。
    
    支持的命令:
        /clear - 清除对话历史
        /model [name] - 查看或设置模型
        /help - 显示帮助
        /quit - 退出程序
    
    示例:
        config = GlobalConfig.load()
        launcher = REPLLauncher(config)
        await launcher.run()
    """

    def __init__(self, config: GlobalConfig, verbose: bool = False):
        """初始化 REPL
        
        Args:
            config: 全局配置
            verbose: 是否详细输出
        """
        self.config = config
        self.verbose = verbose
        self.console = Console()
        self.api = APIService(api_key=config.auth.api_key)
        self.messages = []
        self.tools = get_all_tools()

    async def run(self):
        """运行 REPL"""
        self._print_welcome()

        while True:
            try:
                # 获取用户输入
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")

                if user_input.lower() in ("quit", "exit", "/q"):
                    self._print_goodbye()
                    break
                elif user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # 添加到消息历史
                self.messages.append({"role": "user", "content": user_input})

                # 查询并响应
                await self._query_and_respond()

            except KeyboardInterrupt:
                self.console.print(
                    "\n[yellow]Interrupted. Type /quit to exit.[/yellow]"
                )
            except EOFError:
                break

    async def _handle_command(self, command: str):
        """处理斜杠命令
        
        Args:
            command: 命令字符串
        """
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/clear":
            self.messages.clear()
            self.console.print("[green]Conversation cleared.[/green]")
        elif cmd == "/help":
            self._print_help()
        elif cmd == "/model":
            if args:
                self.config.model.default = args
                self.console.print(f"[green]Model set to: {args}[/green]")
            else:
                self.console.print(
                    f"Current model: {self.config.model.default}"
                )
        elif cmd == "/q":
            self._print_goodbye()
            raise KeyboardInterrupt
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("Type /help for available commands.")

    async def _query_and_respond(self):
        """查询并响应"""
        options = QueryOptions(
            model=self.config.model.default,
            system_prompt=self._build_system_prompt(),
            tools=self._get_tool_schemas(),
        )

        self.console.print("\n[bold purple]Claude[/bold purple] is thinking...\n")

        response_content = ""
        tool_calls = []

        try:
            async for event in self.api.query_model(self.messages, options):
                if event.type == "content_block_delta":
                    text = event.data.get("delta", {}).get("text", "")
                    if text:
                        response_content += text
                        self.console.print(text, end="", markup=False)
                elif event.type == "tool_use":
                    tool_data = event.data
                    tool_calls.append(tool_data)
                    
                    if self.verbose:
                        self.console.print(
                            f"\n[yellow]Tool: {tool_data.get('name')}[/yellow]"
                        )

            self.console.print()

            # 添加助手响应到历史
            if response_content or tool_calls:
                self.messages.append({
                    "role": "assistant",
                    "content": response_content,
                    "tool_calls": tool_calls,
                })

            # 处理工具调用
            if tool_calls:
                await self._execute_tool_calls(tool_calls)

        except Exception as e:
            self.console.print(f"\n[red]Error: {e}[/red]")
            if self.verbose:
                import traceback
                traceback.print_exc()

    async def _execute_tool_calls(self, tool_calls: list[dict]):
        """执行工具调用
        
        Args:
            tool_calls: 工具调用列表
        """
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_input = tool_call.get("input", {})
            tool_id = tool_call.get("id")

            # 查找工具
            tool = get_tool_by_name(tool_name)
            if not tool:
                self.console.print(f"[red]Unknown tool: {tool_name}[/red]")
                continue

            # 显示工具使用
            try:
                input_obj = tool.input_schema(**tool_input)
                self.console.print(f"\n[cyan]{tool.render_tool_use(input_obj)}[/cyan]")
            except Exception:
                self.console.print(f"\n[cyan]Using {tool_name}...[/cyan]")

            # 执行工具
            context = self._create_context()
            
            try:
                result = await tool.call(
                    tool.input_schema(**tool_input),
                    context=context,
                    can_use_tool=lambda: True,
                    on_progress=lambda msg: self.console.print(f"  {msg}"),
                )

                # 显示结果
                self.console.print(
                    f"\n[green]{tool.render_tool_result(result.output)}[/green]"
                )

                # 添加工具结果到消息
                self.messages.append({
                    "role": "tool",
                    "tool_use_id": tool_id,
                    "content": str(result.output),
                })

            except Exception as e:
                self.console.print(f"[red]Tool execution failed: {e}[/red]")
                
                # 添加错误结果
                self.messages.append({
                    "role": "tool",
                    "tool_use_id": tool_id,
                    "content": f"Error: {e}",
                })

    def _print_welcome(self):
        """打印欢迎信息"""
        welcome = """
# Welcome to Python Claude Code!

Type your message or use these commands:
- `/clear` - Clear conversation
- `/model <name>` - Change model  
- `/help` - Show help
- `/quit` or Ctrl+D - Exit
"""
        self.console.print(Markdown(welcome))

    def _print_help(self):
        """打印帮助"""
        help_text = """
## Available Commands

- `/clear` - Clear conversation history
- `/model <name>` - Set the model to use
- `/help` - Show this help message
- `/quit` - Exit the program

## Tips

- Be specific about what you want
- Include file paths when relevant
- Use natural language for complex tasks
- You can ask Claude to use tools like Bash, FileRead, etc.
"""
        self.console.print(Markdown(help_text))

    def _print_goodbye(self):
        """打印告别信息"""
        self.console.print("[blue]Goodbye![/blue]")

    def _build_system_prompt(self) -> str:
        """构建系统提示词
        
        Returns:
            系统提示词
        """
        return """You are a helpful AI coding assistant. You can:

1. Answer questions about code and programming
2. Help debug and fix issues
3. Write new code and modify existing code
4. Execute shell commands (with user permission)
5. Read and write files (with user permission)

Always be helpful, accurate, and explain your reasoning.

When using tools:
- Explain what you're about to do before doing it
- Show the results clearly
- Handle errors gracefully"""

    def _get_tool_schemas(self) -> list[dict]:
        """获取工具 Schema 列表
        
        Returns:
            工具 Schema 列表
        """
        return [
            {
                "name": tool.name,
                "description": tool.get_description(),
                "input_schema": tool.to_json_schema(),
            }
            for tool in self.tools
        ]

    def _create_context(self) -> ToolContext:
        """创建工具上下文
        
        Returns:
            工具上下文
        """
        from pathlib import Path

        return ToolContext(
            working_directory=Path.cwd(),
            permission_mode=self.config.permissions.mode,
            settings=self.config.features,
            messages=self.messages.copy(),
        )
