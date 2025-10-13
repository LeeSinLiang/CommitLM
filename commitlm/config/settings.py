"""Configuration settings for AI docs generator using Pydantic v2."""

import json
from pathlib import Path
from typing import Optional, Literal, Any, Dict, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

HuggingFaceModel = Literal["phi-3-mini-128k", "tinyllama", "qwen2.5-coder-1.5b"]
LLMProvider = Literal["huggingface", "gemini", "anthropic", "openai"]

CPU_MODEL_CONFIGS = {
    "qwen2.5-coder-1.5b": {
        "model_name": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "max_tokens": 512,
        "temperature": 0.2,
        "description": "Best overall performance to speed ratio. Code-specialized with chat template (1.5B params)",
        "size": "1.5B",
        "speed": "Fast",
        "use_chat_template": True,
        "supports_yarn": True,
        "base_context_length": 32768,
        "yarn_config": {
            "factor": 4.0,
            "original_max_position_embeddings": 32768,
            "type": "yarn",
            "extended_context": 131072,
        },
        "memory_optimized": {
            "max_tokens": 512,
            "torch_dtype": "float16",
            "load_in_8bit": True,
            "ram_usage": "~3GB",
            "description_suffix": " - Memory optimized (~3GB RAM)",
            "yarn_factor": 2.0,
            "extended_context": 65536,
        },
        "full_performance": {
            "max_tokens": 1024,
            "torch_dtype": "float32",
            "load_in_8bit": False,
            "ram_usage": "~5GB",
            "description_suffix": " - Full performance (~5GB RAM)",
            "yarn_factor": 4.0,
            "extended_context": 131072,
        },
    },
    "phi-3-mini-128k": {
        "model_name": "microsoft/Phi-3-mini-128k-instruct",
        "max_tokens": 1024,
        "temperature": 0.3,
        "description": "Long-context model with 128K token window. Excellent for large diffs (3.8B params)",
        "size": "3.8B",
        "speed": "Fast",
        "use_chat_template": True,
        "memory_optimized": {
            "max_tokens": 512,
            "torch_dtype": "float16",
            "load_in_8bit": True,
            "ram_usage": "~5GB",
            "description_suffix": " - Memory optimized (~5GB RAM)",
        },
        "full_performance": {
            "max_tokens": 1024,
            "torch_dtype": "float32",
            "load_in_8bit": False,
            "ram_usage": "~8GB",
            "description_suffix": " - Full performance (~8GB RAM)",
        },
    },
    "tinyllama": {
        "model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "max_tokens": 200,
        "temperature": 0.4,
        "description": "Minimal resource usage (1.1B params, ~3GB RAM)",
        "ram_usage": "~3GB",
        "size": "1.1B",
        "speed": "Fastest",
    },
}


