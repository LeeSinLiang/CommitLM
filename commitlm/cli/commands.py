"""Command-line interface for AI docs generator."""

import sys
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config.settings import init_settings, CPU_MODEL_CONFIGS
from ..core.llm_client import LLMClientError, get_available_models

console = Console()


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.option("--config", type=click.Path(), help="Path to configuration file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def main(
    ctx: click.Context, version: bool, config: Optional[str], verbose: bool, debug: bool
):
    """AI-powered documentation generator with git hooks."""
    if version:
        from .. import __version__

        console.print(f"CommitLM v{__version__}")
        sys.exit(0)

    ctx.ensure_object(dict)
    
    # Auto-detect git root for settings loading
    from ..utils.helpers import get_git_root
    
    if config:
        config_path = Path(config)
    else:
        git_root = get_git_root()
        config_path = (git_root / ".commitlm-config.json") if git_root else None
    
    ctx.obj["config_path"] = config_path
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    try:
        settings = init_settings(
            config_path=ctx.obj["config_path"]
        )
        ctx.obj["settings"] = settings
    except Exception as e:
        console.print(f"[red]Error initializing settings: {e}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)

    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@main.command()
@click.option(
    "--provider",
    type=click.Choice(["huggingface", "gemini", "anthropic", "openai"]),
    help="LLM provider to use",
)
@click.option("--model", type=str, help="LLM model to use")
@click.option(
    "--output-dir",
    type=click.Path(),
    default="docs",
    help="Output directory for documentation",
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def init(
    ctx: click.Context,
    provider: Optional[str],
    model: Optional[str],
    output_dir: str,
    force: bool,
):
    """Initialize CommitLM configuration."""
    console.print("[bold blue]🚀 Initializing CommitLM[/bold blue]")

    from ..utils.helpers import get_git_root
    git_root = get_git_root()
    
    if git_root:
        config_path = git_root / ".commitlm-config.json"
        console.print(f"[blue]📁 Detected git repository at: {git_root}[/blue]")
        console.print(f"[blue]💾 Configuration will be saved to: {config_path}[/blue]")
    else:
        config_path = Path(".commitlm-config.json")
        console.print("[yellow]⚠️  No git repository detected. Saving config in current directory.[/yellow]")

    if config_path.exists() and not force:
        if not click.confirm(
            f"Configuration file {config_path} already exists. Overwrite?"
        ):
            console.print("[yellow]Initialization cancelled.[/yellow]")
            return

    if not provider:
        provider = click.prompt(
            "Select LLM provider",
            type=click.Choice(["huggingface", "gemini", "anthropic", "openai"]),
            default="huggingface",
        )

    config_data = {"provider": provider, "documentation": {"output_dir": output_dir}}

    if provider == "huggingface":
        _init_huggingface(config_data, model)
    else:
        _init_api_provider(config_data, provider, model)

    fallback_to_local = click.confirm(
        "\nEnable fallback to a local model if the API fails?", default=False
    )
    config_data["fallback_to_local"] = fallback_to_local

    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        console.print(f"\n[green]✅ Configuration saved to {config_path}[/green]")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("• Run 'commitlm validate' to test the model connection")
        console.print(
            "• Run 'commitlm install-hook' to enable automatic documentation generation"
        )
    except Exception as e:
        console.print(f"[red]❌ Failed to save configuration: {e}[/red]")
        sys.exit(1)


def _init_huggingface(config_data: dict, model: Optional[str]):
    """Initialize HuggingFace configuration."""
    available_models = get_available_models()
    if not available_models:
        console.print("[red]❌ No HuggingFace models available![/red]")
        sys.exit(1)

    console.print("\n[bold]Available Local Models:[/bold]")
    model_table = Table(show_header=True, header_style="bold magenta")
    model_table.add_column("Model", style="cyan", no_wrap=True)
    model_table.add_column("Description")
    for model_key in available_models:
        model_info = CPU_MODEL_CONFIGS[model_key]
        model_table.add_row(model_key, model_info["description"])
    console.print(model_table)

    if not model:
        model = click.prompt(
            "Select model", type=click.Choice(available_models), default="qwen2.5-coder-1.5b"
        )
    config_data["model"] = model
    config_data["huggingface"] = {"model": model}


def _init_api_provider(config_data: dict, provider: str, model: Optional[str]):
    """Initialize API provider configuration."""
    api_key = click.prompt(f"Enter {provider.capitalize()} API key", hide_input=True)
    
    if not model:
        default_models = {
            "gemini": "gemini-1.5-flash",
            "anthropic": "claude-3-haiku-20240307",
            "openai": "gpt-4o",
        }
        model = click.prompt(f"Enter {provider.capitalize()} model", default=default_models.get(provider, ""))
        
    config_data["model"] = model
    config_data[provider] = {"model": model, "api_key": api_key}


@main.command()
@click.pass_context
def validate(ctx: click.Context):
    """Validate current configuration and test LLM connection."""
    console.print("[bold blue]🔍 Validating Configuration[/bold blue]")

    settings = ctx.obj["settings"]

    validation_table = Table(show_header=True, header_style="bold magenta")
    validation_table.add_column("Check", style="cyan")
    validation_table.add_column("Status", justify="center")
    validation_table.add_column("Details")

    try:
        validation_table.add_row("Configuration", "✅", "Loaded")
    except Exception as e:
        validation_table.add_row("Configuration", "❌", str(e))
        console.print(validation_table)
        sys.exit(1)

    try:
        from ..core.llm_client import create_llm_client

        with console.status("[bold green]Connecting to LLM..."):
            client = create_llm_client(settings)

        validation_table.add_row(
            "LLM Provider", "✅", f"Connected to {settings.provider}"
        )

        with console.status("[bold green]Generating test response..."):
            test_response = client.generate_text("Say 'Hello from CommitLM!'", max_tokens=50)

        if test_response:
            validation_table.add_row(
                "Model Connection", "✅", f"Using model: {settings.model}"
            )
            validation_table.add_row(
                "Test Response",
                "✅",
                (
                    test_response[:50].replace('\n', ' ') + "..."
                    if len(test_response) > 50
                    else test_response.replace('\n', ' ')
                ),
            )
        else:
            validation_table.add_row("Model Connection", "❌", "No response received")

    except LLMClientError as e:
        validation_table.add_row("Model Connection", "❌", str(e))
    except Exception as e:
        validation_table.add_row("Model Connection", "❌", f"Unexpected error: {e}")

    output_dir = Path(settings.documentation.output_dir)
    if output_dir.exists():
        validation_table.add_row("Output Directory", "✅", f"Exists: {output_dir}")
    else:
        validation_table.add_row(
            "Output Directory", "⚠️", f"Will be created: {output_dir}"
        )

    console.print(validation_table)

    console.print("\n[bold]Current Configuration:[/bold]")
    active_config = settings.get_active_llm_config()
    config_panel = Panel(
        f"Provider: {settings.provider}\n"
        f"Model: {settings.model}\n"
        f"Max Tokens: {active_config.max_tokens}\n"
        f"Temperature: {active_config.temperature}\n"
        f"Output Directory: {settings.documentation.output_dir}",
        title="Settings",
        border_style="blue",
    )
    console.print(config_panel)


@main.command()
@click.pass_context
def status(ctx: click.Context):
    """Show current status and configuration."""
    settings = ctx.obj["settings"]
    console.print("[bold blue]📊 CommitLM Status[/bold blue]")

    status_table = Table(show_header=True, header_style="bold magenta")
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", justify="center")
    status_table.add_column("Details")

    status_table.add_row("LLM Provider", "✅", settings.provider)
    status_table.add_row("Active Model", "✅", settings.model)

    if settings.provider == "huggingface":
        available_models = get_available_models()
        if available_models:
            status_table.add_row(
                "HuggingFace", "✅ Available", f"{len(available_models)} models ready"
            )
        else:
            status_table.add_row(
                "HuggingFace", "❌ Not installed", "Run: pip install transformers torch"
            )
        hf_config = settings.get_active_llm_config()
        device_info = hf_config.get_device_info()
        device_status = f"{device_info['device'].upper()} ({device_info['acceleration']})"
        if device_info.get("gpu_name"):
            device_status += f" - {device_info['gpu_name']}"
        status_table.add_row("Hardware", "🚀", device_status)

    config_file = Path(".commitlm-config.json")
    if config_file.exists():
        status_table.add_row("Configuration", "✅", str(config_file.resolve()))
    else:
        status_table.add_row(
            "Configuration", "❌", "No config file found (run 'commitlm init')"
        )

    console.print(status_table)


@main.command()
@click.argument("diff_content", required=False)
@click.option(
    "--file", "file_path", type=click.Path(exists=True), help="Read diff from file"
)
@click.option("--output", type=click.Path(), help="Save documentation to file")
@click.option(
    "--provider",
    type=click.Choice(["huggingface", "gemini", "anthropic", "openai"]),
    help="Override LLM provider for this generation",
)
@click.option("--model", type=str, help="Override LLM model for this generation")
@click.pass_context
def generate(
    ctx: click.Context,
    diff_content: Optional[str],
    file_path: Optional[str],
    output: Optional[str],
    provider: Optional[str],
    model: Optional[str],
):
    """Generate documentation from git diff content."""
    settings = ctx.obj["settings"]

    if file_path:
        with open(file_path, "r") as f:
            diff_content = f.read()
    elif not diff_content and not sys.stdin.isatty():
        diff_content = sys.stdin.read()

    if not diff_content:
        console.print(
            "[red]❌ Please provide diff content via argument, file, or stdin.[/red]"
        )
        sys.exit(1)

    try:
        from ..core.llm_client import create_llm_client
        from ..config.settings import Settings

        runtime_settings = settings
        if provider or model:
            settings_dict = runtime_settings.model_dump()
            if provider:
                settings_dict["provider"] = provider
            if model:
                settings_dict["model"] = model
            runtime_settings = Settings(**settings_dict)

        console.print(
            f"[blue]Using provider: {runtime_settings.provider}, model: {runtime_settings.model}[/blue]"
        )

        with console.status("[bold green]Generating documentation..."):
            client = create_llm_client(runtime_settings)
            documentation = client.generate_documentation(diff_content)

        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(documentation)
            console.print(f"[green]Documentation saved to {output_path}[/green]")
        else:
            console.print("\n[bold]Generated Documentation:[/bold]")
            console.print(
                Panel(documentation, title="Documentation", border_style="green")
            )

    except Exception as e:
        console.print(f"[red]Failed to generate documentation: {e}[/red]")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


@main.group()
@click.pass_context
def config(ctx: click.Context):
    """Manage configuration settings."""
    pass


@config.command("get")
@click.argument("key", required=False)
@click.pass_context
def config_get(ctx: click.Context, key: Optional[str]):
    """Get a configuration value."""
    settings = ctx.obj["settings"]
    if key:
        keys = key.split('.')
        value = settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = getattr(value, k, None)
            if value is None:
                console.print(f"[red]Configuration key '{key}' not found.[/red]")
                return
        console.print(value)
    else:
        console.print(settings.model_dump_json(indent=2))


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str):
    """Set a configuration value."""
    settings = ctx.obj["settings"]
    keys = key.split('.')
    s = settings
    for k in keys[:-1]:
        s = getattr(s, k)

    # Try to convert value to the correct type
    try:
        current_value = getattr(s, keys[-1])
        if isinstance(current_value, bool):
            value = value.lower() in ["true", "1", "yes"]
        elif isinstance(current_value, int):
            value = int(value)
        elif isinstance(current_value, float):
            value = float(value)
    except Exception:
        pass # Keep as string if conversion fails

    setattr(s, keys[-1], value)

    settings.save_to_file(ctx.obj["config_path"])
    console.print(f"[green]Set '{key}' to '{value}'[/green]")


@main.command()
@click.option("--force", is_flag=True, help="Overwrite existing hook")
@click.pass_context
def install_hook(ctx: click.Context, force: bool):
    """Install git post-commit hook for automatic documentation generation."""
    from ..integrations.git_client import get_git_client, GitClientError
    from ..utils.helpers import is_git_repository

    console.print("[bold blue]🔗 Installing Git Post-Commit Hook[/bold blue]")

    from ..utils.helpers import get_git_root
    git_root = get_git_root()
    
    if not git_root:
        console.print("[red]Not in a git repository![/red]")
        console.print("Please run this command from within a git repository.")
        sys.exit(1)

    console.print(f"[blue]📁 Git repository detected at: {git_root}[/blue]")
    
    config_path = git_root / ".commitlm-config.json"
    if not config_path.exists():
        console.print(f"[red]No CommitLM configuration found at: {config_path}[/red]")
        console.print("Please run 'commitlm init' first to set up configuration.")
        console.print("[blue]💡 Tip: Run 'commitlm init' and it will automatically save the config in the right place![/blue]")
        sys.exit(1)
    
    console.print(f"[green]✓ Configuration found at: {config_path}[/green]")

    try:
        # Get git client
        git_client = get_git_client()

        # Check if hook already exists
        hooks_dir = git_client.repo_path / ".git" / "hooks"
        hook_file = hooks_dir / "post-commit"

        if hook_file.exists() and not force:
            if not click.confirm(
                f"Post-commit hook already exists at {hook_file}. Overwrite?"
            ):
                console.print("[yellow]Installation cancelled.[/yellow]")
                return

        # Create temporary hook script
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as tmp_file:
            hook_script_path = Path(tmp_file.name)

        # Generate the hook script
        if git_client.create_post_commit_hook_script(hook_script_path):
            # Install the hook
            if git_client.install_post_commit_hook(hook_script_path):
                console.print(
                    "[green]✅ Post-commit hook installed successfully![/green]"
                )
                console.print(f"Location: {hook_file}")

                # Show what happens next
                console.print("\n[bold]What happens next:[/bold]")
                console.print(
                    "• Every time you make a git commit, documentation will be automatically generated"
                )
                console.print(
                    "• Documentation files will be saved in the 'docs/' directory"
                )
                console.print(
                    "• Files are named with commit hash and timestamp for easy identification"
                )

                console.print("\n[bold]Example workflow:[/bold]")
                console.print("1. Make code changes")
                console.print(
                    "2. Run: git add . && git commit -m 'Your commit message'"
                )
                console.print(
                    "3. AI docs will automatically generate documentation in docs/"
                )
            else:
                console.print("[red]❌ Failed to install post-commit hook[/red]")
                sys.exit(1)
        else:
            console.print("[red]❌ Failed to create hook script[/red]")
            sys.exit(1)

        # Clean up temporary file
        hook_script_path.unlink(missing_ok=True)

    except GitClientError as e:
        console.print(f"[red]❌ Git error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.pass_context
def uninstall_hook(ctx: click.Context):
    """Uninstall git post-commit hook."""
    from ..utils.helpers import is_git_repository, get_git_root

    console.print("[bold blue]🗑️ Uninstalling Git Post-Commit Hook[/bold blue]")

    # Check if we're in a git repository
    git_root = get_git_root()
    if not git_root:
        console.print("[red]❌ Not in a git repository![/red]")
        sys.exit(1)
    
    console.print(f"[blue]📁 Git repository detected at: {git_root}[/blue]")

    try:
        hook_file = git_root / ".git" / "hooks" / "post-commit"

        if not hook_file.exists():
            console.print("[yellow]⚠️  No post-commit hook found[/yellow]")
            return

        # Check if it's our hook (look for AI Docs signature)
        with open(hook_file, "r") as f:
            content = f.read()

        if "CommitLM Generator Post-Commit Hook" not in content:
            console.print(
                "[yellow]⚠️  Existing post-commit hook doesn't appear to be from CommitLM[/yellow]"
            )
            if not click.confirm("Remove it anyway?"):
                console.print("[yellow]Uninstall cancelled.[/yellow]")
                return

        # Remove the hook
        hook_file.unlink()
        console.print("[green]✅ Post-commit hook removed successfully![/green]")

    except Exception as e:
        console.print(f"[red]❌ Failed to uninstall hook: {e}[/red]")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
