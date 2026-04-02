"""CLI entry point"""

import asyncio
import typer
from typing import Optional
from pathlib import Path

from .config import GlobalConfig
from .main import REPLLauncher


app = typer.Typer(
    name="python-claude",
    help="Claude Code CLI - AI-powered coding assistant",
    add_completion=False,
)


@app.command()
def main(
    prompt: Optional[str] = typer.Argument(
        None,
        help="The prompt to send to Claude",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Model to use (default: claude-sonnet-4-20250514)",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
    ),
):
    """
    Python Claude Code CLI
    
    Interact with Claude AI for coding assistance, file operations, and more.
    
    Examples:
    
        # Interactive mode
        python-claude
        
        # Single query
        python-claude "Help me fix this bug"
        
        # Specify model
        python-claude -m claude-opus-4-20250514 "Analyze this codebase"
    """
    if version:
        from . import __version__
        typer.echo(f"python-claude version {__version__}")
        raise typer.Exit()

    # 加载配置
    global_config = GlobalConfig.load(config)

    # 覆盖模型
    if model:
        global_config.model.default = model

    # 检查 API key
    if not global_config.auth.api_key:
        typer.echo(
            "Error: ANTHROPIC_API_KEY environment variable not set.\n"
            "Please set it or provide API key in config file.",
            err=True,
        )
        raise typer.Exit(1)

    # 运行
    if prompt:
        # 单次查询模式
        asyncio.run(run_once(prompt, global_config, verbose))
    else:
        # REPL 模式
        launcher = REPLLauncher(global_config, verbose=verbose)
        try:
            asyncio.run(launcher.run())
        except KeyboardInterrupt:
            typer.echo("\nGoodbye!")


async def run_once(prompt: str, config: GlobalConfig, verbose: bool = False):
    """运行单次查询
    
    Args:
        prompt: 用户提示词
        config: 配置
        verbose: 是否详细输出
    """
    from rich.console import Console
    from .services.api import APIService, QueryOptions
    from .tools import get_all_tools

    console = Console()
    api = APIService(api_key=config.auth.api_key)

    options = QueryOptions(
        model=config.model.default,
        system_prompt="You are a helpful coding assistant.",
        tools=[
            {
                "name": tool.name,
                "description": tool.get_description(),
                "input_schema": tool.to_json_schema(),
            }
            for tool in get_all_tools()
        ],
    )

    messages = [{"role": "user", "content": prompt}]

    console.print("\n[bold purple]Claude[/bold purple] is thinking...\n")

    try:
        async for event in api.query_model(messages, options):
            if event.type == "content_block_delta":
                text = event.data.get("delta", {}).get("text", "")
                if text:
                    console.print(text, end="", markup=False)
            elif event.type == "tool_use":
                if verbose:
                    tool_data = event.data
                    console.print(f"\n[yellow]Tool use: {tool_data.get('name')}[/yellow]")
        console.print()
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