class HuggingFaceConfig(BaseModel):
    """HuggingFace local model configuration."""

    model: HuggingFaceModel = Field(
        default="qwen2.5-coder-1.5b", description="HuggingFace model to use"
    )
    max_tokens: int = Field(default=512, description="Maximum tokens for response")
    temperature: float = Field(
        default=0.3, ge=0.0, le=2.0, description="Sampling temperature"
    )
    cache_dir: Optional[str] = Field(
        default=None, description="Custom model cache directory"
    )
    device: str = Field(
        default="auto",
        description="Device to run model on ('auto', 'cpu', 'cuda', 'mps')",
    )
    torch_dtype: str = Field(default="float32", description="PyTorch data type")
    memory_optimization: bool = Field(
        default=True,
        description="Enable memory optimizations (8-bit quantization, float16) - disable for better quality",
    )
    enable_yarn: bool = Field(
        default=False,
        description="Enable YaRN (Yet another RoPE extensioN) for extended context length",
    )

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information with memory optimization applied."""
        base_config = CPU_MODEL_CONFIGS.get(
            self.model, CPU_MODEL_CONFIGS["qwen2.5-coder-1.5b"]
        ).copy()

        if self.memory_optimization and "memory_optimized" in base_config:
            optimized_settings = base_config["memory_optimized"]
            base_config.update(optimized_settings)
            base_config["description"] += optimized_settings.get(
                "description_suffix", ""
            )
        elif not self.memory_optimization and "full_performance" in base_config:
            performance_settings = base_config["full_performance"]
            base_config.update(performance_settings)
            base_config["description"] += performance_settings.get(
                "description_suffix", ""
            )

        return base_config

    def get_model_name(self) -> str:
        """Get the actual HuggingFace model name."""
        return self.get_model_info()["model_name"]

    def get_effective_max_tokens(self) -> int:
        """Get max tokens considering memory optimization."""
        return self.get_model_info().get("max_tokens", self.max_tokens)

    def get_effective_torch_dtype(self) -> str:
        """Get torch dtype considering memory optimization."""
        return self.get_model_info().get("torch_dtype", self.torch_dtype)

    def should_use_8bit_quantization(self) -> bool:
        """Check if 8-bit quantization should be used."""
        return self.memory_optimization and self.get_model_info().get(
            "load_in_8bit", False
        )

    def get_optimal_device(self) -> str:
        """Get the optimal device based on availability and configuration."""
        if self.device == "auto":
            return self._detect_best_device()
        return self.device

    def _detect_best_device(self) -> str:
        """Detect the best available device for model inference."""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"

            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"

            return "cpu"

        except ImportError:
            return "cpu"

    def get_device_info(self) -> Dict[str, Any]:
        """Get information about the selected device."""
        device = self.get_optimal_device()
        info: Dict[str, Any] = {"device": device, "acceleration": "None"}

        try:
            import torch

            if device == "cuda" and torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                memory_gb = (
                    torch.cuda.get_device_properties(0).total_memory // (1024**3)
                    if gpu_count > 0
                    else 0
                )
                info["gpu_count"] = gpu_count
                info["gpu_name"] = gpu_name
                info["gpu_memory_gb"] = memory_gb
                info["acceleration"] = "CUDA"
            elif device == "mps":
                info["acceleration"] = "Apple Metal Performance Shaders"
            else:
                import multiprocessing

                info["cpu_cores"] = multiprocessing.cpu_count()
                info["acceleration"] = "CPU-only"

        except ImportError:
            pass

        return info

    def supports_yarn(self) -> bool:
        """Check if the current model supports YaRN."""
        model_info = self.get_model_info()
        return model_info.get("supports_yarn", False)

    def get_yarn_config(self) -> Dict[str, Any]:
        """Get YaRN configuration for the current model."""
        if not self.enable_yarn or not self.supports_yarn():
            return {}

        model_info = self.get_model_info()
        base_yarn_config = model_info.get("yarn_config", {})

        if self.memory_optimization:
            memory_config = model_info.get("memory_optimized", {})
            yarn_factor = memory_config.get(
                "yarn_factor", base_yarn_config.get("factor", 2.0)
            )
            extended_context = memory_config.get("extended_context", 65536)
        else:
            performance_config = model_info.get("full_performance", {})
            yarn_factor = performance_config.get(
                "yarn_factor", base_yarn_config.get("factor", 4.0)
            )
            extended_context = performance_config.get("extended_context", 131072)

        return {
            "factor": yarn_factor,
            "original_max_position_embeddings": base_yarn_config.get(
                "original_max_position_embeddings", 32768
            ),
            "type": "yarn",
            "extended_context": extended_context,
        }

    def get_rope_scaling_config(self) -> Optional[Dict[str, Any]]:
        """Get RoPE scaling configuration for model loading."""
        if not self.enable_yarn or not self.supports_yarn():
            return None

        yarn_config = self.get_yarn_config()
        return {
            "type": "yarn",
            "factor": yarn_config["factor"],
            "original_max_position_embeddings": yarn_config[
                "original_max_position_embeddings"
            ],
        }


class GeminiConfig(BaseModel):
    """Google Gemini API configuration."""

    model: str = Field(default="gemini-2.5-flash", description="Gemini model to use")
    api_key: Optional[str] = Field(default=None, description="Gemini API key")
    max_tokens: int = Field(default=1024, description="Maximum tokens for response")
    temperature: float = Field(default=0.4, description="Sampling temperature")


class AnthropicConfig(BaseModel):
    """Anthropic Claude API configuration."""

    model: str = Field(
        default="claude-3-5-haiku-latest", description="Anthropic model to use"
    )
    api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    max_tokens: int = Field(default=1024, description="Maximum tokens for response")
    temperature: float = Field(default=0.4, description="Sampling temperature")


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""

    model: str = Field(
        default="gpt-5-mini-2025-08-07", description="OpenAI model to use"
    )
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    max_tokens: int = Field(default=1024, description="Maximum tokens for response")
    temperature: float = Field(default=0.4, description="Sampling temperature")


class GitConfig(BaseModel):
    """Git configuration."""

    auto_commit: bool = Field(
        default=False, description="Auto-commit generated documentation"
    )
    commit_message: str = Field(
        default="docs: update documentation", description="Default commit message"
    )
    ignore_patterns: list[str] = Field(
        default_factory=lambda: ["*.pyc", "*.log", "__pycache__/", ".env"],
        description="Patterns to ignore in git diff",
    )


class GitHubConfig(BaseModel):
    """GitHub configuration."""

    token: Optional[str] = Field(default=None, description="GitHub access token")
    create_pr: bool = Field(
        default=True, description="Create pull request for documentation updates"
    )
    pr_title: str = Field(
        default="docs: update documentation", description="Default PR title"
    )
    pr_body: str = Field(
        default="Automatically generated documentation update",
        description="Default PR body",
    )
    auto_merge: bool = Field(default=False, description="Auto-merge PRs if checks pass")


class DocumentationConfig(BaseModel):
    """Configuration for documentation generation."""

    output_dir: str = "docs"
    commit_url_base: str = ""
    template: str = "default"
    include_files: list[str] = []
    exclude_files: list[str] = []


class TaskSettings(BaseModel):
    """Configuration for a specific task."""

    provider: Optional[str] = None
    model: Optional[str] = None


class Settings(BaseModel):
    """Main configuration for the application."""

    provider: str = Field(..., description="The primary LLM provider.")
    model: str = Field(..., description="The primary LLM model.")

    huggingface: Optional[HuggingFaceConfig] = None
    gemini: Optional[GeminiConfig] = None
    anthropic: Optional[AnthropicConfig] = None
    openai: Optional[OpenAIConfig] = None

    documentation: DocumentationConfig = DocumentationConfig()
    fallback_to_local: bool = False

    commit_message_enabled: bool = Field(
        default=False, description="Enable commit message generation"
    )
    doc_generation_enabled: bool = Field(
        default=False, description="Enable documentation generation"
    )

    commit_message: Optional[TaskSettings] = None
    doc_generation: Optional[TaskSettings] = None

    def get_active_llm_config(
        self, task: Optional[str] = None
    ) -> Union[HuggingFaceConfig, GeminiConfig, AnthropicConfig, OpenAIConfig, None]:
        """Get the configuration for the active LLM provider, with task-specific overrides."""
        provider = self.provider
        model = self.model

        if task:
            task_settings = getattr(self, task, None)
            if task_settings:
                if task_settings.provider:
                    provider = task_settings.provider
                if task_settings.model:
                    model = task_settings.model

        config = getattr(self, provider, None)
        if config:
            config_copy = config.copy(deep=True)
            config_copy.model = model
            return config_copy
        return None

    def save_to_file(self, path: Union[str, Path]):
        """Save the current settings to a file."""
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)


_settings: Optional[Settings] = None


def init_settings(config_path: Optional[Union[str, Path]] = None) -> Settings:
    """Load settings from file or use defaults."""
    global _settings
    if _settings is not None:
        return _settings

    if config_path and Path(config_path).exists():
        with open(config_path, "r") as f:
            config_data = json.load(f)
        _settings = Settings(**config_data)
    else:
        # This case should ideally be handled by the CLI, prompting for init
        # For now, we create a default placeholder
        _settings = Settings(provider="none", model="none")

    return _settings


def get_settings() -> Settings:
    """Get the global settings instance."""
    if _settings is None:
        raise RuntimeError("Settings have not been initialized. Run 'commitlm init'.")
    return _settings
