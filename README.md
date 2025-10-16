# CommitLM — Git Companion That Teaches Your AI What Just Happened. 

[![PyPI version](https://img.shields.io/pypi/v/commitlm.svg)](https://pypi.org/project/commitlm/)
[![Python Versions](https://img.shields.io/pypi/pyversions/commitlm.svg)](https://pypi.org/project/commitlm/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Automated Documentation and Commit Message Generation for Every Git Commit**

AI coding agents are powerful but stateless—they lack context on why a change was made. This leads to guesswork and bugs.

While most "AI commit" tools stop at the message, CommitLM is an AI-native git tool that creates a tiny, structured docs per commit. This acts as a **briefing for LLM coding agents** (like Copilot, Gemini CLI, Claude, etc.), so they can:

* ✅ Pick up exactly where you or another agent left off.  
* 🧠 Respect constraints and project-specific nuances.  
* 🔄 Update callers, tests, and migrations with fewer misses.

```bash
pip install commitlm
commitlm init
```

## Why CommitLM?

- 🚀 **Rapid Documentation for AI Agents**: Eliminate manual documentation and commit message writing, while ensuring your AI agents pick up where you left off.
- ⚡ **Zero Friction**: Works automatically via Git hooks - no workflow changes needed
- 📝 **Memory-savvy & long-context**: 8-bit quantization and YaRN for extended context lengths
- 🤖 **Flexible AI**: Choose from multiple LLM providers or run models locally
- 📝 **Create a Living Knowledge Base**: Your repo becomes a self-updating source of truth, making onboarding and handoffs seamless for both humans and AI. 
- 🔒 **Privacy First**: Run local models for complete data privacy

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [System Requirements](#system-requirements)
- [Configuration](#configuration)
- [Hardware Support](#hardware-support-local-models)
- [Usage Examples](#usage-examples)
- [Commands](#commands)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

### Core Capabilities
- **📝 Automatic Commit Messages**: AI-generated conventional commit messages via `prepare-commit-msg` hook
- **📚 Automatic Documentation**: Comprehensive docs generated after every commit via `post-commit` hook
- **🎯 Task-Specific Models**: Use different models for commit messages vs documentation generation
- **📁 Organized Documentation**: All docs saved in `docs/` folder with timestamps and commit hashes

### Multi-Provider Support
- **☁️ Cloud APIs**: Google Gemini, Anthropic Claude, OpenAI GPT support
- **🏠 Local Models**: HuggingFace models (Qwen2.5-Coder, Phi-3, TinyLlama) - no API keys required
- **🔄 Fallback Options**: Configure fallback to local models if API fails
- **⚙️ Flexible Configuration**: Mix and match providers for different tasks

### Performance & Optimization
- **⚡ GPU/CPU Auto-detection**: Automatically uses NVIDIA GPU, Apple Silicon, or CPU
- **💾 Memory Optimization**: Toggleable 8-bit quantization for systems with limited RAM
- **🎯 Extended Context**: YaRN support for Qwen models (up to 131K tokens)

#### Provider Options

**Local Models (HuggingFace)** - No API keys required, Privacy-first:
- `qwen2.5-coder-1.5b` - **Recommended** - Best performance/speed ratio, YaRN support (1.5B params)
- `phi-3-mini-128k` - Long context (128K tokens), excellent for large diffs (3.8B params)
- `tinyllama` - Minimal resource usage (1.1B params)

**Cloud APIs** - Faster, more capable:
- **Gemini**
- **Anthropic**
- **OpenAI**

### Git Hooks Installation (if not done during init)

CommitLM provides two powerful git hooks: automatic commit message generation and automatic documentation generation.

```bash
# Interactive setup
commitlm install-hook
```

**What each hook does**:

**`prepare-commit-msg` hook** (Commit Messages):
1. Runs before commit editor opens
2. Analyzes staged changes (`git diff --cached`)
3. Generates conventional commit message
4. Pre-fills commit message in editor

**`post-commit` hook** (Documentation):
1. Runs after commit completes
2. Extracts commit diff
3. Generates comprehensive documentation
4. Saves to `docs/commit_<commit message>.md`

Example workflow:
```bash
# Make your code changes
git add .

# Git alias (see below)
git c  # generates commit message, commits, and generate post commit documentation

# Documentation is automatically generated after commit completes
# docs/commit_feat:added_OAuth2_authentication_support.md
```

**Example Generated Commit Message:**
```
feat(auth): add OAuth2 authentication support
```

**Example Generated Documentation:**

Refer to the [docs](docs/) folder for samples.

### Validate Setup

```bash
# View configuration and hardware info
commitlm status
```

## System Requirements

### Recommended Requirements (for local models)
- Python 3.10+
- 8GB+ RAM
- NVIDIA GPU with 4GB+ VRAM (optional, auto-detected) / Apple Silicon (MPS)

## Configuration

### Default Configuration File

Configuration is stored in `.commitlm-config.json` at your git repository root:

```json
{
  "provider": "gemini",
  "model": "gemini-2.0-flash-exp",
  "commit_message_enabled": true,
  "doc_generation_enabled": true,
  "commit_message": {
    "provider": "huggingface",
    "model": "qwen2.5-coder-1.5b"
  },
  "doc_generation": {
    "provider": "gemini",
    "model": "gemini-2.5-pro"
  },
  "fallback_to_local": true
}
```


### If you prefer environment variables:

Set API keys for cloud providers:

```bash
# In your shell profile (~/.bashrc, ~/.zshrc, etc.)
export GEMINI_API_KEY="your-gemini-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```
### Task-Specific Models

Use different models for different tasks:

```bash
# Enable task-specific models during init
commitlm init

# Or configure later
commitlm enable-task

# Change model for specific task
commitlm config change-model commit_message
commitlm config change-model doc_generation
```

**Example use case**: Use lightweight model (gemini-2.5-flash-lite) for commit messages, powerful model (gemini-2.5-pro) for documentation.

## Hardware Support (Local Models)

When using HuggingFace local models, the tool automatically detects and uses the best available hardware:

1. **NVIDIA GPU** (CUDA) - Uses GPU acceleration with `device_map="auto"`
2. **Apple Silicon** (MPS) - Uses Apple's Metal Performance Shaders
3. **CPU** - Falls back to optimized CPU inference (not recommended)

### Memory Optimization

Memory optimization is **enabled by default** for local models and includes:
- 8-bit quantization (reduces memory by ~50%)
- float16 precision
- Automatic model sharding

Disable for better quality (requires more RAM):
```bash
commitlm init --provider huggingface --no-memory-optimization
```

## Usage Examples
### Using Git Alias

```bash
# Set up alias once
commitlm set-alias

# Use it for every commit
git add .
git c  # generates commit message, commits, and generates post-commit documentation
```

### Using Documentation Hook

After installing the `post-commit` hook:

```bash
# Make changes
git add .
git commit -m "feat: add logging feature" # or use 'git c' for auto message

# Documentation automatically generated at:
# docs/commit_feat:implemented_logging_feature.md
```

### Manual Generation (Testing/Debugging)

```bash
# Test documentation generation with sample diff
commitlm generate "fix: resolve memory leak
- Fixed session cleanup
- Added event listener removal"

# Test commit message generation
echo "function test() {}" > test.js
git add test.js
commitlm generate --short-message

# Use specific provider/model for testing
commitlm generate --provider gemini --model gemini-2.0-flash-exp "your diff here"
```

### Advanced: YaRN Extended Context (Local Models)

For HuggingFace Qwen models, YaRN enables extended context lengths:

```bash
# Enable YaRN during initialization
commitlm init --provider huggingface --model qwen2.5-coder-1.5b --enable-yarn

# YaRN with memory optimization (64K context)
commitlm init --provider huggingface --model qwen2.5-coder-1.5b --enable-yarn --memory-optimization

# YaRN with full performance (131K context)
commitlm init --provider huggingface --model qwen2.5-coder-1.5b --enable-yarn --no-memory-optimization
```

**YaRN Benefits:**
- Extended context up to 131K tokens (vs 32K default)
- Better handling of large git diffs without truncation
- Automatic scaling based on memory optimization settings

## Commands

### Primary Commands

| Command | Description |
| --- | --- |
| `commitlm init` | Initializes the project with an interactive setup guide. |
| `commitlm install-hook` | Installs the Git hooks for automation. |
| `commitlm status` | Shows the current configuration and hardware status. |
| `commitlm validate` | Validates the configuration and tests the LLM connection. |

### Secondary Commands

| Command | Description |
| --- | --- |
| `commitlm generate` | Manually generate a commit message or documentation. |
| `commitlm uninstall-hook` | Removes the Git hooks. |
| `commitlm set-alias` | Sets up a Git alias for easier commit message generation. |
| `commitlm config get [KEY]` | Gets a configuration value. |
| `commitlm config set <KEY> <VALUE>` | Sets a configuration value. |
| `commitlm config change-model <TASK>` | Changes the model for a specific task. |
| `commitlm enable-task` | Enables or disables tasks. |

## Troubleshooting

### API Key Issues
```bash
# Verify environment variables are set
echo $GEMINI_API_KEY
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Add to shell profile if missing
export GEMINI_API_KEY="your-key-here"
```

### Model Download Issues (Local Models)
Models are downloaded automatically on first use to `~/.cache/huggingface/`. Ensure you have internet connection and sufficient disk space.

### Memory Errors (Local Models)
```bash
# Enable memory optimization (default)
commitlm init --provider huggingface --memory-optimization

# Try a smaller model
commitlm init --provider huggingface --model tinyllama

# Or switch to cloud API
commitlm init --provider gemini
```

### Performance Issues (Local Models)
```bash
# Check hardware detection
commitlm status

# Disable memory optimization for better quality
commitlm init --provider huggingface --no-memory-optimization

# Switch to cloud API for faster generation
commitlm config change-model default
# Select cloud provider (Gemini/Anthropic/OpenAI)
```

### Hook Not Working
```bash
# Verify hooks are installed
ls -la .git/hooks/

# Reinstall hooks
commitlm install-hook --force

# Check which tasks are enabled
commitlm config get commit_message_enabled
commitlm config get doc_generation_enabled

# Enable/disable tasks
commitlm enable-task
```

### CUDA/GPU Issues (Local Models)
```bash
# Check GPU detection
commitlm status

# Force CPU usage if GPU causes issues
# Edit .commitlm-config.json and set "device": "cpu"
```

### Git Hook Conflicts
If you have existing `prepare-commit-msg` or `post-commit` hooks:
```bash
# Backup existing hooks
cp .git/hooks/prepare-commit-msg .git/hooks/prepare-commit-msg.backup
cp .git/hooks/post-commit .git/hooks/post-commit.backup

# Install CommitLM hooks
commitlm install-hook

# Manually merge if needed by editing .git/hooks/prepare-commit-msg or .git/hooks/post-commit
```

### Configuration Not Found
```bash
# Ensure you're in a git repository
git status

# Reinitialize configuration
commitlm init
```

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) to get started.

Before contributing, please also read our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

CommitLM is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for full details, and [NOTICE](NOTICE) file for third-party attributions.

## Support

- **Issues**: [GitHub Issues](https://github.com/LeeSinLiang/commitLM/issues)
- **Discussions**: [GitHub Discussions](https://github.com/LeeSinLiang/commitLM/discussions)
- **PyPI**: [https://pypi.org/project/commitlm/](https://pypi.org/project/commitlm/)

---

*If CommitLM saves you time, consider giving it a ⭐ on GitHub!*
