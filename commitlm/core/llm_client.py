"""HuggingFace local model client for CPU-optimized documentation generation."""

from abc import ABC, abstractmethod
from typing import List, Optional, Union
import logging
import os

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    AutoTokenizer = None
    AutoModelForCausalLM = None
    pipeline = None
    torch = None

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types
import anthropic
import openai

from ..config.settings import (
    Settings,
    HuggingFaceConfig,
    GeminiConfig,
    AnthropicConfig,
    OpenAIConfig,
    CPU_MODEL_CONFIGS,
)
from ..config.prompts import (
    render_documentation_prompt,
    render_short_commit_message_prompt,
)

logger = logging.getLogger(__name__)

SHORT_MESSAGE_FALLBACK = "chore: failed to generate commit message"


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    pass


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(
        self,
        config: Union[HuggingFaceConfig, GeminiConfig, AnthropicConfig, OpenAIConfig],
    ):
        self.config = config
        self._client = None
        self._setup_client()

    @abstractmethod
    def _setup_client(self) -> None:
        """Setup the provider-specific client."""
        pass

    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    def generate_documentation(
        self, diff_content: str, file_context: str = "", **kwargs
    ) -> str:
        """Generate documentation from git diff content."""
        pass

    @abstractmethod
    def generate_short_message(self, diff_content: str, **kwargs) -> str:
        """Generate a short commit message from git diff content."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass

    def _generate_short_message_fallback(self) -> str:
        """Simple fallback for a short commit message."""
        return SHORT_MESSAGE_FALLBACK


class HuggingFaceClient(LLMClient):
    """CPU-optimized Hugging Face client for local models."""

    def _setup_client(self) -> None:
        """Setup HuggingFace client with CPU optimizations."""
        if not TRANSFORMERS_AVAILABLE:
            raise LLMClientError(
                "Transformers package not installed. Install with: pip install transformers torch accelerate"
            )

        if not isinstance(self.config, HuggingFaceConfig):
            raise LLMClientError("Invalid config type for HuggingFace client")

        self.model_name = self.config.get_model_name()
        self.model_key = self.config.model
        self._load_cpu_optimized_model()

    def _load_cpu_optimized_model(self):
        """Load model with CPU optimizations."""
        try:
            logger.info(f"Loading HuggingFace model: {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, cache_dir=self.config.cache_dir, trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            torch_dtype_str = self.config.get_effective_torch_dtype()
            torch_dtype = getattr(torch, torch_dtype_str)

            optimal_device = self.config.get_optimal_device()
            device_info = self.config.get_device_info()

            logger.info(
                f"Selected device: {optimal_device} ({device_info.get('acceleration', 'Unknown')})"
            )
            if optimal_device == "cuda" and device_info.get("gpu_name"):
                logger.info(
                    f"GPU: {device_info['gpu_name']} ({device_info.get('gpu_memory_gb', 0)}GB)"
                )

            model_kwargs = {
                "torch_dtype": torch_dtype,
                "trust_remote_code": True,
                "use_cache": True,
                "low_cpu_mem_usage": True,
                "cache_dir": self.config.cache_dir,
            }

            # Only use device_map for GPU acceleration, not for CPU
            if optimal_device in ["cuda", "mps"]:
                model_kwargs["device_map"] = "auto"

            rope_scaling = self.config.get_rope_scaling_config()
            if rope_scaling:
                yarn_config = self.config.get_yarn_config()
                extended_context = yarn_config.get("extended_context", 32768)
                logger.info(
                    f"🧶 YaRN enabled for {self.model_name}: "
                    f"factor={rope_scaling['factor']}, extended_context={extended_context:,} tokens"
                )
                model_kwargs["rope_scaling"] = rope_scaling

            if self.config.should_use_8bit_quantization():
                import importlib.util

                if importlib.util.find_spec("bitsandbytes") is not None:
                    model_kwargs["load_in_8bit"] = True
                    logger.info(
                        f"Enabling 8-bit quantization for {self.model_name} (memory optimization ON)"
                    )
                else:
                    logger.warning(
                        "bitsandbytes not available, skipping 8-bit quantization"
                    )
            else:
                logger.info(
                    f"Loading {self.model_name} with full precision (memory optimization OFF)"
                )

            if optimal_device == "cuda" and self.model_key in [
                "qwen2.5-coder-1.5b",
            ]:
                import importlib.util

                if importlib.util.find_spec("flash_attn") is not None:
                    try:
                        model_kwargs["attn_implementation"] = "flash_attention_2"
                        logger.info("Enabling Flash Attention 2 for GPU acceleration")
                    except Exception as e:
                        logger.debug(
                            f"Flash Attention 2 not supported for this model: {e}"
                        )
                else:
                    logger.debug(
                        "Flash Attention 2 not installed, using standard attention"
                    )

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, **model_kwargs
            )

            self.model.eval()

            if pipeline is None:
                raise RuntimeError("Pipeline not available")

            pipeline_kwargs = {
                "model": self.model,
                "tokenizer": self.tokenizer,
                "max_new_tokens": self.config.get_effective_max_tokens(),
                "temperature": self.config.temperature,
                "do_sample": True if self.config.temperature > 0 else False,
                "batch_size": 1,
                "return_full_text": False,
            }

            # Only specify device if NOT using device_map (which means CPU)
            if "device_map" not in model_kwargs:
                if optimal_device == "cpu":
                    pipeline_kwargs["device"] = -1

            self.pipeline = pipeline("text-generation", **pipeline_kwargs)

            logger.info(f"Successfully loaded CPU-optimized model: {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            if self.model_key != "tinyllama":
                logger.info("Attempting fallback to TinyLlama model...")
                self._fallback_to_smaller_model()
            else:
                raise LLMClientError(f"Failed to load model: {e}")

    def _fallback_to_smaller_model(self):
        """Fallback to a smaller model if the current one fails."""
        fallback_order = ["phi-2", "tinyllama", "codet5"]

        for fallback_model in fallback_order:
            if fallback_model == self.model_key:
                continue

            try:
                logger.info(f"Trying fallback model: {fallback_model}")
                self.model_key = fallback_model
                if fallback_model in CPU_MODEL_CONFIGS:
                    self.config.model = fallback_model
                self.model_name = CPU_MODEL_CONFIGS[fallback_model]["model_name"]
                self._load_cpu_optimized_model()
                return
            except Exception as e:
                logger.warning(f"Fallback model {fallback_model} also failed: {e}")
                continue

        raise LLMClientError("All model fallbacks failed")

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using local HuggingFace model."""
        try:
            if self.model_key in ["tinyllama", "codet5"]:
                return self._generate_simple(prompt, **kwargs)
            else:
                return self._generate_standard(prompt, **kwargs)

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return self._generate_fallback()

    def _generate_standard(self, prompt: str, **kwargs) -> str:
        """Standard generation for larger models."""
        try:
            formatted_prompt = self._format_prompt(prompt)

            response = self.pipeline(
                formatted_prompt,
                max_new_tokens=min(
                    self.config.get_effective_max_tokens(),
                    kwargs.get("max_tokens", self.config.get_effective_max_tokens()),
                ),
                temperature=self.config.temperature,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                num_return_sequences=1,
            )

            generated_text = response[0]["generated_text"]
            return self._extract_response(generated_text, formatted_prompt)
        except Exception as e:
            logger.error(f"Standard generation failed: {e}")
            return self._generate_fallback()

    def _generate_simple(self, prompt: str) -> str:
        """Simplified generation for very small models."""
        try:
            # Use shorter, more direct prompts for small models
            simple_prompt = (
                f"Document these code changes:\n{prompt[:1000]}\n\nDocumentation:"
            )

            inputs = self.tokenizer.encode(simple_prompt, return_tensors="pt")

            if torch is None:
                raise RuntimeError("PyTorch not available")

            # Move inputs to same device as model
            if hasattr(self.model, "device"):
                inputs = inputs.to(self.model.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=min(self.config.get_effective_max_tokens(), 256),
                    temperature=self.config.temperature,
                    do_sample=True if self.config.temperature > 0 else False,
                    pad_token_id=self.tokenizer.eos_token_id,
                    num_return_sequences=1,
                )

                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                return response[len(simple_prompt) :].strip()

        except Exception as e:
            logger.error(f"Simple generation failed: {e}")
            return self._generate_fallback()

    def _format_prompt(self, prompt: str) -> str:
        """Format prompt based on model type."""
        model_lower = self.model_name.lower()
        model_config = CPU_MODEL_CONFIGS.get(self.model_key, {})

        # Handle Qwen2.5-Coder with chat template
        if "qwen2.5-coder" in model_lower and model_config.get("use_chat_template"):
            return self._format_qwen_chat_template(prompt)
        elif "phi-3" in model_lower and model_config.get("use_chat_template"):
            return self._format_phi3_chat_template(prompt)
        elif "tinyllama" in model_lower:
            return f"<|system|>\nYou are a helpful assistant.</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
        elif "qwen" in model_lower:
            return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        elif "codet5" in model_lower:
            return f"### Code Analysis Task: {prompt}\n### Response:"
        else:
            return f"### Task: {prompt}\n### Response:"

    def _format_qwen_chat_template(self, prompt: str) -> str:
        """Format prompt using Qwen2.5-Coder chat template."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant specialized in code analysis and documentation generation.",
                },
                {"role": "user", "content": prompt},
            ]
            # Use apply_chat_template if available
            if hasattr(self.tokenizer, "apply_chat_template"):
                return self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            else:
                # Fallback to manual formatting
                return f"<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant specialized in code analysis and documentation generation.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        except Exception as e:
            logger.warning(f"Failed to apply chat template for Qwen2.5-Coder: {e}")
            # Fallback to manual formatting
            return f"<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant specialized in code analysis and documentation generation.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    def _format_phi3_chat_template(self, prompt: str) -> str:
        """Format prompt using Phi-3-mini-128k chat template."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant specialized in code analysis and documentation generation.",
                },
                {"role": "user", "content": prompt},
            ]
            # Use apply_chat_template if available
            if hasattr(self.tokenizer, "apply_chat_template"):
                return self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            else:
                # Fallback to manual formatting
                return f"<|system|>\nYou are a helpful AI assistant specialized in code analysis and documentation generation.<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
        except Exception as e:
            logger.warning(f"Failed to apply chat template for Phi-3: {e}")
            # Fallback to manual formatting
            return f"<|system|>\nYou are a helpful AI assistant specialized in code analysis and documentation generation.<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>\n"

    def _extract_response(self, full_response: str, prompt: str) -> str:
        """Extract the actual response from the full generated text."""
        # Remove the prompt from the response
        if full_response.startswith(prompt):
            response = full_response[len(prompt) :].strip()
        else:
            response = full_response.strip()

        # Clean up model-specific artifacts
        response = response.replace("<|end|>", "").replace("</s>", "").strip()

        # Clean up Qwen2.5-Coder specific artifacts
        response = response.replace("<|im_end|>", "").strip()

        # Clean up response artifacts
        response = (
            response.replace("<|fim_prefix|>", "")
            .replace("<|fim_suffix|>", "")
            .replace("<|fim_middle|>", "")
            .strip()
        )

        # Remove any remaining template markers
        response = (
            response.replace("<|assistant|>", "")
            .replace("<|user|>", "")
            .replace("<|system|>", "")
            .strip()
        )

        return response if response else self._generate_fallback()

    def _generate_fallback(self) -> str:
        """Simple fallback documentation."""
        return """# Code Changes

## Summary
Code modifications detected in this commit.

## Details
This commit contains updates to the codebase. Please review the changes manually for detailed documentation.

## Note
Documentation generation encountered an issue. Please check the model configuration and try again."""

    def generate_documentation(
        self, diff_content: str, file_context: str = "", **kwargs
    ) -> str:
        """Generate documentation from git diff using local HuggingFace model."""
        prompt = self._build_optimized_prompt_from_template(diff_content, file_context)
        return self.generate_text(prompt, **kwargs)

    def generate_short_message(self, diff_content: str, **kwargs) -> str:
        """Generate a short commit message from git diff using local HuggingFace model."""
        prompt = render_short_commit_message_prompt(diff_content)
        # Use a smaller max_tokens for commit messages
        response = self.generate_text(prompt, max_tokens=50, **kwargs)

        if response.startswith("# Code Changes"):
            raise LLMClientError("Failed to generate commit message.")

        # Clean up response to ensure it's a single line
        return response.strip().split("\n")[0]

    def _build_optimized_prompt_from_template(
        self, diff_content: str, file_context: str = ""
    ) -> str:
        """Build prompt using prompts.py templates, optimized for CPU inference."""
        # Truncate diff for CPU models to manage memory and token usage
        max_diff_length = self._get_max_diff_length()
        if len(diff_content) > max_diff_length:
            diff_content = (
                diff_content[:max_diff_length]
                + "\n... (truncated for memory optimization)"
            )

        # Use the proper documentation prompt from prompts.py
        try:
            # Get effective max tokens to inform the model
            max_tokens = self.config.get_effective_max_tokens()

            prompt = render_documentation_prompt(
                diff_content=diff_content,
                file_context=file_context,
                template_name="documentation_generation",
                max_tokens=max_tokens,
            )
            return prompt
        except Exception as e:
            logger.warning(f"Failed to render documentation prompt from template: {e}")
            # Fallback to simplified prompt for CPU-constrained models
            return self._build_fallback_prompt(diff_content, file_context)

    def _get_max_diff_length(self) -> int:
        """Get maximum diff length based on model capability."""
        if self.model_key in ["tinyllama"]:
            return 800
        elif self.model_key in ["qwen2.5-coder-1.5b", "phi-3-mini-128k"]:
            return 4000  # Models with large context windows can handle more content
        else:
            return 1500

    def _build_fallback_prompt(self, diff_content: str, file_context: str = "") -> str:
        """Simple fallback prompt for when template rendering fails."""
        context_section = f"File Context:\n{file_context}\n\n" if file_context else ""

        return f"""Analyze this code change and write brief documentation:

{context_section}```diff
{diff_content}
```

Write documentation with:
1. Summary: What changed
2. Impact: How it affects the code
3. Usage: How to use new features (if any)

Keep it concise and clear."""

    @property
    def provider_name(self) -> str:
        return f"huggingface-{self.model_key}"


