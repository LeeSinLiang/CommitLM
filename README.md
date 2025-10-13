# CommitLM — Docs on every commit.

**Automated Documentation Generation for Every Git Commit**

CommitLM is an AI-powered tool that automatically generates documentation for your code changes and creates conventional commit messages for you. It integrates with Git to analyze your staged changes and provide documentation and commit messages, streamlining your workflow and improving your project's maintainability.

## Features

- **🤖 Automatic Git Hook Integration**: Generates documentation automatically after every commit
- **📁 Organized Documentation**: All docs are saved in `docs/` folder with timestamps and commit hashes
- **🏠 Local AI Models**: Uses HuggingFace models (Qwen2.5-Coder, TinyLlama, Phi-3, etc.) - no API keys required
- **⚡ GPU/CPU Auto-detection**: Automatically uses NVIDIA GPU if available, falls back to CPU
- **💾 Memory Optimization**: Toggleable 8-bit quantization for systems with limited RAM

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd commitlm
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### 2. Initialize Configuration

```bash
# Interactive setup (recommended) - guides you through model selection, YaRN, and token limits
commitlm init

# Non-interactive setup with specific options
commitlm init --model qwen2.5-coder-1.5b --max-tokens 1024 --enable-yarn
```

#### Interactive Setup Flow

When you run `commitlm init`, you'll be guided through:

1. **Model Selection**: Choose from available models with recommendations
2. **YaRN Configuration** (Qwen models only): Enable extended context for large diffs
3. **Max Token Configuration**: Set output length with smart defaults based on your choices

Example interactive session:
```
? Select LLM provider › huggingface
? Select model › qwen2.5-coder-1.5b
? Which tasks do you want to enable? › both
? Do you want to use different models for specific tasks? › No
? Enable fallback to a local model if the API fails? › No
```

**Model Options:**
- `qwen2.5-coder-1.5b` - **Recommended** - Best performance/speed ratio with YaRN support for extended context (1.5B params)
- `phi-3-mini-128k` - Long-context model with 128K token window. Excellent for large diffs (3.8B params)  
- `tinyllama` - Minimal resource usage (1.1B params)

### 3. Install Git Hook

```bash
# Enable automatic documentation generation on every commit
commitlm install-hook
```

After installing the git hook, every time you run `git commit`, AI will automatically:
1. Analyze your git diff
2. Generate comprehensive documentation 
3. Save it in the `docs/` folder with timestamp and commit hash
4. No manual intervention required

Example workflow:
```bash
# Make your code changes
git add .
git commit -m "feat: add user authentication system"

# AI automatically generates documentation at:
# docs/commit_abc1234_2024-01-15_14-30-25.md
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

## Hardware Support

The tool automatically detects and uses the best available hardware:

1. **NVIDIA GPU** (CUDA) - Uses GPU acceleration with `device_map="auto"`
2. **Apple Silicon** (MPS) - Uses Apple's Metal Performance Shaders
3. **CPU** - Falls back to optimized CPU inference

## Memory Optimization

Memory optimization is **enabled by default** and includes:
- 8-bit quantization (reduces memory by ~50%)
- float16 precision
- Automatic model sharding

Disable for better quality (requires more RAM):
```bash
commitlm init --no-memory-optimization
```

## Usage Examples

### Normal Workflow (Automatic)
After running `commitlm install-hook`, documentation is generated automatically:

```bash
# Make changes to your code
echo "console.log('new feature')" >> src/app.js

# Commit as usual - documentation happens automatically
git add .
git commit -m "feat: add logging feature"

# Check the generated documentation
ls docs/
# Output: commit_a1b2c3d_2024-01-15_14-30-25.md
```

### Manual Generation (Debug Only)
The `generate` command is for testing and debugging purposes, not everyday use:

```bash
# Test the AI model with sample diff (for debugging)
commitlm generate "fix: resolve memory leak in user session handler

- Fixed session cleanup on logout
- Added proper event listener removal  
- Implemented garbage collection for expired tokens"
```

### Model Selection During Init
```bash
# For systems with limited RAM (3-4GB)
commitlm init --model tinyllama

# For systems with good specs (8GB+ RAM) - long context support
commitlm init --model phi-3-mini-128k --no-memory-optimization

# For code-focused tasks (recommended)
commitlm init --model qwen2.5-coder-1.5b

# Enable YaRN for extended context (Qwen models only)
commitlm init --model qwen2.5-coder-1.5b --enable-yarn
```

### YaRN Extended Context (Qwen Models)

YaRN (Yet another RoPE extensioN) enables extended context lengths for better handling of large git diffs:

```bash
# Enable YaRN with default settings
commitlm init --model qwen2.5-coder-1.5b --enable-yarn

# YaRN with memory optimization (64K context)
commitlm init --model qwen2.5-coder-1.5b --enable-yarn --memory-optimization

# YaRN with full performance (131K context)  
commitlm init --model qwen2.5-coder-1.5b --enable-yarn --no-memory-optimization

# Override YaRN for specific generation
commitlm generate "large diff content" --enable-yarn
```

**YaRN Benefits:**
- **Extended Context**: Up to 131K tokens (vs 32K default)
- **Better Large Diff Handling**: Processes extensive code changes without truncation
- **Automatic Scaling**: Adapts scaling factor based on memory optimization settings

### Custom Token Limits
```bash
# Set custom max tokens (default varies by model)
commitlm init --max-tokens 512   # Shorter, focused docs
commitlm init --max-tokens 2048  # Longer, detailed docs
```

## Configuration

Configuration is stored in `.commitlm-config.json`:

```json
{
  "model": "qwen2.5-coder-1.5b",
  "huggingface": {
    "model": "qwen2.5-coder-1.5b", 
    "max_tokens": 512,
    "temperature": 0.2,
    "device": "auto",
    "memory_optimization": true
  },
  "documentation": {
    "output_dir": "docs"
  }
}
```

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

### Model Download Issues
Models are downloaded automatically on first use to `~/.cache/huggingface/`. Ensure you have internet connection and sufficient disk space.

### Memory Errors  
```bash
# Enable memory optimization (default)
commitlm init --memory-optimization

# Try a smaller model
commitlm init --model tinyllama
```

### Performance Issues
```bash
# Disable memory optimization for better quality
commitlm init --no-memory-optimization

# Use GPU if available (auto-detected by default)
commitlm status  # Check if GPU is detected
```

### CUDA/GPU Issues
```bash
# Check GPU detection
commitlm status

# Force CPU usage if GPU causes issues  
# Edit .commitlm-config.json and set "device": "cpu"
```
