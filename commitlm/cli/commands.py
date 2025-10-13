"""Command-line interface for AI docs generator."""

import sys
import json
from pathlib import Path
from typing import Optional, Union

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config.settings import init_settings, CPU_MODEL_CONFIGS, TaskSettings
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
@click.pass_context
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

    # At this point, provider is guaranteed to be a string
    assert provider is not None, "Provider must be set"

    config_data = {"provider": provider, "documentation": {"output_dir": output_dir}}

    if provider == "huggingface":
        _init_huggingface(config_data, model)
    else:
        _init_api_provider(config_data, provider, model)

    enabled_tasks = click.prompt(
        "Which tasks do you want to enable?",
        type=click.Choice(["commit_message", "doc_generation", "both"]),
        default="both"
    )
    config_data["commit_message_enabled"] = enabled_tasks in ["commit_message", "both"]
    config_data["doc_generation_enabled"] = enabled_tasks in ["doc_generation", "both"]

    if click.confirm("\nDo you want to use different models for specific tasks?", default=False):
        if config_data["commit_message_enabled"] and click.confirm("  - Configure a specific model for commit message generation?", default=True):
            task_config = _prompt_for_task_model(provider)
            config_data["commit_message"] = task_config

        if config_data["doc_generation_enabled"] and click.confirm("  - Configure a specific model for documentation generation?", default=True):
            task_config = _prompt_for_task_model(provider)
            config_data["doc_generation"] = task_config

    fallback_to_local = click.confirm(
        "\nEnable fallback to a local model if the API fails?", default=False
    )
    config_data["fallback_to_local"] = fallback_to_local

    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        console.print(f"\n[green]✅ Configuration saved to {config_path}[/green]")

        # Automatically run install-hook
        console.print("\n[bold]Next Step: Installing Git Hooks[/bold]")
        hook_type = "none"
        if config_data["commit_message_enabled"] and config_data["doc_generation_enabled"]:
            hook_type = "both"
        elif config_data["commit_message_enabled"]:
            hook_type = "message"
        elif config_data["doc_generation_enabled"]:
            hook_type = "docs"
        
        if hook_type != "none":
            ctx.invoke(install_hook, hook_type=hook_type, force=force)

        # Prompt to set up alias
        if config_data["commit_message_enabled"] and click.confirm("\nWould you like to set up a git alias for easier commits?"):
            ctx.invoke(set_alias)
        else:
            console.print("\nTo generate a commit message, you can run:")
            console.print("[bold cyan]git diff --cached | commitlm generate --short-message[/bold cyan]")
            console.print("\nYou can set up an alias for this command later by running:")
            console.print("[bold cyan]commitlm set-alias[/bold cyan]")

    except Exception as e:
        console.print(f"[red]❌ Failed to save configuration: {e}[/red]")
        sys.exit(1)

def _prompt_for_task_model(default_provider: str) -> dict:
    """Helper to prompt for task-specific model config."""
    console.print("") # for spacing
    provider = click.prompt(
        "    Provider for this task",
        type=click.Choice(["huggingface", "gemini", "anthropic", "openai"]),
        default=default_provider,
    )
    model = click.prompt(f"    Model for this task")
    return {"provider": provider, "model": model}

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
            "gemini": "gemini-2.5-flash",
            "anthropic": "claude-3-5-haiku-latest",
            "openai": "gpt-5-mini-2025-08-07",
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
@click.option(
    "--short-message", is_flag=True, help="Generate a short commit message", hidden=True
)
@click.pass_context
def generate(
    ctx: click.Context,
    diff_content: Optional[str],
    file_path: Optional[str],
    output: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    short_message: bool,
):
    """Generate documentation or a short commit message from git diff content."""
    settings = ctx.obj["settings"]

    if file_path:
        with open(file_path, "r") as f:
            diff_content = f.read()
    elif not diff_content and not sys.stdin.isatty():
        diff_content = sys.stdin.read()

    # If diff_content is an empty string (from stdin), treat it as no content.
    if diff_content is not None and not diff_content.strip():
        diff_content = None

    if not diff_content:
        import subprocess
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode == 0:
            console.print("[yellow]⚠️ No changes added to commit (git add ...)[/yellow]")
            sys.exit(1)
        else:
            # If there are staged changes, get the diff and proceed
            diff_proc = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True)
            diff_content = diff_proc.stdout

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

        if short_message:
            client = create_llm_client(runtime_settings, task="commit_message")
            # When generating a short message for the hook, just print the raw text
            message = client.generate_short_message(diff_content)
            print(message)
            sys.exit(0)
        else:
            client = create_llm_client(runtime_settings, task="doc_generation")

        console.print(
            f"[blue]Using provider: {runtime_settings.provider}, model: {runtime_settings.model}[/blue]"
        )

        with console.status("[bold green]Generating documentation..."):
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
def config():
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
    converted_value: Union[str, bool, int, float] = value
    try:
        current_value = getattr(s, keys[-1])
        if isinstance(current_value, bool):
            converted_value = value.lower() in ["true", "1", "yes"]
        elif isinstance(current_value, int):
            converted_value = int(value)
        elif isinstance(current_value, float):
            converted_value = float(value)
    except Exception:
        pass # Keep as string if conversion fails

    setattr(s, keys[-1], converted_value)

    settings.save_to_file(ctx.obj["config_path"])
    console.print(f"[green]Set '{key}' to '{converted_value}'[/green]")