class GeminiClient(LLMClient):
    """Client for Google Gemini API."""

    def _setup_client(self) -> None:
        """Setup Gemini client."""
        api_key = self.config.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMClientError(
                "GEMINI_API_KEY not found in config file or environment variables."
            )
        self._client = genai.Client(api_key=api_key)
        self.model = self.config.model

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Gemini API."""
        try:
            # Workaround for Gemini 2.5 models: max_output_tokens can cause empty responses
            # Only use temperature for now
            generation_config = types.GenerateContentConfig(
                temperature=self.config.temperature,
            )
            response = self._client.models.generate_content(
                model=self.model, contents=prompt, config=generation_config
            )
            # Handle potential None response
            if response.text is None:
                logger.warning(
                    "Gemini returned None response, trying to access candidates"
                )
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        return (
                            candidate.content.parts[0].text or self._generate_fallback()
                        )
                logger.error(
                    f"Empty response from Gemini. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}"
                )
                return self._generate_fallback()
            return response.text
        except google_exceptions.PermissionDenied as e:
            logger.error(f"Gemini API key is invalid: {e}")
            raise LLMClientError(
                "Gemini API key is invalid. Please run 'commitlm init' to configure a new key or update it in your .commitlm-config.json file."
            )
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return self._generate_fallback()

    def generate_documentation(
        self, diff_content: str, file_context: str = "", **kwargs
    ) -> str:
        """Generate documentation from git diff using Gemini API."""
        prompt = render_documentation_prompt(
            diff_content=diff_content,
            file_context=file_context,
            template_name="documentation_generation",
            max_tokens=self.config.max_tokens,
        )
        return self.generate_text(prompt, **kwargs)

    def generate_short_message(self, diff_content: str, **kwargs) -> str:
        """Generate a short commit message from git diff using Gemini API."""
        prompt = render_short_commit_message_prompt(diff_content)
        response = self.generate_text(prompt, max_tokens=50, **kwargs)

        if response.startswith("# Code Changes"):
            raise LLMClientError("Failed to generate commit message.")

        return response.strip().split("\n")[0]

    def _generate_fallback(self) -> str:
        """Simple fallback documentation."""
        return """# Code Changes

