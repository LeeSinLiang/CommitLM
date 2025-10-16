# Contributing to CommitLM

First off, thank you for considering contributing to CommitLM! It's people like you that make CommitLM such a great tool.

Following these guidelines helps to communicate that you respect the time of the developers managing and developing this open source project. In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests.

## Code of Conduct

This project and everyone participating in it is governed by the [CommitLM Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for CommitLM. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

*   **Use a clear and descriptive title** for the issue to identify the problem.
*   **Describe the steps to reproduce the bug** in as much detail as possible.
*   **Provide specific examples** to demonstrate the steps.
*   **Describe the behavior you observed after following the steps** and what you expected to see instead.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for CommitLM, including completely new features and minor improvements to existing functionality.

*   **Use a clear and descriptive title** for the issue to identify the suggestion.
*   **Provide a step-by-step description of the suggested enhancement** in as much detail as possible.
*   **Provide specific examples to demonstrate the steps.**
*   **Explain why this enhancement would be useful** to most CommitLM users.

## Getting Started

To get started with development, you'll need to have Python 3.9+ installed.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/CommitLM.git
    cd CommitLM
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv env
    source env/bin/activate
    ```
3.  **Install the dependencies:**
    ```bash
    pip install -e .
    ```
4.  **Configure the tool:**
    ```bash
    commitlm init
    ```

## Pull Request Process

1.  Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2.  Update the README.md with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters.
3.  Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent. The versioning scheme we use is [SemVer](http://semver.org/).
4.  You may merge the Pull Request in once you have the sign-off of two other developers, or if you do not have permission to do that, you may request the second reviewer to merge it for you.

## Styleguides

### Git Commit Messages

*	That's what CommitLM is for :) Use `git c` to generate conventional commit messages. 

### Python Styleguide

All Python code must adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/). We use `ruff` to check for linting errors.
