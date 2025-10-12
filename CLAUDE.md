# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CommitLM is an AI-powered documentation generator that automatically creates comprehensive documentation from git changes. The main feature is automatic documentation generation through git post-commit hooks - every commit triggers AI to analyze changes and generate documentation in the `docs/` folder.

## Architecture

### Multi-Provider LLM System

The codebase implements a provider-agnostic LLM architecture supporting multiple backends:

- **Abstract Base**: `LLMClient` abstract class ([commitlm/core/llm_client.py](commitlm/core/llm_client.py:43)) defines the interface
- **Factory Pattern**: `LLMClientFactory` ([commitlm/core/llm_client.py](commitlm/core/llm_client.py:649)) creates appropriate client based on settings
- **Supported Providers**:
  - `HuggingFaceClient`: Local models (Qwen2.5-Coder, Phi-3, TinyLlama) with CPU/GPU optimization
  - `GeminiClient`: Google Gemini API
  - `AnthropicClient`: Claude API
  - `OpenAIClient`: OpenAI API

Provider selection is configured in `.commitlm-config.json` via the `provider` field.

### Configuration System

Settings use Pydantic v2 models ([commitlm/config/settings.py](commitlm/config/settings.py)):

- **Provider-Specific Configs**: `HuggingFaceConfig`, `GeminiConfig`, `AnthropicConfig`, `OpenAIConfig`
- **Model Configurations**: `CPU_MODEL_CONFIGS` dict contains hardware requirements, context lengths, and optimization settings for each local model
- **Settings Loading Priority**: CLI args > config file > environment variables > defaults
- **Configuration File**: `.commitlm-config.json` at git repository root (auto-detected)

### Git Integration

`GitClient` ([commitlm/integrations/git_client.py](commitlm/integrations/git_client.py:26)) wraps GitPython:

- Extracts diffs from commits
- Manages git hooks installation
- Auto-detects git repository root
- The post-commit hook script ([commitlm/integrations/git_client.py](commitlm/integrations/git_client.py:262)) is dynamically generated and installs into `.git/hooks/post-commit`

### HuggingFace Optimizations

The `HuggingFaceClient` implements extensive hardware optimization:

- **Device Detection**: Auto-selects CUDA > MPS > CPU ([commitlm/config/settings.py](commitlm/config/settings.py:152))
- **Memory Optimization**: 8-bit quantization via bitsandbytes, controlled by `memory_optimization` flag
- **YaRN Support**: Extended context (up to 131K tokens) for Qwen models via RoPE scaling ([commitlm/config/settings.py](commitlm/config/settings.py:236))
- **Chat Templates**: Model-specific prompt formatting (Qwen, Phi-3, TinyLlama) ([commitlm/core/llm_client.py](commitlm/core/llm_client.py:301))
- **Fallback Chain**: Auto-fallback to smaller models on OOM ([commitlm/core/llm_client.py](commitlm/core/llm_client.py:210))

## Development Commands

### Setup
```bash
# Install in development mode
pip install -e .

# Install with all dependencies
pip install -r requirements.txt
```

### Configuration
```bash
# Initialize configuration (interactive)
commitlm init

# Initialize with specific provider
commitlm init --provider gemini --model gemini-1.5-flash

# Initialize HuggingFace with YaRN
commitlm init --model qwen2.5-coder-1.5b --enable-yarn
```

### Git Hook Management
```bash
# Install post-commit hook (main feature)
commitlm install-hook

# Uninstall hook
commitlm uninstall-hook
```

### Testing and Validation
```bash
# Validate configuration and test LLM connection
commitlm validate

# Check system status and hardware detection
commitlm status

# Manual documentation generation (for testing)
commitlm generate "your diff content here"
commitlm generate --file path/to/diff.txt
```

### Configuration Management
```bash
# View all configuration
commitlm config get

# Get specific value
commitlm config get huggingface.max_tokens

# Set configuration value
commitlm config set huggingface.temperature 0.5
```

## Key Implementation Details

### Adding New LLM Providers

1. Create config class in [commitlm/config/settings.py](commitlm/config/settings.py) inheriting from `BaseModel`
2. Add client class in [commitlm/core/llm_client.py](commitlm/core/llm_client.py) inheriting from `LLMClient`
3. Implement `_setup_client()`, `generate_text()`, `generate_documentation()`, and `provider_name` property
4. Update `LLMClientFactory.create_client()` to handle new provider
5. Add provider to `LLMProvider` Literal type

### Memory Optimization Toggle

The `memory_optimization` flag ([commitlm/config/settings.py](commitlm/config/settings.py:104)) affects:
- Torch dtype (float16 vs float32)
- 8-bit quantization (enabled/disabled)
- Max tokens limits
- YaRN scaling factors

Model configs contain both `memory_optimized` and `full_performance` settings that are applied dynamically.

### Prompt System

Prompts use Jinja2 templates via `render_documentation_prompt()` ([commitlm/config/prompts.py](commitlm/config/prompts.py)). The HuggingFace client additionally wraps prompts in model-specific chat templates.

### Git Hook Workflow

1. User commits code
2. Post-commit hook runs ([commitlm/integrations/git_client.py](commitlm/integrations/git_client.py:275))
3. Hook extracts diff using `git show`
4. Calls `commitlm generate` with diff content
5. Saves documentation to `docs/commit_<short_hash>_<timestamp>.md`
6. Prepends metadata header (commit hash, message, timestamp)

## Configuration File Structure

The `.commitlm-config.json` should be at git repository root:

```json
{
  "provider": "huggingface|gemini|anthropic|openai",
  "model": "model-name",
  "huggingface": {
    "model": "qwen2.5-coder-1.5b",
    "max_tokens": 512,
    "temperature": 0.3,
    "device": "auto",
    "memory_optimization": true,
    "enable_yarn": false
  },
  "gemini": {
    "model": "gemini-1.5-flash",
    "api_key": "your-key"
  },
  "documentation": {
    "output_dir": "docs"
  },
  "fallback_to_local": false
}
```

API keys should be stored in environment variables (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) rather than config file.

## Testing Patterns

When testing LLM integration:
- Use `commitlm validate` to verify provider connection
- Use `commitlm status` to check hardware detection
- Use `commitlm generate` with sample text for quick iteration
- Check logs for device selection, quantization status, and YaRN config

## Recent Project Changes

The project was recently renamed from "ai-doc" to "CommitLM" (commit dcd84b4). Some legacy references may still exist in comments or hook scripts.

A multi-provider system was added (commit 2bf6e59) to support cloud LLM APIs alongside local models.