## Summary
Code modifications detected in this commit.

## Details
This commit contains updates to the codebase. Please review the changes manually for detailed documentation.

## Note
Documentation generation via Gemini failed. Please check your API key and model configuration."""

    @property
    def provider_name(self) -> str:
        return "gemini"


class AnthropicClient(LLMClient):
    """Client for Anthropic Claude API."""

    def _setup_client(self) -> None:
        """Setup Anthropic client."""
        api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMClientError(
                "ANTHROPIC_API_KEY not found in config file or environment variables."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Anthropic API."""
        try:
            message = self._client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except anthropic.APIStatusError as e:
            if e.status_code == 401:
                logger.error(f"Anthropic API key is invalid: {e}")
                raise LLMClientError(
                    "Anthropic API key is invalid. Please run 'commitlm init' to configure a new key or update it in your .commitlm-config.json file."
                )
            logger.error(f"Anthropic API call failed: {e}")
            return self._generate_fallback()
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return self._generate_fallback()

    def generate_documentation(
        self, diff_content: str, file_context: str = "", **kwargs
    ) -> str:
        """Generate documentation from git diff using Anthropic API."""
        prompt = render_documentation_prompt(
            diff_content=diff_content,
            file_context=file_context,
            template_name="documentation_generation",
            max_tokens=self.config.max_tokens,
        )
        return self.generate_text(prompt, **kwargs)

    def generate_short_message(self, diff_content: str, **kwargs) -> str:
        """Generate a short commit message from git diff using Anthropic API."""
        prompt = render_short_commit_message_prompt(diff_content)
        response = self.generate_text(prompt, max_tokens=50, **kwargs)

        if response.startswith("# Code Changes"):
            return self._generate_short_message_fallback()

        return response.strip().split("\n")[0]

    def _generate_fallback(self) -> str:
        """Simple fallback documentation."""
        return """# Code Changes

## Summary
Code modifications detected in this commit.

## Details
This commit contains updates to the codebase. Please review the changes manually for detailed documentation.

## Note
Documentation generation via Anthropic failed. Please check your API key and model configuration."""

    @property
    def provider_name(self) -> str:
        return "anthropic"


