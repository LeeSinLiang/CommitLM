"""Prompt templates and management for AI docs generator."""

from typing import Dict, Optional
from jinja2 import Template
from pathlib import Path
import json


class PromptTemplate:
    """A prompt template with Jinja2 support."""

    def __init__(self, name: str, template: str, description: str = ""):
        self.name = name
        self.template = Template(template)
        self.description = description

    def render(self, **kwargs) -> str:
        """Render the template with provided variables."""
        return self.template.render(**kwargs)


class PromptManager:
    """Manages prompt templates for different documentation scenarios."""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default prompt templates."""

        self.register_template(
            "documentation_generation",
            """You are a technical documentation expert. Analyze the provided git diff and generate comprehensive, professional documentation.

{% if max_tokens -%}
**Output Length Limit:** You have a maximum of {{ max_tokens }} tokens for your response. Please ensure your documentation is complete within this limit while maintaining quality and clarity.

{% endif -%}
{% if file_context -%}
**File Context:**
{{ file_context }}

{% endif -%}
**Git Diff:**
```diff
{{ diff_content }}
```

**Instructions:**
Generate clear, well-structured documentation that includes:

1. **Summary**: Brief overview of what changed and why
2. **Changes**: Detailed explanation of modifications, additions, or deletions
3. **Impact**: How these changes affect the codebase or functionality
4. **Usage**: Examples and usage instructions for new features
5. **Breaking Changes**: Any backward compatibility issues (if applicable)
6. **Migration Notes**: Steps needed to adapt to changes (if applicable)

**Requirements:**
- Use clear, concise language appropriate for developers
- Format output as clean Markdown with proper headers
- Include code examples where relevant
- Focus on practical information developers need
- Highlight important changes or deprecations
{% if max_tokens -%}
- Keep response within {{ max_tokens }} tokens - structure content appropriately
{% endif %}

**Output Format:**
Format your response as professional Markdown documentation.""",
            "Main template for generating documentation from git diffs",
        )

        self.register_template(
            "change_analysis",
            """Analyze the following git diff and provide a structured analysis of the changes.

**Git Diff:**
```diff
{{ diff_content }}
```

Please provide:

1. **Change Type**: (feature, bugfix, refactor, docs, test, etc.)
2. **Scope**: What parts of the system are affected
3. **Complexity**: Low/Medium/High complexity rating
4. **Files Modified**: List of changed files and their roles
5. **Key Changes**: Most important modifications
6. **Dependencies**: Any new dependencies or changes to existing ones
7. **Testing**: What should be tested based on these changes

Keep your analysis concise and technical.""",
            "Analyzes git diffs for change classification and impact assessment",
        )

        self.register_template(
            "api_documentation",
            """Generate API documentation based on the code changes in the git diff.

{% if file_context -%}
**File Context:**
{{ file_context }}

{% endif -%}
**Git Diff:**
```diff
{{ diff_content }}
```

Focus on documenting:

1. **New API Endpoints** (if any):
   - Method and URL
   - Parameters and request body
   - Response format and status codes
   - Example requests/responses

2. **Modified API Endpoints** (if any):
   - What changed
   - Migration notes for clients
   - Backward compatibility notes

3. **New Functions/Methods** (if any):
   - Function signature
   - Parameters and return values
   - Usage examples
   - Error conditions

4. **Data Models** (if any):
   - Schema changes
   - Field descriptions
   - Validation rules

Format as clear Markdown with code examples.""",
            "Generates API-focused documentation for code changes",
        )

        self.register_template(
            "release_notes",
            """Generate release notes based on the provided git diff.

**Git Diff:**
```diff
{{ diff_content }}
```

{% if version -%}
**Version:** {{ version }}
{% endif -%}

Create release notes with these sections:

## 🎉 New Features
- List any new functionality added

## 🔧 Improvements  
- List enhancements to existing features

## 🐛 Bug Fixes
- List bug fixes and resolved issues

## ⚠️ Breaking Changes
- List any breaking changes (if applicable)
- Include migration instructions

## 📝 Documentation
- List documentation updates

## 🔨 Internal Changes
- List refactoring, code cleanup, or internal improvements

**Guidelines:**
- Use bullet points for easy reading
- Be concise but informative
- Focus on user-facing changes
- Include relevant issue numbers if mentioned in commits
- Use emojis to make it more engaging

Format as Markdown suitable for GitHub releases.""",
            "Generates user-friendly release notes from git changes",
        )

        self.register_template(
            "code_review_summary",
            """Provide a code review summary based on the git diff.

**Git Diff:**
```diff
{{ diff_content }}
```

**Review Summary:**