@config.command("change-model")
@click.argument("task", type=click.Choice(["commit_message", "doc_generation", "default"]))
@click.pass_context
def change_model(ctx: click.Context, task: str):
    """Change the model for a specific task."""
    settings = ctx.obj["settings"]
    
    if task == "default":
        provider = click.prompt(
            "Select LLM provider",
            type=click.Choice(["huggingface", "gemini", "anthropic", "openai"]),
            default=settings.provider,
        )
        model = click.prompt("Enter the model name", default=settings.model)
        settings.provider = provider
        settings.model = model
    else:
        task_settings = getattr(settings, task, None)
        if not task_settings:
            task_settings = TaskSettings()
            setattr(settings, task, task_settings)
            
        default_provider = task_settings.provider if task_settings.provider else settings.provider
        default_model = task_settings.model if task_settings.model else settings.model
        
        provider = click.prompt(
            f"Select LLM provider for {task}",
            type=click.Choice(["huggingface", "gemini", "anthropic", "openai"]),
            default=default_provider,
        )
        model = click.prompt(f"Enter the model name for {task}", default=default_model)
        
        task_settings.provider = provider
        task_settings.model = model

    settings.save_to_file(ctx.obj["config_path"])
    console.print(f"[green]✅ Model for '{task}' updated successfully.[/green]")

@main.command("enable-task")
@click.pass_context
def enable_task(ctx: click.Context):
    """Enable or disable tasks and configure their models."""
    settings = ctx.obj["settings"]

    enabled_tasks = click.prompt(
        "Which tasks do you want to enable?",
        type=click.Choice(["commit_message", "doc_generation", "both"]),
        default="both"
    )
    settings.commit_message_enabled = enabled_tasks in ["commit_message", "both"]
    settings.doc_generation_enabled = enabled_tasks in ["doc_generation", "both"]

    if click.confirm("\nDo you want to use different models for the enabled tasks?", default=False):
        if settings.commit_message_enabled and click.confirm("  - Configure a specific model for commit message generation?", default=True):
            task_config = _prompt_for_task_model(settings.provider)
            settings.commit_message = TaskSettings(**task_config)

        if settings.doc_generation_enabled and click.confirm("  - Configure a specific model for documentation generation?", default=True):
            task_config = _prompt_for_task_model(settings.provider)
            settings.doc_generation = TaskSettings(**task_config)
    else:
        # Reset task-specific models if user chooses not to use them
        settings.commit_message = None
        settings.doc_generation = None

    settings.save_to_file(ctx.obj["config_path"])
    console.print("[green]✅ Tasks enabled and configured successfully.[/green]")

    # Also need to reinstall hooks
    console.print("\n[bold]Re-installing Git Hooks based on new settings...[/bold]")
    hook_type = "none"
    if settings.commit_message_enabled and settings.doc_generation_enabled:
        hook_type = "both"
    elif settings.commit_message_enabled:
        hook_type = "message"
    elif settings.doc_generation_enabled:
        hook_type = "docs"
    
    if hook_type != "none":
        ctx.invoke(install_hook, hook_type=hook_type, force=True)
    else:
        # if no tasks are enabled, we should probably uninstall all hooks
        ctx.invoke(uninstall_hook)


@main.command()
@click.argument("hook_type", type=click.Choice(["message", "docs", "both"]), default="both")
@click.option("--force", is_flag=True, help="Overwrite existing hook(s)")
@click.pass_context
def install_hook(ctx: click.Context, hook_type: str, force: bool):
    """Install git hooks for automation."""
    from ..integrations.git_client import get_git_client, GitClientError
    from ..utils.helpers import get_git_root

    console.print("[bold blue]🔗 Installing Git Hooks[/bold blue]")
    git_root = get_git_root()

    if not git_root:
        console.print("[red]Not in a git repository![/red]")
        sys.exit(1)

    console.print(f"[blue]📁 Git repository detected at: {git_root}[/blue]")

    if hook_type in ["message", "both"]:
        _install_prepare_commit_msg_hook(force)

    if hook_type in ["docs", "both"]:
        _install_post_commit_hook(force)

