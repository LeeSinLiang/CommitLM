"""Initialization command for CommitLM."""

import sys
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from InquirerPy import prompt

from ..config.settings import CPU_MODEL_CONFIGS
from ..core.llm_client import get_available_models

console = Console()


def init_command(
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
        console.print(
            "[yellow]⚠️  No git repository detected. Saving config in current directory.[/yellow]"
        )

    if config_path.exists() and not force:
        questions = [
            {
                "type": "list",
                "message": f"Configuration file {config_path} already exists. Overwrite?",
                "choices": ["Yes", "No"],
                "name": "overwrite",
                "default": "No",
                "qmark": "",
            }
        ]
        answers = prompt(questions)
        if answers.get("overwrite") == "No":
            console.print("[yellow]Initialization cancelled.[/yellow]")
            return

    if not provider:
        questions = [
            {
                "type": "list",
                "message": "Select LLM provider",
                "choices": ["huggingface", "gemini", "anthropic", "openai"],
                "name": "provider",
                "default": "huggingface",
                "qmark": "",
            }
        ]
        answers = prompt(questions)
        provider = answers.get("provider")

    # At this point, provider is guaranteed to be a string
    assert provider is not None, "Provider must be set"

    config_data = {"provider": provider, "documentation": {"output_dir": output_dir}}

    if provider == "huggingface":
        _init_huggingface(config_data, model)
    else:
        _init_api_provider(config_data, provider, model)

    questions = [
        {
            "type": "list",
            "message": "Which tasks do you want to enable?",
            "choices": ["commit_message", "doc_generation", "both"],
            "name": "enabled_tasks",
            "default": "both",
            "qmark": "",
        }
    ]
    answers = prompt(questions)
    enabled_tasks = answers.get("enabled_tasks")

    config_data["commit_message_enabled"] = enabled_tasks in ["commit_message", "both"]
    config_data["doc_generation_enabled"] = enabled_tasks in ["doc_generation", "both"]

    questions = [
        {
            "type": "list",
            "message": "\nDo you want to use different models for specific tasks?",
            "choices": ["Yes", "No"],
            "name": "use_specific_models",
            "default": "No",
            "qmark": "",
        }
    ]
    answers = prompt(questions)

    if answers.get("use_specific_models") == "Yes":
        if config_data["commit_message_enabled"]:
            questions = [
                {
                    "type": "list",
                    "message": "Configure a specific model for commit message generation?",
                    "choices": ["Yes", "No"],
                    "name": "config_commit_msg_model",
                    "default": "Yes",
                    "qmark": "",
                }
            ]
            answers = prompt(questions)
            if answers.get("config_commit_msg_model") == "Yes":
                task_config = _prompt_for_task_model(provider)
                config_data["commit_message"] = task_config

        if config_data["doc_generation_enabled"]:
            questions = [
                {
                    "type": "list",
                    "message": "Configure a specific model for documentation generation?",
                    "choices": ["Yes", "No"],
                    "name": "config_doc_gen_model",
                    "default": "Yes",
                    "qmark": "",
                }
            ]
            answers = prompt(questions)
            if answers.get("config_doc_gen_model") == "Yes":
                task_config = _prompt_for_task_model(provider)
                config_data["doc_generation"] = task_config

    questions = [
        {
            "type": "list",
            "message": "\nEnable fallback to a local model if the API fails?",
            "choices": ["Yes", "No"],
            "name": "fallback_to_local",
            "default": "No",
            "qmark": "",
        }
    ]
    answers = prompt(questions)
    config_data["fallback_to_local"] = answers.get("fallback_to_local") == "Yes"

    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        console.print(f"\n[green]✅ Configuration saved to {config_path}[/green]")

        # Automatically run install-hook
        console.print("\n[bold]Next Step: Installing Git Hooks[/bold]")
        hook_type = "none"
        if (
            config_data["commit_message_enabled"]
            and config_data["doc_generation_enabled"]
        ):
            hook_type = "both"
        elif config_data["commit_message_enabled"]:
            hook_type = "message"
        elif config_data["doc_generation_enabled"]:
            hook_type = "docs"

        if hook_type != "none":
            from .commands import install_hook

            ctx.invoke(install_hook, hook_type=hook_type, force=force)

        # Prompt to set up alias
        questions = [
            {
                "type": "list",
                "message": "\nWould you like to set up a git alias for easier commits?",
                "choices": ["Yes", "No"],
                "name": "setup_alias",
                "default": "Yes",
                "qmark": "",
            }
        ]
        answers = prompt(questions)
        if (
            config_data["commit_message_enabled"]
            and answers.get("setup_alias") == "Yes"
        ):
            from .commands import set_alias

            ctx.invoke(set_alias)
        else:
            console.print("\nTo generate a commit message, you can run:")
            console.print(
                "[bold cyan]git diff --cached | commitlm generate --short-message[/bold cyan]"
            )
            console.print(
                "\nYou can set up an alias for this command later by running:"
            )
            console.print("[bold cyan]commitlm set-alias[/bold cyan]")

    except Exception as e:
        console.print(f"[red]❌ Failed to save configuration: {e}[/red]")
        sys.exit(1)


def _prompt_for_task_model(default_provider: str) -> dict:
    """Helper to prompt for task-specific model config."""
    questions = [
        {
            "type": "list",
            "message": "Provider for this task",
            "choices": ["huggingface", "gemini", "anthropic", "openai"],
            "name": "provider",
            "default": default_provider,
            "qmark": "",
        },
        {
            "type": "input",
            "message": "Model for this task",
            "name": "model",
            "qmark": "",
        },
    ]
    answers = prompt(questions)
    return {"provider": answers.get("provider"), "model": answers.get("model")}


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
        questions = [
            {
                "type": "list",
                "message": "Select model",
                "choices": available_models,
                "name": "model",
                "default": "qwen2.5-coder-1.5b",
                "qmark": "",
            }
        ]
        answers = prompt(questions)
        model = answers.get("model")

    config_data["model"] = model
    config_data["huggingface"] = {"model": model}


def _init_api_provider(config_data: dict, provider: str, model: Optional[str]):
    """Initialize API provider configuration."""
    questions = [
        {
            "type": "password",
            "message": f"Enter {provider.capitalize()} API key",
            "name": "api_key",
            "qmark": "",
        }
    ]
    answers = prompt(questions)
    api_key = answers.get("api_key")

    if not model:
        default_models = {
            "gemini": "gemini-2.5-flash",
            "anthropic": "claude-3-5-haiku-latest",
            "openai": "gpt-5-mini-2025-08-07",
        }
        questions = [
            {
                "type": "input",
                "message": f"Enter {provider.capitalize()} model",
                "name": "model",
                "default": default_models.get(provider, ""),
                "qmark": "",
            }
        ]
        answers = prompt(questions)
        model = answers.get("model")

    config_data["model"] = model
    config_data[provider] = {"model": model, "api_key": api_key}
