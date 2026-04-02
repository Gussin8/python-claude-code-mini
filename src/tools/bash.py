"""Bash tool - Execute shell commands"""

from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field

from .base import Tool, ToolResult, PermissionResult, ToolContext


class BashInput(BaseModel):
    """Bash 工具输入
    
    Attributes:
        command: 要执行的 Shell 命令
        timeout: 超时时间（秒），默认 60 秒
        dangerously_disable_sandbox: 是否禁用沙箱（默认 False）
    """

    command: str = Field(description="要执行的 Shell 命令")
    timeout: Optional[int] = Field(default=60, description="超时时间（秒）")
    dangerously_disable_sandbox: bool = Field(default=False)


@dataclass
class BashOutput:
    """Bash 工具输出
    
    Attributes:
        stdout: 标准输出
        stderr: 错误输出
        exit_code: 退出码
        is_error: 是否有错误
    """

    stdout: str
    stderr: str
    exit_code: int
    is_error: bool = False


class BashTool(Tool[BashInput, BashOutput, str]):
    """Bash 工具 - 执行 Shell 命令
    
    这是最常用的工具之一，允许执行各种 Shell 命令。
    
    安全特性:
        - 危险命令检测（rm -rf, dd, mkfs 等）
        - 超时控制
        - 输出大小限制
        - 权限检查
    
    示例:
        # 简单命令
        tool = BashTool()
        result = await tool.call(
            BashInput(command="ls -la"),
            context
        )
        
        # 带超时
        result = await tool.call(
            BashInput(command="sleep 10", timeout=5),
            context
        )
    """

    name = "Bash"
    aliases = ["shell", "exec"]
    description_text = "Execute shell commands"
    max_result_size_chars = 1_000_000
    input_schema = BashInput

    def get_description(self, input: Optional[BashInput] = None) -> str:
        """获取工具描述"""
        return """Execute a shell command and return the output.

Use this tool to:
- Run build commands (npm install, pip install, make, etc.)
- Execute scripts (python script.py, node app.js, etc.)
- Navigate the filesystem (cd, ls, pwd, etc.)
- Install packages
- Run tests (pytest, npm test, etc.)
- Git operations (git status, git commit, etc.)

Safety notes:
- Destructive commands require explicit confirmation
- Long-running commands should use background mode
- Use timeouts to prevent hanging
- Avoid using interactive commands that require user input"""

    def is_read_only(self, input: BashInput) -> bool:
        """判断是否为只读操作"""
        safe_prefixes = [
            "ls",
            "cat",
            "head",
            "tail",
            "grep",
            "find",
            "pwd",
            "whoami",
            "date",
            "echo",
            "git status",
            "git diff",
            "git log",
        ]
        cmd = input.command.split()[0] if input.command else ""
        return any(cmd.startswith(prefix) for prefix in safe_prefixes)

    def is_destructive(self, input: BashInput) -> bool:
        """判断是否为破坏性操作"""
        dangerous_cmds = [
            "rm",
            "del",
            "dd",
            "mkfs",
            "reboot",
            "shutdown",
            "rmdir",
        ]
        cmd = input.command.split()[0] if input.command else ""
        return cmd in dangerous_cmds or ">" in input.command or "|" in input.command

    def is_concurrency_safe(self, input: BashInput) -> bool:
        """判断是否可以并发执行"""
        return True

    async def check_permissions(
        self,
        input: BashInput,
        context: ToolContext,
    ) -> PermissionResult:
        """检查权限"""
        # 检查黑名单命令
        dangerous_patterns = [
            "rm -rf /",
            "rm -rf ~",
            "dd if=/dev/zero",
            "mkfs",
            "reboot",
            "shutdown",
            ":(){:|:&};:",  # Fork bomb
        ]

        for pattern in dangerous_patterns:
            if pattern in input.command:
                return PermissionResult(
                    behavior="deny",
                    reason=f"Dangerous command detected: {pattern}",
                )

        return PermissionResult(behavior="allow")

    async def call(
        self,
        args: BashInput,
        context: ToolContext,
        can_use_tool: callable,
        parent_message: Optional[str] = None,
        on_progress: Optional[callable] = None,
    ) -> ToolResult[BashOutput]:
        """执行 Bash 命令"""
        import asyncio

        try:
            # 创建子进程
            process = await asyncio.create_subprocess_shell(
                args.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(context.working_directory),
            )

            # 等待完成或超时
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=args.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    output=BashOutput(
                        stdout="",
                        stderr=f"Command timed out after {args.timeout} seconds",
                        exit_code=-1,
                        is_error=True,
                    ),
                )

            # 解码输出
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # 截断大输出
            if len(stdout_str) > self.max_result_size_chars:
                stdout_str = (
                    stdout_str[: self.max_result_size_chars] + "\n... (truncated)"
                )

            return ToolResult(
                output=BashOutput(
                    stdout=stdout_str,
                    stderr=stderr_str,
                    exit_code=process.returncode or 0,
                    is_error=process.returncode != 0,
                ),
            )

        except Exception as e:
            return ToolResult(
                output=BashOutput(
                    stdout="",
                    stderr=str(e),
                    exit_code=-1,
                    is_error=True,
                ),
            )

    def render_tool_use(self, input: BashInput) -> str:
        """渲染工具使用消息"""
        return f"🔨 Running: `{input.command}`"

    def render_tool_result(self, output: BashOutput) -> str:
        """渲染工具结果"""
        lines = []
        if output.stdout:
            lines.append(f"```\n{output.stdout}\n```")
        if output.stderr:
            lines.append(f"**Stderr:**\n```\n{output.stderr}\n```")
        lines.append(f"**Exit code:** {output.exit_code}")
        return "\n".join(lines)