class OpenAIClient(LLMClient):
    """Client for OpenAI API."""

    def _setup_client(self) -> None:
        """Setup OpenAI client."""
        api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMClientError(
                "OPENAI_API_KEY not found in config file or environment variables."
            )
        self._client = openai.OpenAI(api_key=api_key)

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using OpenAI API."""
        try:
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            return response.choices[0].message.content or ""
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI API key is invalid: {e}")
            raise LLMClientError(
                "OpenAI API key is invalid. Please run 'commitlm init' to configure a new key or update it in your .commitlm-config.json file."
            )
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return self._generate_fallback()

    def generate_documentation(
        self, diff_content: str, file_context: str = "", **kwargs
    ) -> str:
        """Generate documentation from git diff using OpenAI API."""
        prompt = render_documentation_prompt(
            diff_content=diff_content,
            file_context=file_context,
            template_name="documentation_generation",
            max_tokens=self.config.max_tokens,
        )
        return self.generate_text(prompt, **kwargs)

    def generate_short_message(self, diff_content: str, **kwargs) -> str:
        """Generate a short commit message from git diff using OpenAI API."""
        prompt = render_short_commit_message_prompt(diff_content)
        response = self.generate_text(prompt, max_tokens=50, **kwargs)

        if response.startswith("# Code Changes"):
            return self._generate_short_message_fallback()

        return response.strip().split("\n")[0]

    def _generate_fallback(self) -> str:
        """Simple fallback documentation."""
        return """# Code Changes

