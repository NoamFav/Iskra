# autocommit

A beautiful, feature-rich Git automation toolkit that combines Go performance with Python elegance. Autocommit streamlines your Git workflow with AI-powered commit messages, bulk repository management, and stunning terminal UI.

## ✨ Features

### 🤖 AI-Powered Commits (`ai_commit`)
- **Smart Commit Messages**: Generates conventional commit messages using local LLM (Ollama)
- **Context-Aware**: Analyzes your git diff and branch to suggest appropriate commit types
- **Conventional Commits**: Follows the `<type>(<scope>): <subject>` format
- **Fast**: Written in Go for lightning-fast execution
- **Automatic Push**: Stages, commits, and pushes in one command

### 📦 Bulk Repository Manager (`autocommit`)
- **Multi-Repo Operations**: Process multiple git repositories at once
- **Beautiful UI**: Rich terminal interface with progress tracking and colored output
- **Flexible Filtering**: Include/exclude specific repositories
- **DS_Store Cleanup**: Automatically handle macOS .DS_Store files
- **Git Operations**: Pull, commit, and push across all repositories

### 🔄 GitHub Clone Manager (`pull_repos`)
- **Batch Cloning**: Clone all your GitHub repositories at once
- **Smart Filtering**: Filter by stars, forks, privacy status
- **Repository Stats**: Shows file counts, directory structure, and repository size
- **GitHub CLI Integration**: Uses `gh` CLI for authenticated access

## 🚀 Installation

### Prerequisites
- Python 3.9+
- Go 1.16+ (for building from source)
- [Ollama](https://ollama.ai/) (optional, for AI commit messages)
- [GitHub CLI](https://cli.github.com/) (optional, for `pull_repos`)

### Install from Source

```bash
# Clone the repository
git clone <your-repo-url>
cd autocommit/python

# Build and install
pip install -e .
```

The installation process will automatically:
1. Build the Go binary (`ai_commit`)
2. Bundle it with the Python package
3. Install all three command-line tools

## 📖 Usage

### `ai_commit` - Smart Git Commits

Basic usage with AI-generated commit message:
```bash
ai_commit
```

Specify a custom message:
```bash
ai_commit -m "feat(api): add user authentication"
```

Pull before committing:
```bash
ai_commit --pull
```

#### Environment Variables
- `OLLAMA_MODEL`: Ollama model to use (default: `mistral`)
- `OLLAMA_URL`: Ollama API endpoint (default: `http://127.0.0.1:11434`)

#### How It Works
1. Stages all changes with `git add .`
2. Analyzes your git diff to detect change type (feat/fix/refactor/chore)
3. Uses the current branch as scope
4. Sends context to Ollama for commit message generation
5. Commits with generated message
6. Pushes to remote

### `autocommit` - Bulk Repository Manager

Process all repositories in a directory:
```bash
autocommit --dir ~/Projects
```

With AI-generated commit messages:
```bash
autocommit --commit-message "auto-commit"
```

Pull before committing:
```bash
autocommit --pull
```

Clean up .DS_Store files:
```bash
autocommit --remove-ds-store --handle-gitignore
```

Filter repositories:
```bash
# Process only specific repos
autocommit --only repo1 repo2 repo3

# Exclude specific repos
autocommit --exclude old-project archive
```

Use manual git commands instead of ai_commit:
```bash
autocommit --no-auto-commit
```

#### Options
- `--dir`: Base directory containing git repositories (default: `~/Neoware`)
- `--commit-message`: Commit message or 'auto-commit' for AI generation
- `--pull`: Pull changes before committing
- `--handle-gitignore`: Ensure .gitignore includes .DS_Store
- `--remove-ds-store`: Remove .DS_Store files from repositories
- `--exclude`: List of directories to exclude
- `--only`: Process only these directories
- `--no-auto-commit`: Use manual git commands instead of ai_commit

### `pull_repos` - GitHub Clone Manager

Clone all your GitHub repositories:
```bash
pull_repos
```

Specify target directory:
```bash
pull_repos --base-dir ~/GitHub
```

Filter repositories:
```bash
# Only repos with 10+ stars
pull_repos --only-stars 10

# Exclude forks
pull_repos --filter-forks

# Exclude specific repos
pull_repos --exclude repo1 repo2
```

Set repository limit:
```bash
pull_repos --limit 50
```

#### Options
- `--base-dir`: Target directory for cloning (default: `~/Neoware`)
- `--limit`: Maximum number of repositories to fetch (default: 1000)
- `--filter-forks`: Exclude forked repositories
- `--only-stars`: Minimum star count
- `--exclude`: List of repository names to exclude

## 🎨 Features Showcase

### Beautiful Terminal UI
- **Rich Formatting**: Colored output with icons and borders
- **Progress Tracking**: Real-time status updates
- **Tree Views**: Visual file change summaries
- **Panels & Tables**: Organized information display
- **Error Handling**: Clear, formatted error messages

### Smart Commit Detection
The `ai_commit` tool analyzes your changes to suggest commit types:
- **feat**: More additions than deletions
- **fix**: Diff contains "fix" or "bug"
- **refactor**: Diff contains "refactor" or more deletions than additions
- **chore**: Default fallback

### Conventional Commits
All AI-generated commits follow the conventional commit format:
```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
```

## 🏗️ Architecture

The project combines Go and Python for optimal performance:

```
autocommit/
├── python/
│   ├── src/auto_commit/
│   │   ├── __init__.py
│   │   ├── ai_commit.py          # Binary wrapper
│   │   ├── auto_commit.py        # Bulk repo manager
│   │   └── pull_repos.py         # GitHub clone tool
│   ├── gocli/
│   │   ├── cmd/auto_commit/      # Go binary source
│   │   ├── internal/git/         # Git operations
│   │   └── internal/llm/         # Ollama integration
│   ├── setup.py                  # Build configuration
│   └── pyproject.toml           # Package metadata
```

### Why Go + Python?
- **Go**: Fast git operations and LLM API calls
- **Python**: Rich terminal UI and convenient scripting
- **Best of Both**: Performance where it matters, convenience everywhere else

## 🔧 Configuration

### Ollama Setup
For AI commit messages, install and run Ollama:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull mistral

# Ensure Ollama is running
ollama serve
```

### GitHub CLI Setup
For repository cloning:

```bash
# Install GitHub CLI
# macOS: brew install gh
# Other: https://cli.github.com/

# Authenticate
gh auth login
```

## 🤝 Contributing

Contributions are welcome! This project is structured to make it easy to:
- Add new Git automation features
- Improve the terminal UI
- Extend LLM integrations
- Support additional platforms

## 📝 License

[Add your license here]

## 🙏 Acknowledgments

- Built with [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- Powered by [Ollama](https://ollama.ai/) for local LLM inference
- Integrated with [GitHub CLI](https://cli.github.com/) for repository management

---

**Made with ❤️ for developers who love automation**