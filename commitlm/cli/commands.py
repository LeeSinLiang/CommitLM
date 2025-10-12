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
    "--model",
    type=click.Choice(
        [
            "phi-3-mini-128k",
            "tinyllama",
            "qwen2.5-coder-1.5b",
        ]
    ),
    help="HuggingFace model to use",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="docs",
    help="Output directory for documentation",
)
@click.option(
    "--memory-optimization/--no-memory-optimization",
    default=True,
    help="Enable memory optimizations for better compatibility (default: enabled)",
)
@click.option(
    "--max-tokens",
    type=int,
    help="Maximum tokens for model output (uses model default if not specified)",
)
@click.option(
    "--enable-yarn/--disable-yarn",
    default=False,
    help="Enable YaRN for extended context length (Qwen models only)",
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def init(
    ctx: click.Context,
    model: Optional[str],
    output_dir: str,
    memory_optimization: bool,
    max_tokens: Optional[int],
    enable_yarn: bool,
    force: bool,
):
    """Initialize CommitLM configuration."""
    console.print("[bold blue]🚀 Initializing CommitLM[/bold blue]")
    
    # Auto-detect git repository root and save config there
    from ..utils.helpers import get_git_root
    git_root = get_git_root()
    
    if git_root:
        config_path = git_root / ".commitlm-config.json"
        console.print(f"[blue]📁 Detected git repository at: {git_root}[/blue]")
        console.print(f"[blue]💾 Configuration will be saved to: {config_path}[/blue]")
    else:
        config_path = Path(".commitlm-config.json")
        console.print("[yellow]⚠️  No git repository detected. Saving config in current directory.[/yellow]")
        console.print("[yellow]   Note: You'll need to run this from your git repository root for git hooks to work.[/yellow]")

    if config_path.exists() and not force:
        if not click.confirm(
            f"Configuration file {config_path} already exists. Overwrite?"
        ):
            console.print("[yellow]Initialization cancelled.[/yellow]")
            return

    available_models = get_available_models()
    if not available_models:
        console.print("[red]❌ No HuggingFace models available![/red]")
        console.print("Please install the required packages:")
        console.print("  pip install transformers torch accelerate")
        sys.exit(1)

    console.print("\n[bold]Available Local Models:[/bold]")
    model_table = Table(show_header=True, header_style="bold magenta")
    model_table.add_column("Model", style="cyan", no_wrap=True)
    model_table.add_column("Size", justify="center")
    model_table.add_column("RAM Usage", justify="center")
    model_table.add_column("Speed", justify="center")
    model_table.add_column("Description")

    for model_key in available_models:
        model_info = CPU_MODEL_CONFIGS[model_key]
        model_table.add_row(
            model_key.title().replace("-", " "),
            model_info["size"],
            f'Optimized: {model_info["memory_optimized"]["ram_usage"]} Full: {model_info["full_performance"]["ram_usage"]}' if "memory_optimized" in model_info.keys() else model_info["ram_usage"],
            model_info["speed"],
            model_info["description"],
        )

    console.print(model_table)

    if not model:
        console.print(
            "\n[bold]Recommended:[/bold] [green]qwen2.5-coder-1.5b[/green] - Best overall performance to speed ratio"
        )
        model = click.prompt(
            "Select model", type=click.Choice(available_models), default="qwen2.5-coder-1.5b"
        )

    if not model:
        console.print("[red]❌ No model selected[/red]")
        sys.exit(1)

    model_info = CPU_MODEL_CONFIGS.get(model)
    if not model_info:
        console.print(f"[red]❌ Invalid model: {model}[/red]")
        sys.exit(1)

    console.print(f"\n[bold]Selected Model:[/bold] {model}")
    console.print(f"[dim]• Size: {model_info['size']} parameters[/dim]")
    if memory_optimization and model in ["qwen2.5-coder-1.5b", "phi-3-mini-128k"]:
        console.print(f"[dim]• RAM Usage: {model_info['memory_optimized']['ram_usage']}[/dim]")
    elif memory_optimization == False and model in ["qwen2.5-coder-1.5b", "phi-3-mini-128k"]:
        console.print(f"[dim]• RAM Usage: {model_info['full_performance']['ram_usage']}[/dim]")
    else:
        console.print(f"[dim]• RAM Usage: {model_info['ram_usage']}[/dim]")
    console.print(f"[dim]• Speed: {model_info['speed']}[/dim]")
    console.print(f"[dim]• Description: {model_info['description']}[/dim]")

    # Show memory optimization info
    optimization_mode = (
        "Memory Optimized (recommended for most systems)"
        if memory_optimization
        else "Full Performance (requires more RAM)"
    )
    console.print(f"[blue]ℹ️  Optimization Mode: {optimization_mode}[/blue]")
    if memory_optimization and model in ["qwen2.5-coder-1.5b", "phi-3-mini-128k"]:
        optimized_info = model_info.get("memory_optimized", {})
        console.print(
            f"[dim]• Optimized RAM Usage: {optimized_info.get('ram_usage', 'N/A')}[/dim]"
        )

    # Interactive YaRN prompt (only for Qwen models and if not specified via CLI)
    supports_yarn = model_info.get("supports_yarn", False)
    if supports_yarn and "qwen" in model.lower() and enable_yarn is False:  # Only prompt if not set via CLI
        console.print(f"\n[bold]🧶 YaRN (Extended Context) Options:[/bold]")
        console.print("[dim]YaRN enables extended context length for processing larger git diffs.[/dim]")
        
        yarn_config = model_info.get("yarn_config", {})
        base_context = model_info.get("base_context_length", 32768)
        
        if memory_optimization:
            memory_config = model_info.get("memory_optimized", {})
            extended_context = memory_config.get("extended_context", 65536)
        else:
            performance_config = model_info.get("full_performance", {})
            extended_context = performance_config.get("extended_context", 131072)
        
        console.print(f"[dim]• Default context: {base_context:,} tokens[/dim]")
        console.print(f"[dim]• Extended context: {extended_context:,} tokens[/dim]")
        
        enable_yarn = click.confirm(
            "Enable YaRN for extended context length?", 
            default=False
        )
    
    # Interactive max tokens prompt
    if max_tokens is None:  # Only prompt if not specified via CLI
        console.print(f"\n[bold]📝 Output Length Configuration:[/bold]")
        
        if enable_yarn and supports_yarn:
            yarn_config = model_info.get("yarn_config", {})
            if memory_optimization:
                memory_config = model_info.get("memory_optimized", {})
                default_max_tokens = 512 
                extended_context = memory_config.get("extended_context", 65536)
            else:
                performance_config = model_info.get("full_performance", {})
                default_max_tokens = 1024
                extended_context = performance_config.get("extended_context", 131072)
            console.print(f"[dim]YaRN enabled - can handle up to {extended_context:,} input tokens[/dim]")
        else:
            default_max_tokens = model_info["max_tokens"]
            base_context = model_info.get("base_context_length", 32768)
            console.print(f"[dim]Standard context - can handle up to {base_context:,} input tokens[/dim]")
        
        console.print(f"[dim]• Recommended: {default_max_tokens} tokens[/dim]")
        console.print("[dim]• Higher values = more detailed docs but slower generation[/dim]")
        
        max_tokens_input = click.prompt(
            f"Max output tokens",
            type=int,
            default=default_max_tokens,
            show_default=True
        )
        effective_max_tokens = max_tokens_input
    else:
        effective_max_tokens = max_tokens
    
    # Check YaRN availability and display final info
    if enable_yarn and not supports_yarn:
        console.print(f"[yellow]⚠️  YaRN not supported by {model}. Ignoring YaRN setting.[/yellow]")
        enable_yarn = False
    elif enable_yarn and supports_yarn:
        yarn_config = model_info.get("yarn_config", {})
        if memory_optimization:
            memory_config = model_info.get("memory_optimized", {})
            extended_context = memory_config.get("extended_context", 65536)
        else:
            performance_config = model_info.get("full_performance", {})  
            extended_context = performance_config.get("extended_context", 131072)
        console.print(f"[green]🧶 YaRN enabled! Extended context: {extended_context:,} tokens[/green]")
    
    # Create configuration
    config_data = {
        "model": model,
        "huggingface": {
            "model": model,
            "max_tokens": effective_max_tokens,
            "temperature": model_info["temperature"],
            "device": "auto",  # Auto-detect best available device
            "torch_dtype": "float32",
            "memory_optimization": memory_optimization,
            "enable_yarn": enable_yarn,
        },
        "documentation": {"output_dir": output_dir},
    }
    
    # Display final configuration summary
    console.print(f"\n[blue]ℹ️  Final Configuration:[/blue]")
    console.print(f"[blue]• Max output tokens: {effective_max_tokens}[/blue]")
    if enable_yarn:
        if memory_optimization:
            memory_config = model_info.get("memory_optimized", {})
            extended_context = memory_config.get("extended_context", 65536)
        else:
            performance_config = model_info.get("full_performance", {})
            extended_context = performance_config.get("extended_context", 131072)
        console.print(f"[blue]• Extended input context: {extended_context:,} tokens (YaRN)[/blue]")
    else:
        base_context = model_info.get("base_context_length", 32768)
        console.print(f"[blue]• Standard input context: {base_context:,} tokens[/blue]")

    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)

        console.print(f"\n[green]✅ Configuration saved to {config_path}[/green]")

        console.print("\n[bold]Next Steps:[/bold]")
        console.print("• Run 'commitlm validate' to test the model connection")
        console.print(
            "• Run 'commitlm install-hook' to enable automatic documentation generation"
        )
        console.print(
            "• The first time you use a model, it will be downloaded automatically"
        )

    except Exception as e:
        console.print(f"[red]❌ Failed to save configuration: {e}[/red]")
        sys.exit(1)


