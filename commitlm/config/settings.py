"""Configuration settings for AI docs generator using Pydantic v2."""

import os
import json
from pathlib import Path
from typing import Optional, Literal, Any, Dict
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()

HuggingFaceModel = Literal[
    "phi-3-mini-128k", "tinyllama", "qwen2.5-coder-1.5b"
]

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
    cache_dir: Optional[str] = Field(None, description="Custom model cache directory")
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
            yarn_factor = memory_config.get("yarn_factor", base_yarn_config.get("factor", 2.0))
            extended_context = memory_config.get("extended_context", 65536)
        else:
            performance_config = model_info.get("full_performance", {})
            yarn_factor = performance_config.get("yarn_factor", base_yarn_config.get("factor", 4.0))
            extended_context = performance_config.get("extended_context", 131072)
        
        return {
            "factor": yarn_factor,
            "original_max_position_embeddings": base_yarn_config.get("original_max_position_embeddings", 32768),
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
            "original_max_position_embeddings": yarn_config["original_max_position_embeddings"],
        }


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
    """Documentation generation configuration."""

    output_dir: Path = Field(
        default=Path("docs"), description="Output directory for documentation"
    )
    formats: list[str] = Field(
        default_factory=lambda: ["markdown"], description="Output formats"
    )
    include_code_examples: bool = Field(
        default=True, description="Include code examples in documentation"
    )
    max_file_size: int = Field(
        default=1_000_000, description="Maximum file size to analyze (bytes)"
    )


class Settings(BaseModel):
    """Main configuration settings."""

    model: HuggingFaceModel = Field(
        default="qwen2.5-coder-1.5b", description="HuggingFace model to use"
    )
    huggingface: HuggingFaceConfig = Field(
        default_factory=lambda: HuggingFaceConfig(cache_dir=None)
    )

    git: GitConfig = Field(default_factory=lambda: GitConfig())
    github: GitHubConfig = Field(default_factory=lambda: GitHubConfig())
    documentation: DocumentationConfig = Field(
        default_factory=lambda: DocumentationConfig()
    )

    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(default=False, description="Enable verbose output")
    config_file: Path = Field(
        default=Path(".commitlm-config.json"), description="Configuration file path"
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate that the model is supported."""
        if v not in [
            "phi-3-mini-128k",
            "tinyllama",
            "qwen2.5-coder-1.5b",
        ]:
            raise ValueError(f"Unsupported model: {v}")
        return v

    def model_post_init(self, _context: Any) -> None:
        """Post-initialization validation."""
        if self.huggingface.model != self.model:
            self.huggingface.model = self.model

        model_info = CPU_MODEL_CONFIGS[self.model]
        if (
            hasattr(self.huggingface, "max_tokens")
            and self.huggingface.max_tokens == 512
        ):
            self.huggingface.max_tokens = model_info["max_tokens"]
        if (
            hasattr(self.huggingface, "temperature")
            and self.huggingface.temperature == 0.3
        ):
            self.huggingface.temperature = model_info["temperature"]

    def get_active_llm_config(self) -> HuggingFaceConfig:
        """Get the configuration for the active HuggingFace model."""
        return self.huggingface

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed information about the selected model."""
        return CPU_MODEL_CONFIGS[self.model]

    @classmethod
    def load_from_file(cls, config_path: Path) -> "Settings":
        """Load settings from a JSON configuration file."""
        if not config_path.exists():
            return cls()

        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            return cls(**config_data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Invalid configuration file: {e}")

    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """Save settings to a JSON configuration file."""
        if config_path is None:
            config_path = self.config_file

        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = self.model_dump(
            exclude={
                "openai": {"api_key"},
                "anthropic": {"api_key"},
                "gemini": {"api_key"},
            }
        )

        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=2, default=str)

    @classmethod
    def load_from_env_and_file(cls, config_path: Optional[Path] = None) -> "Settings":
        """Load settings with priority: CLI args > config file > env vars > defaults."""
        if config_path is None:
            config_path = Path(".ai-docs-config.json")

        settings = cls.load_from_file(config_path)

        env_overrides = {}

        if model := os.getenv("AI_DOCS_MODEL"):
            env_overrides["model"] = model

        if debug := os.getenv("AI_DOCS_DEBUG"):
            env_overrides["debug"] = debug.lower() in ("true", "1", "yes")

        if verbose := os.getenv("AI_DOCS_VERBOSE"):
            env_overrides["verbose"] = verbose.lower() in ("true", "1", "yes")

        if env_overrides:
            current_dict = settings.model_dump()
            current_dict.update(env_overrides)
            settings = cls(**current_dict)

        return settings


settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global settings
    if settings is None:
        settings = Settings.load_from_env_and_file()
    return settings


def init_settings(config_path: Optional[Path] = None, **overrides) -> Settings:
    """Initialize settings with optional overrides."""
    global settings
    if config_path:
        settings = Settings.load_from_env_and_file(config_path)
    else:
        settings = Settings.load_from_env_and_file()

    if overrides:
        current_dict = settings.model_dump()
        current_dict.update(overrides)
        settings = Settings(**current_dict)

    return settings
