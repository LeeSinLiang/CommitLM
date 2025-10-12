# CommitLM — Docs on every commit.

**Automated Documentation Generation for Every Git Commit**

AI-powered documentation generator that automatically creates comprehensive documentation from your git changes using local AI models. The main feature is automatic documentation generation through git post-commit hooks - every time you commit code, AI analyzes the changes and generates documentation in your `docs/` folder.

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
cd ai-doc
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### 2. Initialize Configuration

```bash
# Interactive setup (recommended) - guides you through model selection, YaRN, and token limits
ai-docs init

# Non-interactive setup with specific options
ai-docs init --model qwen2.5-coder-1.5b --max-tokens 1024 --enable-yarn
```

#### Interactive Setup Flow

When you run `ai-docs init`, you'll be guided through:

1. **Model Selection**: Choose from available models with recommendations
2. **YaRN Configuration** (Qwen models only): Enable extended context for large diffs
3. **Max Token Configuration**: Set output length with smart defaults based on your choices

Example interactive session:
```
🚀 Initializing AI Docs Generator

Available Local Models:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Model                    ┃ Size ┃ RAM Usage              ┃ Description                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Recommended: qwen2.5-coder-1.5b - Best overall performance to speed ratio
Select model [qwen2.5-coder-1.5b]: 

🧶 YaRN (Extended Context) Options:
YaRN enables extended context length for processing larger git diffs.
• Default context: 32,768 tokens
• Extended context: 131,072 tokens
Enable YaRN for extended context length? [y/N]: y

📝 Output Length Configuration:
YaRN enabled - can handle up to 131,072 input tokens
• Recommended: 1024 tokens
• Higher values = more detailed docs but slower generation
Max output tokens [1024]: 1024
```

**Model Options:**
- `qwen2.5-coder-1.5b` - **Recommended** - Best performance/speed ratio with YaRN support for extended context (1.5B params)
- `phi-3-mini-128k` - Long-context model with 128K token window. Excellent for large diffs (3.8B params)  
- `tinyllama` - Minimal resource usage (1.1B params)

### 3. Install Git Hook

```bash
# Enable automatic documentation generation on every commit
ai-docs install-hook
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
ai-docs status
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
ai-docs init --no-memory-optimization
```

## Usage Examples

### Normal Workflow (Automatic)
After running `ai-docs install-hook`, documentation is generated automatically:

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
ai-docs generate "fix: resolve memory leak in user session handler

- Fixed session cleanup on logout
- Added proper event listener removal  
- Implemented garbage collection for expired tokens"
```

### Model Selection During Init
```bash
# For systems with limited RAM (3-4GB)
ai-docs init --model tinyllama

# For systems with good specs (8GB+ RAM) - long context support
ai-docs init --model phi-3-mini-128k --no-memory-optimization

# For code-focused tasks (recommended)
ai-docs init --model qwen2.5-coder-1.5b

# Enable YaRN for extended context (Qwen models only)
ai-docs init --model qwen2.5-coder-1.5b --enable-yarn
```

### YaRN Extended Context (Qwen Models)

YaRN (Yet another RoPE extensioN) enables extended context lengths for better handling of large git diffs:

```bash
# Enable YaRN with default settings
ai-docs init --model qwen2.5-coder-1.5b --enable-yarn

# YaRN with memory optimization (64K context)
ai-docs init --model qwen2.5-coder-1.5b --enable-yarn --memory-optimization

# YaRN with full performance (131K context)  
ai-docs init --model qwen2.5-coder-1.5b --enable-yarn --no-memory-optimization

# Override YaRN for specific generation
ai-docs generate "large diff content" --enable-yarn
```

**YaRN Benefits:**
- **Extended Context**: Up to 131K tokens (vs 32K default)
- **Better Large Diff Handling**: Processes extensive code changes without truncation
- **Automatic Scaling**: Adapts scaling factor based on memory optimization settings

### Custom Token Limits
```bash
# Set custom max tokens (default varies by model)
ai-docs init --max-tokens 512   # Shorter, focused docs
ai-docs init --max-tokens 2048  # Longer, detailed docs
```

## Configuration

Configuration is stored in `.ai-docs-config.json`:

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

```bash
ai-docs init            # Initialize configuration (Step 2)
ai-docs install-hook    # Install git post-commit hook (Step 3 - Main feature)
ai-docs status          # Show current config and hardware info  
ai-docs validate        # Test model connection
ai-docs generate TEXT   # Manual generation (debug/testing only)
ai-docs uninstall-hook  # Remove git post-commit hook
ai-docs --help          # Show all commands
```

**Primary Commands:**
- `ai-docs init` → Set up your AI model and configuration
- `ai-docs install-hook` → **Enable automatic documentation** (this is what you want!)
- `ai-docs status` → Check everything is working

**Debug Commands:**
- `ai-docs generate` → Test documentation generation manually
- `ai-docs validate` → Test AI model is loading correctly

## Troubleshooting

### Model Download Issues
Models are downloaded automatically on first use to `~/.cache/huggingface/`. Ensure you have internet connection and sufficient disk space.

### Memory Errors  
```bash
# Enable memory optimization (default)
ai-docs init --memory-optimization

# Try a smaller model
ai-docs init --model tinyllama
```

### Performance Issues
```bash
# Disable memory optimization for better quality
ai-docs init --no-memory-optimization

# Use GPU if available (auto-detected by default)
ai-docs status  # Check if GPU is detected
```

### CUDA/GPU Issues
```bash
# Check GPU detection
ai-docs status

# Force CPU usage if GPU causes issues  
# Edit .ai-docs-config.json and set "device": "cpu"
```