## Summary
Code modifications detected in this commit.

## Details
This commit contains updates to the codebase. Please review the changes manually for detailed documentation.

## Note
Documentation generation via OpenAI failed. Please check your API key and model configuration."""

    @property
    def provider_name(self) -> str:
        return "openai"


class LLMClientFactory:
    """Factory for creating LLM clients."""

    @staticmethod
    def create_client(settings: Settings, task: Optional[str] = None) -> LLMClient:
        """Create an LLM client based on the settings."""
        active_config = settings.get_active_llm_config(task)

        provider = settings.provider
        if task:
            task_settings = getattr(settings, task, None)
            if task_settings and task_settings.provider:
                provider = task_settings.provider

        if not active_config:
            raise LLMClientError(f"Configuration for provider '{provider}' not found.")

        if provider == "huggingface":
            return HuggingFaceClient(active_config)
        elif provider == "gemini":
            return GeminiClient(active_config)
        elif provider == "anthropic":
            return AnthropicClient(active_config)
        elif provider == "openai":
            return OpenAIClient(active_config)
        else:
            raise LLMClientError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def get_available_models() -> List[str]:
        """Get list of available HuggingFace models."""
        if TRANSFORMERS_AVAILABLE:
            return list(CPU_MODEL_CONFIGS.keys())
        return []

    @staticmethod
    def validate_model_availability(model: str) -> bool:
        """Check if a model is available."""
        return TRANSFORMERS_AVAILABLE and model in CPU_MODEL_CONFIGS


def create_llm_client(settings: Settings, task: Optional[str] = None) -> LLMClient:
    """Convenience function to create an LLM client."""
    return LLMClientFactory.create_client(settings, task)


def get_available_models() -> List[str]:
    """Convenience function to get available models."""
    return LLMClientFactory.get_available_models()
