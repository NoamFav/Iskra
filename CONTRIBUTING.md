# Contributing to Iskra

First off, thank you for considering contributing to Iskra! It's people like you that make Iskra such a great tool for managing Git repositories.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project and everyone participating in it is governed by the [Iskra Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [noamfav@nf-software.com](mailto:noamfav@nf-software.com).

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **Go 1.22+** - [Download Go](https://golang.org/dl/)
- **Git** - [Download Git](https://git-scm.com/downloads)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/Iskra.git
cd Iskra
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/NoamFav/Iskra.git
```

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (code snippets, configuration files)
- **Describe the behavior you observed and what you expected**
- **Include your environment details** (OS, Python version, Go version)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the proposed enhancement**
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Your First Code Contribution

Unsure where to begin? Look for issues labeled:

- `good first issue` - Simple issues for newcomers
- `help wanted` - Issues that need community help
- `documentation` - Documentation improvements

## Development Setup

### 1. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### 3. Build the Go Binary

```bash
cd gocli
go build -o ../src/iskra/bin/ai_commit ./cmd/iskra
cd ..
```

### 4. Verify Installation

```bash
iskra --help
```

### 5. Run Tests

```bash
pytest
```

### 6. Run Linters

```bash
# Python
flake8 src/
black --check src/

# Go
cd gocli
go fmt ./...
go vet ./...
```

## Style Guidelines

### Python Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting
- Maximum line length: 79 characters
- Use type hints where appropriate
- Write docstrings for all public functions, classes, and modules

```python
def process_repository(path: str, config: Config) -> ProcessingResult:
    """
    Process a single Git repository.

    Args:
        path: Absolute path to the repository.
        config: Configuration object with processing options.

    Returns:
        ProcessingResult containing the operation outcome.

    Raises:
        RepositoryNotFoundError: If the path is not a valid Git repository.
    """
    ...
```

### Go Code Style

- Follow standard Go conventions
- Use `gofmt` for formatting
- Use `go vet` for static analysis
- Write comments for exported functions and types

### Documentation Style

- Use Markdown for documentation
- Keep line lengths reasonable (< 120 characters)
- Include code examples where helpful
- Update the README if adding new features

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code refactoring (no feature or fix)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build, etc.)

### Examples

```
feat(ai): add Claude API provider support

Add support for Anthropic's Claude API as an alternative
to Ollama for commit message generation.

Closes #42
```

```
fix(git): resolve SSH key detection on Windows

The SSH agent check was failing on Windows due to
incorrect path handling.
```

## Pull Request Process

### Before Submitting

1. **Update your fork** with the latest upstream changes:

```bash
git fetch upstream
git rebase upstream/main
```

2. **Create a feature branch**:

```bash
git checkout -b feature/your-feature-name
```

3. **Make your changes** following the style guidelines

4. **Run tests and linters**:

```bash
pytest
flake8 src/
black src/
```

5. **Commit your changes** using conventional commits

### Submitting the PR

1. Push your branch to your fork:

```bash
git push origin feature/your-feature-name
```

2. Open a Pull Request on GitHub

3. Fill out the PR template with:
   - A clear description of changes
   - Link to related issues
   - Screenshots (if applicable)
   - Testing instructions

### Review Process

1. A maintainer will review your PR
2. Address any requested changes
3. Once approved, your PR will be merged

### After Merge

- Delete your feature branch
- Update your local main branch:

```bash
git checkout main
git pull upstream main
```

## Questions?

Feel free to open an issue with the `question` label or reach out to the maintainers.

---

Thank you for contributing to Iskra! ⚡
