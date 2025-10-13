"""Utility functions and helpers for AI docs generator."""

import re
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import shutil


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO", verbose: bool = False) -> None:
    """Setup logging configuration."""
    if verbose:
        level = "DEBUG"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_file_hash(file_path: Path) -> str:
    """Generate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Failed to hash file {file_path}: {e}")
        return ""


def get_text_hash(text: str) -> str:
    """Generate SHA-256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_directory(path: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    path.mkdir(parents=True, exist_ok=True)


def safe_filename(filename: str) -> str:
    """Convert a string to a safe filename by removing/replacing unsafe characters."""
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    filename = re.sub(r"[\x00-\x1f]", "", filename)
    filename = filename.strip(". ")

    if not filename:
        filename = "unnamed"

    if len(filename) > 255:
        filename = filename[:255]

    return filename


def get_git_root(path: Path | None = None) -> Optional[Path]:
    """Find the git repository root directory."""
    if path is None:
        path = Path.cwd()

    path = Path(path).resolve()

    while path != path.parent:
        if (path / ".git").exists():
            return path
        path = path.parent

    return None


def is_git_repository(path: Path | None = None) -> bool:
    """Check if the current directory is inside a git repository."""
    return get_git_root(path) is not None


def get_file_language(file_path: Path) -> str:
    """Detect programming language from file extension."""
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".php": "php",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".kt": "kotlin",
        ".swift": "swift",
        ".scala": "scala",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".fish": "fish",
        ".ps1": "powershell",
        ".sql": "sql",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".xml": "xml",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "conf",
        ".md": "markdown",
        ".markdown": "markdown",
        ".rst": "rst",
        ".tex": "latex",
        ".r": "r",
        ".R": "r",
        ".m": "matlab",
        ".pl": "perl",
        ".lua": "lua",
        ".vim": "vim",
        ".dockerfile": "dockerfile",
        ".dockerignore": "dockerignore",
        ".gitignore": "gitignore",
        ".editorconfig": "editorconfig",
    }

    suffix = file_path.suffix.lower()
    name = file_path.name.lower()

    if name == "dockerfile":
        return "dockerfile"
    elif name == "makefile":
        return "makefile"
    elif name.startswith(".env"):
        return "env"
    elif name == "requirements.txt":
        return "requirements"
    elif name in ["license", "licence"]:
        return "license"
    elif name == "readme":
        return "text"

    return extension_map.get(suffix, "text")


def extract_functions_and_classes(content: str, language: str) -> Dict[str, List[str]]:
    """Extract function and class names from code content."""
    functions = []
    classes = []

    if language == "python":
        func_pattern = r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
        class_pattern = r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]"

        for line in content.split("\n"):
            func_match = re.match(func_pattern, line)
            if func_match:
                functions.append(func_match.group(1))

            class_match = re.match(class_pattern, line)
            if class_match:
                classes.append(class_match.group(1))

    elif language in ["javascript", "typescript", "jsx", "tsx"]:
        func_patterns = [
            r"function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(",
            r"const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*=>|\([^)]*\)\s*=>\s*{|function)",
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:\s*(?:async\s+)?(?:\([^)]*\)\s*=>|\([^)]*\)\s*=>\s*{|function)",
        ]

        class_pattern = r"class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)"

        for line in content.split("\n"):
            for pattern in func_patterns:
                match = re.search(pattern, line)
                if match:
                    functions.append(match.group(1))
                    break

            class_match = re.search(class_pattern, line)
            if class_match:
                classes.append(class_match.group(1))

    return {"functions": functions, "classes": classes}


def analyze_diff_complexity(diff_content: str) -> Dict[str, Any]:
    """Analyze the complexity of a git diff."""
    lines = diff_content.split("\n")

    stats = {
        "total_lines": len(lines),
        "additions": 0,
        "deletions": 0,
        "modifications": 0,
        "files_changed": set(),
        "complexity_score": 0,
        "change_types": set(),
        "languages": set(),
    }

    current_file = None

    for line in lines:
        if line.startswith("diff --git"):
            match = re.search(r"diff --git a/(.+?) b/(.+?)$", line)
            if match:
                current_file = match.group(2)
                stats["files_changed"].add(current_file)

                if current_file:
                    lang = get_file_language(Path(current_file))
                    stats["languages"].add(lang)

        if line.startswith("+") and not line.startswith("+++"):
            stats["additions"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            stats["deletions"] += 1

    file_count = len(stats["files_changed"])
    total_changes = stats["additions"] + stats["deletions"]

    stats["complexity_score"] = min(100, (file_count * 10) + (total_changes / 10))

    if stats["complexity_score"] < 20:
        stats["complexity_level"] = "low"
    elif stats["complexity_score"] < 50:
        stats["complexity_level"] = "medium"
    else:
        stats["complexity_level"] = "high"

    if any(line.startswith("+++") and "/dev/null" not in line for line in lines):
        stats["change_types"].add("addition")
    if any(line.startswith("---") and "/dev/null" not in line for line in lines):
        stats["change_types"].add("deletion")
    if stats["additions"] > 0 and stats["deletions"] > 0:
        stats["change_types"].add("modification")

    # Convert sets to lists for JSON serialization
    stats["files_changed"] = list(stats["files_changed"])
    stats["change_types"] = list(stats["change_types"])
    stats["languages"] = list(stats["languages"])

    return stats


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f}{size_names[i]}"


def get_timestamp(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get current timestamp as formatted string."""
    return datetime.now().strftime(format_str)


def validate_api_key(api_key: str, provider: str) -> bool:
    """Basic validation for API key format."""
    if not api_key or not api_key.strip():
        return False

    if provider == "openai":
        return api_key.startswith("sk-") and len(api_key) > 20
    elif provider == "anthropic":
        return api_key.startswith("sk-ant-") and len(api_key) > 30
    elif provider == "gemini":
        return len(api_key) > 20

    return True


def clean_diff_content(diff_content: str) -> str:
    """Clean and normalize git diff content."""
    lines = diff_content.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.rstrip()

        if not cleaned_lines and not line:
            continue

        cleaned_lines.append(line)

    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)


def create_temp_file(content: str, suffix: str = ".tmp") -> Path:
    """Create a temporary file with the given content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        f.write(content)
        return Path(f.name)


def cleanup_temp_file(file_path: Path) -> None:
    """Clean up a temporary file."""
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {e}")


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is binary."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\0" in chunk
    except Exception:
        return False


def get_relative_path(file_path: Path, base_path: Path | None = None) -> Path:
    """Get relative path from base directory."""
    if base_path is None:
        base_path = Path.cwd()

    try:
        return file_path.relative_to(base_path)
    except ValueError:
        return file_path


def backup_file(file_path: Path, backup_suffix: str = ".backup") -> Path:
    """Create a backup of a file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
    shutil.copy2(file_path, backup_path)
    return backup_path


def restore_backup(backup_path: Path) -> Path:
    """Restore a file from backup."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    if not backup_path.name.endswith(".backup"):
        raise ValueError(f"Not a backup file: {backup_path}")

    original_path = backup_path.with_suffix("")
    original_path = original_path.with_suffix(
        original_path.suffix.replace(".backup", "")
    )

    shutil.copy2(backup_path, original_path)
    return original_path
