"""CLI interface for MedWriter."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4, UUID

import typer
from loguru import logger
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from src.config.settings import settings
from src.worker.worker import Worker

app = typer.Typer()
console = Console()


class CLIInterface:
    """Interactive CLI for medical article writing."""

    def __init__(self):
        """Initialize CLI interface."""
        self.worker: Worker | None = None
        self.server_process: subprocess.Popen | None = None
        self.running = False
        self.conversation_id: UUID = uuid4()  # New conversation ID for Phase Two

    async def start_mcp_server(self) -> bool:
        """
        Start MCP server in background.

        Returns:
            True if server started successfully
        """
        console.print("\n[cyan]Starting MCP server...[/cyan]")

        try:
            # Ensure logs directory exists
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)

            # Start server as subprocess
            server_script = Path(__file__).parent.parent / "mcp_server" / "server.py"

            # Create log file for server output
            server_log = logs_dir / "mcp_server_stdout.log"
            log_file = open(server_log, "w")

            self.server_process = subprocess.Popen(
                [sys.executable, str(server_script)],
                stdout=log_file,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            )

            # Wait for server to be ready
            console.print("[cyan]Waiting for server to be ready...[/cyan]")
            max_wait = 15
            for i in range(max_wait):
                time.sleep(1)

                # Check if process died
                if self.server_process.poll() is not None:
                    console.print("[red]Server process died[/red]")
                    console.print(f"[yellow]Check logs at: {server_log}[/yellow]")
                    # Read last few lines of log
                    if server_log.exists():
                        with open(server_log) as f:
                            lines = f.readlines()
                            if lines:
                                console.print("[red]Last error:[/red]")
                                for line in lines[-10:]:
                                    console.print(f"  {line.rstrip()}")
                    return False

                # Try to connect using FastMCP Client with HTTP transport
                try:
                    from fastmcp import Client
                    from fastmcp.client.transports import StreamableHttpTransport

                    transport = StreamableHttpTransport(url=settings.mcp_server_url)
                    async with Client(transport) as test_client:
                        # Try to list tools as a connection check
                        tools = await test_client.list_tools()
                        if len(tools) > 0:
                            console.print("[green]✓ MCP server ready[/green]")
                            return True
                except Exception as e:
                    # Silently continue waiting
                    pass

                if i < max_wait - 1:
                    console.print(f"[dim]Waiting... ({i + 1}/{max_wait})[/dim]")

            console.print("[red]Server failed to start in time[/red]")
            console.print(f"[yellow]Check logs at: {server_log}[/yellow]")
            return False

        except Exception as e:
            console.print(f"[red]Error starting server: {e}[/red]")
            import traceback
            traceback.print_exc()
            return False

    async def initialize_worker(self) -> bool:
        """
        Initialize worker.

        Returns:
            True if initialization successful
        """
        console.print(f"\n[cyan]Initializing agent with {settings.llm_provider} ({settings.model_name})...[/cyan]")

        try:
            self.worker = Worker(settings)
            await self.worker.initialize()
            console.print("[green]✓ Worker initialized[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Error initializing worker: {e}[/red]")
            logger.error(f"Worker initialization failed: {e}")
            return False

    def show_help(self) -> None:
        """Display help message."""
        help_text = """
**Available Commands:**

- `/help` - Show this help message
- `/new` - Start a new conversation
- `/clear` - Clear conversation history (in-memory only)
- `/model openai|anthropic` - Switch LLM provider
- `/exit` - Quit application

**Usage:**

Type your message and press Enter to chat with the medical article assistant.
The assistant has access to:
- Web search for medical information
- Medical knowledge database
- Citation generator

**Conversation History:**

Your conversations are automatically saved to the database. Previous messages
in the same conversation are used as context for better responses.

**Example queries:**