1. **Overall Assessment**: Brief overview of the changes
2. **Code Quality**: Comments on code structure, readability, and maintainability
3. **Potential Issues**: Any concerns or suggestions for improvement
4. **Security Considerations**: Security implications (if any)
5. **Performance Impact**: Potential performance effects
6. **Testing Recommendations**: What should be tested
7. **Documentation Needs**: What documentation should be updated

Keep the review constructive and focused on helping improve the code.""",
            "Provides code review-style analysis of changes",
        )

        self.register_template(
            "commit_message",
            """Generate a clear, conventional commit message based on the git diff.

**Git Diff:**
```diff
{{ diff_content }}
```

**Guidelines:**
- Use conventional commits format: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore
- Keep the summary line under 50 characters
- Add a detailed body if needed (wrapped at 72 characters)
- Include breaking change notes if applicable

**Format:**
```
type(scope): brief description

Optional longer description explaining the change in more detail.
Wrap at 72 characters per line.

BREAKING CHANGE: describe breaking change if applicable
```

Provide only the commit message, nothing else.""",
            "Generates conventional commit messages from git diffs",
        )

        self.register_template(
            "short_commit_message",
            """Generate a single-line, conventional commit message based on the git diff.

**Git Diff:**
```diff
{{ diff_content }}
```

**Instructions:**
- Follow the conventional commits format: `type(scope): description`
- The entire commit message must be a single line.
- Do NOT include a body or any extra explanation.
- Choose the most appropriate type (feat, fix, docs, style, refactor, test, chore).
- The scope should be a short identifier of the code section affected.
- The description should be a concise summary of the change.

**Example:**
`feat(api): add new user authentication endpoint`

**Your output must be only the single-line commit message.**""",
            "Generates a single-line conventional commit message from git diffs",
        )

    def register_template(self, name: str, template: str, description: str = ""):
        """Register a new prompt template."""
        self._templates[name] = PromptTemplate(name, template, description)

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self._templates.get(name)

    def render_prompt(self, template_name: str, **kwargs) -> str:
        """Render a prompt template with provided variables."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        return template.render(**kwargs)

    def list_templates(self) -> Dict[str, str]:
        """List all available templates with their descriptions."""
        return {
            name: template.description for name, template in self._templates.items()
        }

    def load_template_from_file(
        self, name: str, file_path: Path, description: str = ""
    ):
        """Load a template from a file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Template file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        self.register_template(name, template_content, description)

    def save_template_to_file(self, name: str, file_path: Path):
        """Save a template to a file."""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")

        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(template.template.source)

    def export_templates(self, output_path: Path):
        """Export all templates to a JSON file."""
        templates_data = {}
        for name, template in self._templates.items():
            templates_data[name] = {
                "template": template.template.source,
                "description": template.description,
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(templates_data, f, indent=2, ensure_ascii=False)

    def import_templates(self, input_path: Path):
        """Import templates from a JSON file."""
        if not input_path.exists():
            raise FileNotFoundError(f"Template file not found: {input_path}")

        with open(input_path, "r", encoding="utf-8") as f:
            templates_data = json.load(f)

        for name, template_info in templates_data.items():
            self.register_template(
                name, template_info["template"], template_info.get("description", "")
            )


_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def render_documentation_prompt(
    diff_content: str,
    file_context: str = "",
    template_name: str = "documentation_generation",
    max_tokens: Optional[int] = None,
) -> str:
    """Convenience function to render documentation generation prompt."""
    manager = get_prompt_manager()
    kwargs: Dict[str, object] = {
        "diff_content": diff_content,
        "file_context": file_context,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    return manager.render_prompt(template_name, **kwargs)


def render_analysis_prompt(
    diff_content: str, template_name: str = "change_analysis"
) -> str:
    """Convenience function to render change analysis prompt."""
    manager = get_prompt_manager()
    return manager.render_prompt(template_name, diff_content=diff_content)


def render_api_docs_prompt(diff_content: str, file_context: str = "") -> str:
    """Convenience function to render API documentation prompt."""
    manager = get_prompt_manager()
    return manager.render_prompt(
        "api_documentation", diff_content=diff_content, file_context=file_context
    )


def render_release_notes_prompt(diff_content: str, version: str = "") -> str:
    """Convenience function to render release notes prompt."""
    manager = get_prompt_manager()
    return manager.render_prompt(
        "release_notes", diff_content=diff_content, version=version
    )


def render_commit_message_prompt(diff_content: str) -> str:
    """Convenience function to render commit message prompt."""
    manager = get_prompt_manager()
    return manager.render_prompt("commit_message", diff_content=diff_content)


def get_available_templates() -> Dict[str, str]:
    """Get list of available prompt templates."""
    manager = get_prompt_manager()
    return manager.list_templates()


def render_short_commit_message_prompt(diff_content: str) -> str:
    """Convenience function to render the short commit message prompt."""
    manager = get_prompt_manager()
    return manager.render_prompt("short_commit_message", diff_content=diff_content)
