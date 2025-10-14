# CommitLM — AI-powered Git Documentation & Commit Messages

[![PyPI version](https://img.shields.io/pypi/v/commitlm.svg)](https://pypi.org/project/commitlm/)
[![Python Versions](https://img.shields.io/pypi/pyversions/commitlm.svg)](https://pypi.org/project/commitlm/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Automated Documentation and Commit Message Generation for Every Git Commit**

CommitLM is an AI-native tool that automatically generates comprehensive documentation for your code changes and creates conventional commit messages. It integrates seamlessly with Git through hooks to analyze your changes and provide intelligent documentation and commit messages, streamlining your workflow and improving your project's maintainability.

## Why CommitLM?

- 🚀 **Save Time**: Eliminate manual documentation and commit message writing
- 📝 **Maintain Quality**: Consistent, professional documentation for every commit
- 🤖 **Flexible AI**: Choose from multiple LLM providers or run models locally
- ⚡ **Zero Friction**: Works automatically via Git hooks - no workflow changes needed
- 🔒 **Privacy First**: Run local models for complete data privacy
- 💰 **Cost Effective**: Free local models or affordable cloud APIs

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

## Quick Start

### 1. Install

```bash
pip install commitlm
```

### 2. Initialize Configuration

```bash
# Interactive setup (recommended) - guides you through provider, model, and task selection
commitlm init

# Setup with specific provider and model
commitlm init --provider gemini --model gemini-2.0-flash-exp
commitlm init --provider anthropic --model claude-3-5-haiku-latest
commitlm init --provider openai --model gpt-4o-mini
commitlm init --provider huggingface --model qwen2.5-coder-1.5b
```

#### Interactive Setup Flow

When you run `commitlm init`, you'll be guided through:

1. **Provider Selection**: Choose between local (HuggingFace) or cloud (Gemini, Anthropic, OpenAI)
2. **Model Selection**: Pick from provider-specific models
3. **Task Configuration**: Enable commit messages, documentation, or both
4. **Task-Specific Models** (optional): Use different models for different tasks
5. **Fallback Configuration**: Set up fallback to local models if API fails

Example interactive session:
```
? Select LLM provider › gemini
? Select model › gemini-2.0-flash-exp
? Which tasks do you want to enable? › both
? Do you want to use different models for specific tasks? › Yes
  ? Select provider for commit_message › huggingface
  ? Select model › qwen2.5-coder-1.5b
? Enable fallback to a local model if the API fails? › Yes
```

#### Provider Options

**Local Models (HuggingFace)** - No API keys required:
- `qwen2.5-coder-1.5b` - **Recommended** - Best performance/speed ratio, YaRN support (1.5B params)
- `phi-3-mini-128k` - Long context (128K tokens), excellent for large diffs (3.8B params)
- `tinyllama` - Minimal resource usage (1.1B params)

**Cloud APIs** - Faster, more capable:
- **Gemini**: `gemini-2.0-flash-exp`, `gemini-1.5-pro`, `gemini-1.5-flash` (requires `GEMINI_API_KEY`)
- **Anthropic**: `claude-3-5-sonnet-latest`, `claude-3-5-haiku-latest` (requires `ANTHROPIC_API_KEY`)
- **OpenAI**: `gpt-4o`, `gpt-4o-mini` (requires `OPENAI_API_KEY`)

### 3. Install Git Hooks

CommitLM provides two powerful git hooks:

```bash
# Install both hooks (recommended)
commitlm install-hook

# Install only commit message generation
commitlm install-hook message

# Install only documentation generation
commitlm install-hook docs
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
4. Saves to `docs/commit_<hash>_<timestamp>.md`

Example workflow:
```bash
# Make your code changes
git add .

# Option 1: Use hook to generate message
git commit
# Editor opens with AI-generated message pre-filled
# Edit if needed, save and close

# Option 2: Use git alias (see below)
git c  # Stages, generates message, commits in one step

# Documentation is automatically generated after commit completes
# docs/commit_abc1234_2025-01-15_14-30-25.md
```

**Example Generated Commit Message:**
```
feat(auth): add OAuth2 authentication support

Implemented OAuth2 authentication flow with support for Google and GitHub providers.
Added token refresh mechanism and secure session management.
```

**Example Generated Documentation:**
```markdown
# Commit Documentation

## Summary
Added OAuth2 authentication support with Google and GitHub providers, implementing
secure token management and session handling.

## Changes Made
- Implemented OAuth2 authentication flow
- Added GoogleAuthProvider and GitHubAuthProvider classes
- Created TokenRefreshService for automatic token renewal
- Added secure session storage with encryption

## Technical Impact
- New dependencies: oauth2-client, jose
- Database migration required for user_tokens table
- Environment variables needed: GOOGLE_CLIENT_ID, GITHUB_CLIENT_ID

## Usage Example
\`\`\`python
from auth import OAuth2Manager

manager = OAuth2Manager(provider='google')
auth_url = manager.get_authorization_url()
\`\`\`
```

#### Alternative: Git Alias Workflow

Set up a convenient git alias for one-command commits:

```bash
commitlm set-alias
# Creates 'git c' alias (or custom name)

# Now use it:
git add .
git c  # Automatically generates message and commits
```

### 4. Validate Setup

```bash
# View configuration and hardware info
commitlm status
```

## System Requirements

### Minimum Requirements
- Python 3.9+
- 4GB RAM (with memory optimization enabled)
- 2GB disk space (for model downloads)

### Recommended Requirements  
- Python 3.10+
- 8GB+ RAM
- NVIDIA GPU with 4GB+ VRAM (optional, auto-detected)
- SSD storage

## Configuration

### Environment Variables

Set API keys for cloud providers:

```bash
# In your shell profile (~/.bashrc, ~/.zshrc, etc.)
export GEMINI_API_KEY="your-gemini-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

**Where to get API keys:**
- **Gemini**: [Google AI Studio](https://makersuite.google.com/app/apikey) - Free tier available
- **Anthropic**: [Anthropic Console](https://console.anthropic.com/) - Pay-as-you-go pricing
- **OpenAI**: [OpenAI Platform](https://platform.openai.com/api-keys) - Pay-as-you-go pricing

### Task-Specific Models

Use different models for different tasks:

```bash
# Enable task-specific models during init
commitlm init
# Select "Yes" when prompted "Do you want to use different models for specific tasks?"

# Or configure later
commitlm enable-task

# Change model for specific task
commitlm config change-model commit_message
commitlm config change-model doc_generation
```

**Example use case**: Use fast local model (Qwen) for commit messages, powerful cloud API (Claude) for documentation.

### Configuration File

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
    "model": "gemini-1.5-pro"
  },
  "fallback_to_local": true
}
```

## Hardware Support (Local Models)

When using HuggingFace local models, the tool automatically detects and uses the best available hardware:

1. **NVIDIA GPU** (CUDA) - Uses GPU acceleration with `device_map="auto"`
2. **Apple Silicon** (MPS) - Uses Apple's Metal Performance Shaders
3. **CPU** - Falls back to optimized CPU inference

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

### Using Commit Message Hook

```bash
# Make changes
echo "def new_feature(): pass" >> src/app.py
git add .

# Commit without message - hook generates it
git commit
# Editor opens with pre-filled message:
# feat(app): add new feature function

# Review, edit if needed, save and close
```

### Using Git Alias

```bash
# Set up alias once
commitlm set-alias

# Use it for every commit
git add .
git c  # Generates message and commits automatically
```

### Using Documentation Hook

After installing the `post-commit` hook:

```bash
# Make changes
echo "console.log('new feature')" >> src/app.js
git add .
git commit -m "feat: add logging feature"

# Documentation automatically generated at:
# docs/commit_a1b2c3d_2025-01-15_14-30-25.md
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

We welcome contributions! Here's how you can help:

### Reporting Issues
- Check [existing issues](https://github.com/LeeSinLiang/commitLM/issues) first
- Provide clear reproduction steps
- Include system info from `commitlm status`

### Feature Requests
- Open an issue with the `enhancement` label
- Describe the use case and expected behavior

### Development Setup
```bash
# Clone the repository
git clone https://github.com/LeeSinLiang/commitLM.git
cd commitLM

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
black commitlm/
ruff check commitlm/
```

### Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Run linters (`black .` and `ruff check .`)
7. Commit your changes (use CommitLM for commit messages!)
8. Push to your fork
9. Open a Pull Request

## License

CommitLM is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for full details.
See [NOTICE](NOTICE) file for third-party attributions.

## Support

- **Issues**: [GitHub Issues](https://github.com/LeeSinLiang/commitLM/issues)
- **Discussions**: [GitHub Discussions](https://github.com/LeeSinLiang/commitLM/discussions)
- **PyPI**: [https://pypi.org/project/commitlm/](https://pypi.org/project/commitlm/)

---

*If CommitLM saves you time, consider giving it a ⭐ on GitHub!*