- "Write an article about diabetes management"
- "What are the latest treatments for hypertension?"
- "Generate citations for heart disease research"
"""
        console.print(Panel(Markdown(help_text), title="MedWriter Help", border_style="cyan"))

    async def handle_command(self, command: str) -> bool:
        """
        Handle CLI commands.

        Args:
            command: Command string

        Returns:
            True to continue, False to exit
        """
        command = command.strip().lower()

        if command == "/help":
            self.show_help()

        elif command == "/new":
            # Start new conversation
            self.conversation_id = uuid4()
            console.print(f"[green]✓ Started new conversation[/green]")
            console.print(f"[dim]Conversation ID: {self.conversation_id}[/dim]")

        elif command == "/clear":
            if self.worker:
                self.worker.reset_conversation()
                console.print("[green]✓ Conversation history cleared[/green]")
            else:
                console.print("[red]Worker not initialized[/red]")

        elif command.startswith("/model"):
            parts = command.split()
            if len(parts) < 2:
                console.print("[red]Usage: /model openai|anthropic[/red]")
                return True

            provider = parts[1]
            if provider not in ["openai", "anthropic"]:
                console.print("[red]Invalid provider. Use 'openai' or 'anthropic'[/red]")
                return True

            try:
                if self.worker:
                    await self.worker.switch_llm_provider(provider)
                    console.print(f"[green]✓ Switched to {provider}[/green]")
                else:
                    console.print("[red]Worker not initialized[/red]")
            except Exception as e:
                console.print(f"[red]Error switching provider: {e}[/red]")

        elif command == "/exit":
            return False

        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[dim]Type /help for available commands[/dim]")

        return True

    async def chat_loop(self) -> None:
        """Main interactive chat loop."""
        console.print("\n[green]Ready! Type your message or /help for commands.[/green]")
        console.print(f"[dim]Conversation ID: {self.conversation_id}[/dim]")

        while self.running:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]>[/bold cyan]").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    should_continue = await self.handle_command(user_input)
                    if not should_continue:
                        break
                    continue

                # Process query
                if not self.worker:
                    console.print("[red]Worker not initialized[/red]")
                    continue

                console.print()  # Empty line before response

                # Process query with conversation context (Phase Two)
                try:
                    # Show loading indicator
                    console.print("[dim]Processing with conversation history...[/dim]")

                    # Process with context from database
                    response = await self.worker.process_query_with_context(
                        user_input,
                        self.conversation_id
                    )

                    # Display response
                    console.print(response)
                    console.print()  # New line after response

                except Exception as e:
                    console.print(f"\n[red]Error: {e}[/red]")
                    logger.error(f"Error processing query: {e}")

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
                continue

            except EOFError:
                break

    async def run(self) -> None:
        """Run the CLI application."""
        # Show banner
        console.print(Panel(
            "[bold cyan]🏥 Medical Article Writer - Phase Two[/bold cyan]\n"
            "[dim]Conversations saved to database • Previous messages used as context[/dim]",
            border_style="cyan"
        ))

        self.running = True

        try:
            # Start MCP server
            if not await self.start_mcp_server():
                console.print("[red]Failed to start MCP server[/red]")
                return

            # Initialize worker
            if not await self.initialize_worker():
                console.print("[red]Failed to initialize worker[/red]")
                return

            # Run chat loop
            await self.chat_loop()

        except Exception as e:
            console.print(f"\n[red]Fatal error: {e}[/red]")
            logger.exception("Fatal error in CLI")

        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up resources."""
        console.print("\n[cyan]Shutting down...[/cyan]")

        self.running = False

        # Shutdown worker
        if self.worker:
            await self.worker.shutdown()

        # Stop server
        if self.server_process:
            console.print("[cyan]Stopping MCP server...[/cyan]")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

        console.print("[green]Goodbye![/green]")


def setup_logging():
    """Configure logging."""
    # Remove default logger
    logger.remove()

    # Add console logger (INFO and above)
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # Add file logger (all levels)
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="3 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function} | {message}",
    )


@app.command()
def main():
    """Start the MedWriter CLI."""
    # Setup logging
    setup_logging()

    # Run CLI
    cli = CLIInterface()
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.exception("CLI error")
        sys.exit(1)


if __name__ == "__main__":
    app()