@main.command()
@click.pass_context
def validate(ctx: click.Context):
    """Validate current configuration and test LLM connection."""
    console.print("[bold blue]🔍 Validating Configuration[/bold blue]")

    settings = ctx.obj["settings"]

    # Validation table
    validation_table = Table(show_header=True, header_style="bold magenta")
    validation_table.add_column("Check", style="cyan")
    validation_table.add_column("Status", justify="center")
    validation_table.add_column("Details")

    # Check configuration
    try:
        settings.model_validate(settings.model_dump())
        validation_table.add_row("Configuration", "✅", "Valid")
    except Exception as e:
        validation_table.add_row("Configuration", "❌", str(e))
        console.print(validation_table)
        sys.exit(1)

    # Check HuggingFace availability
    available_models = get_available_models()

    if available_models:
        validation_table.add_row("HuggingFace Package", "✅", "transformers installed")
    else:
        validation_table.add_row(
            "HuggingFace Package", "❌", "transformers not installed"
        )
        console.print(validation_table)
        sys.exit(1)

    # Test LLM connection
    try:
        from ..core.llm_client import create_llm_client

        client = create_llm_client(settings)

        # Simple test
        test_response = client.generate_text("Say 'Hello from CommitLM!'", max_tokens=50)

        if test_response:
            validation_table.add_row(
                "Model Connection", "✅", f"Connected to {settings.model}"
            )
            validation_table.add_row(
                "Test Response",
                "✅",
                (
                    test_response[:50] + "..."
                    if len(test_response) > 50
                    else test_response
                ),
            )
        else:
            validation_table.add_row("Model Connection", "❌", "No response received")

    except LLMClientError as e:
        validation_table.add_row("Model Connection", "❌", str(e))
    except Exception as e:
        validation_table.add_row("Model Connection", "❌", f"Unexpected error: {e}")

    # Check output directory
    output_dir = Path(settings.documentation.output_dir)
    if output_dir.exists():
        validation_table.add_row("Output Directory", "✅", f"Exists: {output_dir}")
    else:
        validation_table.add_row(
            "Output Directory", "⚠️", f"Will be created: {output_dir}"
        )

    console.print(validation_table)

    # Configuration summary
    console.print("\n[bold]Current Configuration:[/bold]")
    config_panel = Panel(
        f"Model: {settings.model}\n"
        f"Max Tokens: {settings.huggingface.max_tokens}\n"
        f"Temperature: {settings.huggingface.temperature}\n"
        f"Output Directory: {settings.documentation.output_dir}\n"
        f"Debug Mode: {settings.debug}\n"
        f"Verbose Mode: {settings.verbose}",
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

    # Model status
    available_models = get_available_models()

    status_table = Table(show_header=True, header_style="bold magenta")
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", justify="center")
    status_table.add_column("Details")

    # Current model
    current_model = settings.model
    if current_model in available_models:
        model_info = settings.get_model_info()
        status_table.add_row(
            "Active Model", "✅", f"{current_model} ({model_info['size']} params)"
        )
    else:
        status_table.add_row("Active Model", "❌", f"{current_model} (not available)")

    # HuggingFace package status
    if available_models:
        status_table.add_row(
            "HuggingFace", "✅ Available", f"{len(available_models)} models ready"
        )
    else:
        status_table.add_row(
            "HuggingFace", "❌ Not installed", "Run: pip install transformers torch"
        )

    # Device information
    hf_config = settings.get_active_llm_config()
    device_info = hf_config.get_device_info()
    device_status = f"{device_info['device'].upper()} ({device_info['acceleration']})"
    if device_info.get("gpu_name"):
        device_status += f" - {device_info['gpu_name']}"
    status_table.add_row("Hardware", "🚀", device_status)

    # Memory optimization status
    memory_opt = (
        "ON (optimized)" if hf_config.memory_optimization else "OFF (full performance)"
    )
    status_table.add_row("Memory Optimization", "⚙️", memory_opt)

    # Configuration file
    config_file = Path(".commitlm-config.json")
    if config_file.exists():
        status_table.add_row("Configuration", "✅", str(config_file))
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
    "--model",
    type=click.Choice(
        [
            "phi-3-mini-128k",
            "tinyllama",
            "qwen2.5-coder-1.5b",
        ]
    ),
    help="Override model for this generation",
)
@click.option(
    "--memory-optimization/--no-memory-optimization",
    default=True,
    help="Enable/disable memory optimizations (default: enabled)",
)
@click.option(
    "--enable-yarn/--disable-yarn",
    default=None,
    help="Override YaRN setting for this generation (Qwen models only)",
)
@click.pass_context
def generate(
    ctx: click.Context,
    diff_content: Optional[str],
    file_path: Optional[str],
    output: Optional[str],
    model: Optional[str],
    memory_optimization: bool,
    enable_yarn: Optional[bool],
):
    """Generate documentation from git diff content."""
    settings = ctx.obj["settings"]

    # Get diff content
    if file_path:
        with open(file_path, "r") as f:
            diff_content = f.read()
    elif not diff_content:
        console.print(
            "[red]❌ Please provide diff content as argument or use --file option[/red]"
        )
        sys.exit(1)

    if not diff_content.strip():
        console.print("[yellow]⚠️  No diff content provided[/yellow]")
        return

    try:
        from ..core.llm_client import create_llm_client

        # Apply CLI overrides to settings
        runtime_settings = settings
        if model or memory_optimization != True or enable_yarn is not None:  # True is the default
            # Create a copy of settings with overrides
            settings_dict = runtime_settings.model_dump()
            if model:
                settings_dict["model"] = model
                settings_dict["huggingface"]["model"] = model
            settings_dict["huggingface"]["memory_optimization"] = memory_optimization
            if enable_yarn is not None:
                settings_dict["huggingface"]["enable_yarn"] = enable_yarn
            from ..config.settings import Settings

            runtime_settings = Settings(**settings_dict)

        # Show configuration info
        model_info = runtime_settings.get_model_info()
        hf_config = runtime_settings.get_active_llm_config()
        device_info = hf_config.get_device_info()
        optimization_status = (
            "ON (memory optimized)" if memory_optimization else "OFF (full performance)"
        )

        console.print(
            f"[blue]Using model: {runtime_settings.model} - {model_info['description']}"
        )
        console.print(f"[blue]Memory optimization: {optimization_status}[/blue]")
        console.print(
            f"[blue]Hardware: {device_info['device'].upper()} ({device_info['acceleration']})[/blue]"
        )
        
        # Show YaRN status if relevant
        if hf_config.supports_yarn():
            yarn_status = "ON" if hf_config.enable_yarn else "OFF"
            if hf_config.enable_yarn:
                yarn_config = hf_config.get_yarn_config()
                extended_context = yarn_config.get("extended_context", 32768)
                console.print(f"[blue]🧶 YaRN: {yarn_status} (extended context: {extended_context:,} tokens)[/blue]")
            else:
                console.print(f"[blue]🧶 YaRN: {yarn_status}[/blue]")

        with console.status("[bold green]Generating documentation..."):
            client = create_llm_client(runtime_settings)
            documentation = client.generate_documentation(diff_content)

        # Output results
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