def _install_prepare_commit_msg_hook(force: bool):
    """Install the prepare-commit-msg hook."""
    from ..integrations.git_client import get_git_client, GitClientError
    git_client = get_git_client()
    hooks_dir = git_client.repo_path / ".git" / "hooks"
    hook_file = hooks_dir / "prepare-commit-msg"
    if hook_file.exists() and not force:
        if not click.confirm(f"Hook already exists at {hook_file}. Overwrite?"):
            console.print("[yellow]Installation cancelled.[/yellow]")
            return
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as tmp_file:
        hook_script_path = Path(tmp_file.name)
    if git_client.create_prepare_commit_msg_hook_script(hook_script_path):
        if git_client.install_prepare_commit_msg_hook(hook_script_path):
            console.print(f"[green]✅ prepare-commit-msg hook installed successfully![/green]")
        else:
            console.print("[red]❌ Failed to install prepare-commit-msg hook[/red]")
    else:
        console.print("[red]❌ Failed to create hook script[/red]")
    hook_script_path.unlink(missing_ok=True)

def _install_post_commit_hook(force: bool):
    """Install the post-commit hook."""
    from ..integrations.git_client import get_git_client, GitClientError
    git_client = get_git_client()
    hooks_dir = git_client.repo_path / ".git" / "hooks"
    hook_file = hooks_dir / "post-commit"
    if hook_file.exists() and not force:
        if not click.confirm(f"Hook already exists at {hook_file}. Overwrite?"):
            console.print("[yellow]Installation cancelled.[/yellow]")
            return
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as tmp_file:
        hook_script_path = Path(tmp_file.name)
    if git_client.create_post_commit_hook_script(hook_script_path):
        if git_client.install_post_commit_hook(hook_script_path):
            console.print(f"[green]✅ post-commit hook installed successfully![/green]")
        else:
            console.print("[red]❌ Failed to install post-commit hook[/red]")
    else:
        console.print("[red]❌ Failed to create hook script[/red]")
    hook_script_path.unlink(missing_ok=True)


@main.command()
@click.pass_context
def uninstall_hook(ctx: click.Context):
    """Uninstall git hooks."""
    from ..utils.helpers import get_git_root

    console.print("[bold blue]🗑️ Uninstalling Git Hooks[/bold blue]")

    git_root = get_git_root()
    if not git_root:
        console.print("[red]❌ Not in a git repository![/red]")
        sys.exit(1)

    console.print(f"[blue]📁 Git repository detected at: {git_root}[/blue]")

    _uninstall_hook_file("post-commit", "CommitLM Generator Post-Commit Hook", git_root, ctx.obj.get("debug", False))
    _uninstall_hook_file("prepare-commit-msg", "CommitLM-prepare-commit-msg", git_root, ctx.obj.get("debug", False))


def _uninstall_hook_file(hook_name: str, signature: str, git_root: Path, debug: bool):
    """Helper function to uninstall a single git hook."""
    try:
        hook_file = git_root / ".git" / "hooks" / hook_name

        if not hook_file.exists():
            console.print(f"[yellow]⚠️  No {hook_name} hook found[/yellow]")
            return

        with open(hook_file, "r") as f:
            content = f.read()

        if signature not in content:
            console.print(
                f"[yellow]⚠️  Existing {hook_name} hook doesn't appear to be from CommitLM[/yellow]"
            )
            if not click.confirm("Remove it anyway?"):
                console.print(f"[yellow]Uninstall of {hook_name} cancelled.[/yellow]")
                return

        hook_file.unlink()
        console.print(f"[green]✅ {hook_name} hook removed successfully![/green]")

    except Exception as e:
        console.print(f"[red]❌ Failed to uninstall {hook_name} hook: {e}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.pass_context
def set_alias(ctx: click.Context):
    """Set a git alias for easy commit message generation."""
    console.print("[bold blue]Setting up git alias[/bold blue]")

    try:
        from git import Repo, GitCommandError
        import os
        repo = Repo(os.getcwd(), search_parent_directories=True)
    except (GitCommandError, ImportError):
        console.print("[red]Not in a git repository or gitpython not installed.[/red]")
        sys.exit(1)

    def is_alias_taken(name):
        return repo.config_reader().has_option("alias", name)

    alias_name = click.prompt("Enter a name for the git alias", default="c")

    if is_alias_taken(alias_name):
        if not click.confirm(f"Alias '{alias_name}' is already taken. Overwrite?"):
            console.print("[yellow]Alias setup cancelled.[/yellow]")
            return

    alias_command = "!git diff --cached | commitlm generate --short-message | git commit -F -"
    with repo.config_writer(config_level='global') as cw:
        cw.set_value("alias", alias_name, alias_command)

    console.print(f"[green]✅ Alias '{alias_name}' set successfully.[/green]")
    console.print(f"You can now use 'git {alias_name}' to commit with a generated message.")


if __name__ == "__main__":
    main()
