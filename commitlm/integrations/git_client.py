"""Git integration client for extracting diffs and managing repository operations."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING, cast
import logging

if TYPE_CHECKING:
    from git import Repo as RepoType

try:
    import git
    from git import Repo, GitCommandError
except ImportError:
    git = None
    Repo = None
    GitCommandError = Exception

from ..utils.helpers import get_git_root

logger = logging.getLogger(__name__)


class GitClientError(Exception):
    """Base exception for git client errors."""

    pass


class GitClient:
    """Git client for repository operations and diff extraction."""

    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize git client.

        Args:
            repo_path: Path to git repository. If None, uses current directory.
        """
        self.repo_path = repo_path or Path.cwd()
        self._repo = None
        self._setup_repo()

    def _setup_repo(self) -> None:
        """Setup git repository connection."""
        if git is None:
            raise GitClientError(
                "GitPython package not installed. Install with: pip install gitpython"
            )

        git_root = get_git_root(self.repo_path)
        if not git_root:
            raise GitClientError(f"No git repository found at {self.repo_path}")

        self.repo_path = git_root

        if Repo is None:
            raise GitClientError(
                "GitPython library not available. Install with: pip install GitPython"
            )

        try:
            self._repo = Repo(self.repo_path)
            logger.info(f"Git client initialized for repository: {self.repo_path}")
        except Exception as e:
            raise GitClientError(f"Failed to initialize git repository: {e}")

    @property
    def repo(self) -> "RepoType":
        """Get the git repository object."""
        if self._repo is None:
            self._setup_repo()
        return cast("RepoType", self._repo)

    def get_last_commit_diff(self, ignore_patterns: Optional[List[str]] = None) -> str:
        """Get the diff for the last commit.

        Args:
            ignore_patterns: List of file patterns to ignore

        Returns:
            Git diff as string
        """
        try:
            last_commit = self.repo.head.commit

            if last_commit.parents:
                parent_commit = last_commit.parents[0]
                diff = self.repo.git.diff(parent_commit.hexsha, last_commit.hexsha)
            else:
                diff = self.repo.git.diff(
                    "4b825dc642cb6eb9a060e54bf8d69288fbee4904", last_commit.hexsha
                )

            if ignore_patterns:
                diff = self._filter_diff_by_patterns(diff, ignore_patterns)

            return diff

        except GitCommandError as e:
            logger.error(f"Failed to get git diff: {e}")
            raise GitClientError(f"Failed to get git diff: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting git diff: {e}")
            raise GitClientError(f"Unexpected error getting git diff: {e}")

    def get_diff_between_commits(
        self, from_commit: str, to_commit: str = "HEAD"
    ) -> str:
        """Get diff between two commits.

        Args:
            from_commit: Starting commit hash or reference
            to_commit: Ending commit hash or reference (default: HEAD)

        Returns:
            Git diff as string
        """
        try:
            diff = self.repo.git.diff(from_commit, to_commit)
            return diff
        except GitCommandError as e:
            logger.error(
                f"Failed to get diff between {from_commit} and {to_commit}: {e}"
            )
            raise GitClientError(f"Failed to get diff between commits: {e}")

    def get_last_commit_info(self) -> Dict[str, Any]:
        """Get information about the last commit.

        Returns:
            Dictionary with commit information
        """
        try:
            last_commit = self.repo.head.commit

            return {
                "hash": last_commit.hexsha,
                "short_hash": last_commit.hexsha[:8],
                "message": last_commit.message.strip(),
                "author": {
                    "name": last_commit.author.name,
                    "email": last_commit.author.email,
                },
                "committer": {
                    "name": last_commit.committer.name,
                    "email": last_commit.committer.email,
                },
                "timestamp": last_commit.committed_datetime,
                "files_changed": self._get_changed_files(last_commit),
            }
        except Exception as e:
            logger.error(f"Failed to get commit info: {e}")
            raise GitClientError(f"Failed to get commit info: {e}")

    def get_changed_files(self, commit_hash: Optional[str] = None) -> List[str]:
        """Get list of files changed in a commit.

        Args:
            commit_hash: Commit to analyze (default: last commit)

        Returns:
            List of changed file paths
        """
        try:
            if commit_hash:
                commit = self.repo.commit(commit_hash)
            else:
                commit = self.repo.head.commit

            return self._get_changed_files(commit)
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            raise GitClientError(f"Failed to get changed files: {e}")

    def _get_changed_files(self, commit) -> List[str]:
        """Get list of files changed in a specific commit."""
        try:
            if commit.parents:
                parent = commit.parents[0]
                diff_index = parent.diff(commit)
            else:
                diff_index = commit.diff("4b825dc642cb6eb9a060e54bf8d69288fbee4904")

            changed_files = []
            for diff_item in diff_index:
                if diff_item.a_path:
                    changed_files.append(diff_item.a_path)
                if diff_item.b_path and diff_item.b_path != diff_item.a_path:
                    changed_files.append(diff_item.b_path)

            return list(set(changed_files))
        except Exception as e:
            logger.warning(f"Failed to get changed files for commit: {e}")
            return []

    def _filter_diff_by_patterns(self, diff: str, ignore_patterns: List[str]) -> str:
        """Filter diff content by removing ignored file patterns."""
        if not ignore_patterns:
            return diff

        lines = diff.split("\n")
        filtered_lines = []
        current_file = None
        skip_file = False

        for line in lines:
            if line.startswith("diff --git"):
                parts = line.split(" ")
                if len(parts) >= 4:
                    current_file = parts[3][2:]

                    skip_file = any(
                        self._match_pattern(current_file, pattern)
                        for pattern in ignore_patterns
                    )

                if not skip_file:
                    filtered_lines.append(line)
            elif not skip_file:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _match_pattern(self, filepath: str, pattern: str) -> bool:
        """Check if a file path matches an ignore pattern."""
        import fnmatch

        return fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(
            os.path.basename(filepath), pattern
        )

    def is_clean_working_tree(self) -> bool:
        """Check if the working tree is clean (no uncommitted changes)."""
        try:
            return not self.repo.is_dirty() and not self.repo.untracked_files
        except Exception as e:
            logger.warning(f"Failed to check working tree status: {e}")
            return False

    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        try:
            return self.repo.active_branch.name
        except Exception as e:
            logger.warning(f"Failed to get current branch: {e}")
            return "unknown"

    def get_repo_name(self) -> str:
        """Get the repository name."""
        return self.repo_path.name

    def install_post_commit_hook(self, hook_script_path: Path) -> bool:
        """Install a post-commit hook script.

        Args:
            hook_script_path: Path to the hook script to install

        Returns:
            True if installation successful, False otherwise
        """
        try:
            hooks_dir = self.repo_path / ".git" / "hooks"
            hook_file = hooks_dir / "post-commit"

            hooks_dir.mkdir(exist_ok=True)

            import shutil

            shutil.copy2(hook_script_path, hook_file)

            hook_file.chmod(0o755)

            logger.info(f"Post-commit hook installed at {hook_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to install post-commit hook: {e}")
            return False

    def install_prepare_commit_msg_hook(self, hook_script_path: Path) -> bool:
        """Install a prepare-commit-msg hook script."""
        try:
            hooks_dir = self.repo_path / ".git" / "hooks"
            hook_file = hooks_dir / "prepare-commit-msg"

            hooks_dir.mkdir(exist_ok=True)

            import shutil

            shutil.copy2(hook_script_path, hook_file)

            hook_file.chmod(0o755)

            logger.info(f"Prepare-commit-msg hook installed at {hook_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to install prepare-commit-msg hook: {e}")
            return False

    def create_post_commit_hook_script(self, output_path: Path) -> bool:
        """Create a post-commit hook script that calls CommitLM.

        Args:
            output_path: Where to save the hook script

        Returns:
            True if script created successfully
        """
        try:
            hook_content = """#!/bin/bash
# CommitLM Post-Commit Hook
# This script automatically generates documentation after each commit

# Exit on any error
set -e

# Get the repository root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Check if CommitLM is configured
if [ ! -f ".commitlm-config.json" ]; then
    echo "CommitLM: No configuration found, skipping documentation generation"
    exit 0
fi

# Generate documentation from the last commit
echo "CommitLM: Generating documentation for latest commit..."

# Get the commit hash
COMMIT_HASH="$(git rev-parse HEAD)"
COMMIT_SHORT="$(git rev-parse --short HEAD)"
COMMIT_MSG="$(git log -1 --pretty=format:'%s')"

# Get the diff for the last commit
DIFF_OUTPUT="$(git show --no-merges --format="" $COMMIT_HASH)"

# Skip if no changes (merge commits, etc.)
if [ -z "$DIFF_OUTPUT" ]; then
    echo "CommitLM: No changes to document, skipping"
    exit 0
fi

# Create docs directory if it doesn't exist
mkdir -p docs

# Sanitize commit message for use in filename
# Convert to lowercase, replace spaces with hyphens, remove special chars, truncate
SANITIZED_MSG=$(echo "$COMMIT_MSG" | \\
    tr '[:upper:]' '[:lower:]' | \\
    sed 's/[^a-z0-9 -]//g' | \\
    sed 's/ /-/g' | \\
    sed 's/--*/-/g' | \\
    cut -c1-50)

# Remove trailing hyphens
SANITIZED_MSG=$(echo "$SANITIZED_MSG" | sed 's/-*$//')

# Fallback to "unnamed" if sanitization results in empty string
if [ -z "$SANITIZED_MSG" ]; then
    SANITIZED_MSG="unnamed"
fi

# Generate filename with sanitized message and short hash for uniqueness
DOC_FILENAME="docs/commit_${SANITIZED_MSG}_${COMMIT_SHORT}.md"

# Use commitlm global command
commitlm generate \\
    --output "$DOC_FILENAME" \\
    "$DIFF_OUTPUT" \\
    2>/dev/null || {
    echo "CommitLM: Failed to generate documentation"
    exit 1
}

# Add metadata header to the generated file
GENERATED_DATE="$(date)"
REPO_NAME="$(basename "$REPO_ROOT")"
TEMP_FILE="${DOC_FILENAME}.tmp"
cat > "$TEMP_FILE" << EOF
# Documentation for Commit $COMMIT_SHORT

**Commit Hash:** $COMMIT_HASH
**Commit Message:** $COMMIT_MSG
**Generated:** $GENERATED_DATE
**Repository:** $REPO_NAME

---

EOF

# Append the generated documentation
cat "$DOC_FILENAME" >> "$TEMP_FILE"
mv "$TEMP_FILE" "$DOC_FILENAME"

echo "CommitLM: Documentation generated at $DOC_FILENAME"
"""

            # Write the hook script
            with open(output_path, "w") as f:
                f.write(hook_content)

            # Make it executable
            output_path.chmod(0o755)

            logger.info(f"Post-commit hook script created at {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create post-commit hook script: {e}")
            return False

    def create_prepare_commit_msg_hook_script(self, output_path: Path) -> bool:
        """Create a prepare-commit-msg hook script that calls CommitLM."""
        try:
            hook_content = """#!/bin/bash
# CommitLM Generator Prepare-Commit-Msg Hook

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2
COMMIT_SHA=$3

# Only run if no message is specified via -m or -F
if [ "$COMMIT_SOURCE" != "message" ]; then
    # Check if the feature is enabled in the config
    if grep -q '"enabled": true' .commitlm-config.json 2>/dev/null; then
        # Get staged diff
        DIFF_OUTPUT=$(git diff --cached)

        if [ -n "$DIFF_OUTPUT" ]; then
            # Call commitlm to generate message
            GENERATED_MSG=$(echo "$DIFF_OUTPUT" | commitlm generate --short-message)

            # Write message to commit message file
            echo "$GENERATED_MSG" > "$COMMIT_MSG_FILE"
        fi
    fi
fi
"""
            with open(output_path, "w") as f:
                f.write(hook_content)

            output_path.chmod(0o755)
            logger.info(f"Prepare-commit-msg hook script created at {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create prepare-commit-msg hook script: {e}")
            return False


def get_git_client(repo_path: Optional[Path] = None) -> GitClient:
    """Convenience function to get a git client."""
    return GitClient(repo_path)


def extract_commit_diff(repo_path: Optional[Path] = None) -> str:
    """Extract the diff from the last commit."""
    client = get_git_client(repo_path)
    return client.get_last_commit_diff()
