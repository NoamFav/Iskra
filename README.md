# ⚡ Iskra




<div align="center">

<img src="https://img.shields.io/badge/version-1.0.0-blue.svg?style=for-the-badge" alt="Version">
<img src="https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge" alt="License">
<img src="https://img.shields.io/badge/python-3.8+-blue.svg?style=for-the-badge&logo=python" alt="Python">
<img src="https://img.shields.io/badge/go-1.22+-00ADD8.svg?style=for-the-badge&logo=go" alt="Go">

**Intelligent multi-repository Git automation tool with AI-powered commit messages**

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Support](#-support)

---

</div>

## 🎯 Overview

Iskra is a powerful command-line tool designed to manage multiple Git repositories with unprecedented efficiency. It combines intelligent repository tracking, AI-powered commit message generation, and streamlined Git operations into a single, elegant interface.

### Why Iskra?

- **Time-Saving**: Manage 100+ repositories in seconds instead of hours
- **Intelligent**: AI understands your changes and writes meaningful commit messages
- **Flexible**: Works with your workflow, not against it
- **Beautiful**: Rich terminal UI with progress indicators and colored output
- **Safe**: Dry-run mode, confirmations, and detailed logging keep you in control

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 **Smart Repository Tracking**

- Track repositories once, use everywhere
- Automatic discovery and scanning
- Per-repository configuration overrides
- Active/inactive repository management

### 🤖 **AI-Powered Commits**

- Intelligent commit message generation via Ollama
- Conventional commit format support
- Context-aware type detection
- Multi-provider support (Ollama, Claude, OpenAI)

### 🔄 **Batch Operations**

- Process multiple repositories simultaneously
- Flexible filtering with glob patterns
- Skip unchanged repositories automatically
- Pull before commit, push after commit

</td>
<td width="50%">

### 🎨 **Beautiful Terminal UI**

- Rich formatting with colors and icons
- Real-time progress indicators
- Detailed operation summaries
- Tree view of file changes

### ⚙️ **Flexible Configuration**

- Global and per-repository settings
- Multiple configuration profiles
- YAML-based configuration files
- Environment variable support

### 🛡️ **Safety First**

- Dry-run mode to preview actions
- Confirmation prompts for critical operations
- Protected branch detection
- Detailed operation logging

</td>
</tr>
</table>

---

## 📦 Installation

### Prerequisites

Before installing Iskra, ensure you have:

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **Go 1.22+** - [Download Go](https://golang.org/dl/) (for AI commit binary)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **Ollama** (optional) - [Download Ollama](https://ollama.ai) (for AI commit messages)

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/NoamFav/Iskra/main/script/install.sh | bash
```

Or download and inspect first:

```bash
wget https://raw.githubusercontent.com/NoamFav/Iskra/main/script/install.sh
chmod +x install.sh
./install.sh
```

### Install from Source

```bash
# Clone the repository
git clone https://github.com/NoamFav/Iskra.git
cd Iskra

# Install with pip
pip install -e .

# Verify installation
iskra --help
```

### Available Commands

After installation, you'll have access to:

| Command       | Description                           |
| ------------- | ------------------------------------- |
| `iskra`       | Main repository automation tool       |
| `iskra exec`  | Run any command across all repos      |
| `iskra log`   | Git history viewer with rich formatting |
| `iskra info`  | Repository stats display (like onefetch) |
| `iskra-init`  | Configuration and repository tracking |
| `ai_commit`   | AI-powered commit message generator   |
| `pull-repos`  | GitHub repository cloning tool        |

---

## 🚀 Quick Start

### 1️⃣ Initialize Iskra

Set up Iskra and scan for repositories in your projects directory:

```bash
iskra-init init --base-dir ~/Projects
```

This interactive wizard will:

- ✅ Create configuration at `~/.config/iskra/`
- ✅ Scan for all Git repositories in `~/Projects`
- ✅ Track discovered repositories
- ✅ Configure your preferences (AI commits, auto-push, etc.)

**Quick setup (skip interactive questions):**

```bash
iskra-init init --base-dir ~/Projects -y
```

### 2️⃣ View Tracked Repositories

See all repositories that Iskra is tracking:

```bash
iskra-init list
```

**Example output:**

```
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Name        ┃ Path              ┃ Branch ┃ Remote           ┃ Status  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ my-project  │ ~/Projects/my-... │ main   │ github.com/...   │ ✓ Active│
│ web-app     │ ~/Projects/web... │ main   │ github.com/...   │ ✓ Active│
└─────────────┴───────────────────┴────────┴──────────────────┴─────────┘
```

### 3️⃣ Process All Repositories

Run Iskra to commit and push changes across all tracked repositories:

```bash
iskra
```

**What happens:**

1. 🔍 Loads your tracked repositories
2. 🤖 Generates AI commit messages for changes
3. 💾 Commits with intelligent messages
4. 🚀 Pushes to remote repositories
5. 📊 Shows beautiful progress and summaries

---

## 📖 Documentation

### Main Command: `iskra`

The primary tool for processing repositories.

#### Basic Usage

```bash
# Process all tracked repositories
iskra

# Process with custom base directory
iskra --dir ~/OtherProjects

# Scan for repos instead of using tracked list
iskra --scan
```

#### Filtering Options

```bash
# Process only specific repositories
iskra --only "myproject*"

# Exclude certain repositories
iskra --exclude "test*" "temp*"

# Combine include and exclude
iskra --only "client-*" --exclude "*-archive"
```

#### Git Operations

```bash
# Pull latest changes before committing
iskra --pull

# Commit but don't push
iskra --no-push

# Use manual commit message instead of AI
iskra --no-ai-commit --commit-message "Update dependencies"
```

#### Safety & Preview

```bash
# Preview what would happen (no changes made)
iskra --dry-run

# Show file diffs before committing
iskra --show-diff

# Skip all confirmation prompts
iskra -y

# Only show status, don't commit
iskra --status-only
```

#### Special Operations

```bash
# Remove .DS_Store files and update .gitignore
iskra --remove-ds-store --handle-gitignore
```

### Configuration: `iskra-init`

Manage Iskra's configuration and tracked repositories.

#### Initialize

```bash
# Interactive initialization
iskra-init init --base-dir ~/Projects

# Quick initialization (accept defaults)
iskra-init init --base-dir ~/Projects -y

# Show tracked repos after initialization
iskra-init init --base-dir ~/Projects --show-repos
```

#### Manage Repositories

```bash
# List all tracked repositories
iskra-init list

# List including inactive repositories
iskra-init list --all

# Add a repository manually
iskra-init add ~/path/to/my-repo

# Remove a repository from tracking
iskra-init remove ~/path/to/my-repo
```

### Execute Commands: `iskra exec`

Run any git or shell command across all tracked repositories (like gita's "superman mode"):

```bash
# Git commands
iskra exec "git log --oneline -5"     # Last 5 commits per repo
iskra exec "git fetch --all"          # Fetch all remotes
iskra exec "git stash list"           # List stashes
iskra exec "git branch -a"            # Show all branches

# Shell commands
iskra exec "npm install"              # Install dependencies
iskra exec "make test"                # Run tests
iskra exec "ls -la"                   # List files

# With filters
iskra exec --only "api-*" "npm test"  # Only api repos
iskra exec --exclude "archive-*" "git pull"

# Options
iskra exec -y "git fetch"             # Skip confirmation
iskra exec --fail-fast "make build"   # Stop on first error
iskra exec -q "git status"            # Quiet mode
```

### Git History: `iskra log`

View git history for the current repository with beautiful formatting.

```bash
# Show last 20 commits (default)
iskra log

# Show more commits
iskra log -n 50

# Compact one-line format
iskra log --oneline

# Filter by author
iskra log --author "noam"

# Filter by date
iskra log --since "2 weeks ago"
iskra log --until "2024-01-01"

# Search commit messages
iskra log --grep "fix"

# Show ASCII branch graph
iskra log --graph

# Show commits from all branches
iskra log --all

# Combine options
iskra log -n 30 --author "noam" --oneline
```

### Repository Info: `iskra info`

Display repository statistics with ASCII art (inspired by [onefetch](https://github.com/o2sh/onefetch)).

```bash
# Show current repo info
iskra info
```

**Displays:**
- Language breakdown with percentages
- Lines of code count
- Total commits and contributors
- Repository size
- Current branch and remote URL
- ASCII art for the dominant language

**Custom Icon:** Place an `icon.png` in your repository root for custom ASCII art display instead of the language icon.

### GitHub Tools: `pull-repos`

Clone all your GitHub repositories at once.

```bash
# Clone all your GitHub repos
pull-repos --base-dir ~/GitHub

# Filter out forked repositories
pull-repos --filter-forks

# Only repos with 10+ stars
pull-repos --only-stars 10

# Exclude specific patterns
pull-repos --exclude "test-*" "archive-*"

# Limit number of repos to clone
pull-repos --limit 50
```

**Note:** Requires [GitHub CLI](https://cli.github.com/) (`gh`) to be installed and authenticated.

### AI Commit: `ai_commit`

Standalone AI-powered commit tool.

```bash
# Generate AI commit message and commit
cd my-repo
git add .
ai_commit

# Use custom message instead
ai_commit "fix: resolve authentication bug"

# Pull before committing
ai_commit --pull
```

---

## ⚙️ Configuration

### Global Configuration

Located at `~/.config/iskra/config.yaml`:

```yaml
# Base directory for repository operations
base_dir: ~/Projects

# Repository scanning
max_depth: 3
follow_symlinks: true

# Git operations
auto_pull: true
auto_push: true
auto_stash: false        # Stash local changes before pull, restore after
default_branch: main

# AI commit settings
use_ai_commit: true
commit_message_style: conventional
ai_provider: ollama      # Options: ollama, openai, claude

# OpenAI configuration (if ai_provider: openai)
openai_api_key: null     # Or set OPENAI_API_KEY env var
openai_model: gpt-4o-mini

# Claude configuration (if ai_provider: claude)
claude_api_key: null     # Or set ANTHROPIC_API_KEY env var
claude_model: claude-sonnet-4-20250514

# Safety & confirmation
require_confirmation: true
require_confirmation_for_protected: true
dry_run: false

# UI preferences
show_diff: false         # Show diff before committing
verbose: false
use_rich_ui: true

# Filtering
exclude_patterns: []
only_patterns: []

# Protected branches (warns before committing)
protected_branches:
  - main
  - master
  - production

# Safety checks
check_ssh_keys: true     # Warn if SSH remote but no keys in agent
warn_conflicts: true     # Check for merge conflicts before operations

# Special handling
handle_gitignore: false
remove_ds_store: false
```

### Per-Repository Configuration

Override global settings for specific repositories by creating `.iskra.yaml` in the repository root:

```yaml
# Disable AI commits for this repository
use_ai_commit: false

# Don't automatically push
auto_push: false

# Always require confirmation
require_confirmation: true

# Custom protected branches
protected_branches:
  - main
  - develop
  - staging
  - production

# Exclude specific files
exclude_files:
  - "*.log"
  - "temp/*"

# Custom commit template
custom_commit_template: "[{issue}] {message}"

# Pre/post commit hooks (shell commands)
pre_commit_command: "npm test"       # Runs before commit, fails commit if non-zero exit
post_commit_command: "npm run deploy" # Runs after successful commit
```

### Environment Variables

You can also configure Iskra using environment variables:

```bash
# AI Provider API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Ollama configuration
export OLLAMA_MODEL="mistral"        # Default model for Ollama
export OLLAMA_URL="http://127.0.0.1:11434"  # Ollama server URL
```

### Configuration Directory Structure

```
~/.config/iskra/
├── config.yaml          # Global configuration
├── repos.json           # Tracked repositories database
└── logs/                # Operation logs
    ├── iskra-20241128.log
    └── iskra-20241129.log
```

---

## 🤖 AI Commit Messages

Iskra supports multiple AI providers for generating intelligent, context-aware commit messages.

### Supported Providers

| Provider | Local/Cloud | Setup Required |
|----------|-------------|----------------|
| **Ollama** (default) | Local | Install Ollama + model |
| **OpenAI** | Cloud | API key |
| **Claude** | Cloud | API key |

### Setup Ollama (Default)

1. **Install Ollama:**

   ```bash
   # macOS
   brew install ollama

   # Or download from https://ollama.ai
   ```

2. **Pull a model:**

   ```bash
   ollama pull mistral
   # or
   ollama pull llama2
   ```

3. **Start Ollama (if not running):**
   ```bash
   ollama serve
   ```

### Setup OpenAI

```yaml
# In ~/.config/iskra/config.yaml
ai_provider: openai
openai_api_key: sk-...  # Or set OPENAI_API_KEY env var
openai_model: gpt-4o-mini  # Or gpt-4o, gpt-3.5-turbo
```

### Setup Claude

```yaml
# In ~/.config/iskra/config.yaml
ai_provider: claude
claude_api_key: sk-ant-...  # Or set ANTHROPIC_API_KEY env var
claude_model: claude-sonnet-4-20250514
```

### Smart Fallback

If AI generation fails, Iskra automatically falls back to generating smart commit messages based on file analysis:

- Detects file types (tests, docs, config, dependencies)
- Analyzes operations (added, modified, deleted)
- Generates appropriate conventional commit messages

**Examples of fallback messages:**
- `docs: update documentation`
- `test: add tests`
- `chore: update dependencies`
- `feat: add new-feature.py`

### How It Works

When you run `iskra` with AI commits enabled:

1. 📝 Analyzes your staged changes using `git diff`
2. 🔍 Detects the type of changes (feat, fix, refactor, etc.)
3. 🤖 Sends context to your configured AI provider
4. ✨ Receives an intelligent, conventional commit message
5. 💾 Commits with the generated message
6. ↩️ Falls back to smart message if AI fails

### Commit Message Format

Iskra follows the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Example outputs:**

- `feat(auth): add OAuth2 authentication flow`
- `fix(api): resolve null pointer exception in user handler`
- `docs(readme): update installation instructions`
- `refactor(database): optimize query performance`

### Customization

Configure AI behavior via environment variables:

```bash
# Ollama settings
export OLLAMA_MODEL=mistral

# Use a different Ollama instance
export OLLAMA_URL=http://192.168.1.100:11434
```

### Standalone Usage

Use the AI commit tool directly:

```bash
cd my-repository
git add .
ai_commit

# With custom message fallback
ai_commit "feat: add new feature"
```

---

## 🎯 Common Workflows

### Daily Commit Routine

Process all repositories with AI-generated commits:

```bash
# With confirmation prompts (safe)
iskra

# Quick mode (no prompts)
iskra -y
```

### Sync All Repositories

Pull latest changes from all tracked repositories:

```bash
iskra --pull --status-only
```

### Preview Before Committing

Use dry-run to see what would happen:

```bash
# Preview all operations
iskra --dry-run

# If satisfied, run for real
iskra
```

### Work on Specific Projects

Filter repositories by pattern:

```bash
# Only process client projects
iskra --only "client-*"

# Process everything except archives
iskra --exclude "archive-*" "temp-*"

# Combine filters
iskra --only "project-*" --exclude "*-test"
```

### Handle macOS .DS_Store Files

Clean up and prevent .DS_Store files:

```bash
iskra --remove-ds-store --handle-gitignore
```

### Manual Control

Disable AI and use custom messages:

```bash
iskra --no-ai-commit --commit-message "chore: update dependencies"
```

### Safe Operations on Protected Branches

Iskra automatically warns before committing to protected branches:

```bash
# Iskra will warn and require -y flag for protected branches
iskra
# Output: ⚠ Protected branch: main
#         Use -y to confirm operations on protected branches

# Confirm you want to commit to protected branch
iskra -y
```

### View Changes Before Committing

Use `--show-diff` to review changes:

```bash
# Show colored diff output before committing
iskra --show-diff
```

### Auto-Stash Workflow

Enable auto-stash to safely pull with local changes:

```yaml
# In config.yaml
auto_stash: true
```

```bash
# With auto_stash enabled:
# 1. Stashes your local changes
# 2. Pulls from remote
# 3. Restores your stashed changes
iskra --pull
```

---

## 🔧 Advanced Features

### Pre/Post Commit Hooks

Run commands before and after commits in specific repositories:

```yaml
# In .iskra.yaml (per-repository)
pre_commit_command: "npm test"
post_commit_command: "npm run notify"
```

- **Pre-commit**: Runs before commit. If it fails (non-zero exit), commit is aborted.
- **Post-commit**: Runs after successful commit. Failures are warnings only.

### Conflict Detection

Iskra checks for conflicts before operations:

```bash
# Warns if merge conflicts exist
# Output: ⚠ Merge conflicts detected in 3 file(s)
#         • src/file1.py
#         • src/file2.py
#         • src/file3.py

# Warns if pull would cause conflicts
# Output: ⚠ Pull would cause conflicts
#         Resolve manually or use --no-conflict-check
```

### SSH Key Detection

Iskra warns if you're using SSH remotes without keys:

```bash
# Output: ⚠ SSH remote but no keys in agent
#         Run: ssh-add ~/.ssh/id_rsa
```

### Glob Pattern Matching

Use powerful patterns to filter repositories:

```bash
# Match nested repositories
iskra --only "*/mobile-app"

# Multiple patterns
iskra --only "client-*" "api-*" "backend-*"

# Complex exclusions
iskra --exclude "*-test" "*-temp" "archive/*"

# Case-insensitive matching (depends on shell)
iskra --only "[Cc]lient-*"
```

### Repository-Specific Settings

Create `.iskra.yaml` in any repository for custom behavior:

```yaml
# Example: Disable auto-push for production repos
auto_push: false
require_confirmation: true

# Example: Use different commit style
commit_message_style: simple

# Example: Add custom validation
pre_commit_command: "make test"
```

### Status Checking

Monitor repository state without making changes:

```bash
# Show git status for all repos
iskra --status-only

# Show detailed diffs
iskra --show-diff --status-only

# Check which repos need pulling
iskra --pull --dry-run
```

### Batch Updates

Update multiple repositories efficiently:

```bash
# Pull all repos
iskra --pull --status-only

# Commit and push all changes
iskra -y

# Update specific category
iskra --only "backend-*" --pull
```

---

## 🐛 Troubleshooting

### No repositories found

**Problem:** `iskra` shows "No repositories found"

**Solutions:**

```bash
# Make sure you've initialized Iskra
iskra-init init --base-dir ~/Projects

# Or use scan mode
iskra --scan --dir ~/Projects

# Check tracked repos
iskra-init list
```

### AI commit not working

**Problem:** AI commit messages fail or show errors

**Solutions:**

```bash
# Check if Ollama is running
ollama list

# Start Ollama if needed
ollama serve

# Pull a model if missing
ollama pull llama2

# Test the binary directly
which ai_commit
ai_commit --help

# Check environment variables
echo $OLLAMA_MODEL
echo $OLLAMA_URL
```

### Configuration not loading

**Problem:** Settings don't seem to apply

**Solutions:**

```bash
# Check config file location
ls -la ~/.config/iskra/

# View current configuration
cat ~/.config/iskra/config.yaml

# Reinitialize if corrupted
mv ~/.config/iskra ~/.config/iskra.backup
iskra-init init --base-dir ~/Projects

# Check for per-repo overrides
cat .iskra.yaml  # in the problematic repo
```

### GitHub CLI issues

**Problem:** `pull-repos` fails

**Solutions:**

```bash
# Check if GitHub CLI is installed
which gh

# Install GitHub CLI
brew install gh  # macOS
# or visit https://cli.github.com/

# Authenticate
gh auth login

# Test connection
gh repo list --limit 5
```

### Permission errors

**Problem:** Cannot write to config directory

**Solutions:**

```bash
# Check permissions
ls -la ~/.config/

# Create directory if missing
mkdir -p ~/.config/iskra

# Fix permissions
chmod 755 ~/.config/iskra
```

### Git authentication issues

**Problem:** Push fails with authentication errors

**Solutions:**

```bash
# Check remote URL
git remote -v

# Update to SSH if using HTTPS
git remote set-url origin git@github.com:user/repo.git

# Or configure Git credential helper
git config --global credential.helper cache
```

---

## 📊 Logging

All operations are automatically logged for auditing and debugging.

### Log Location

Logs are stored in `~/.config/iskra/logs/`:

```bash
# View today's log
tail -f ~/.config/iskra/logs/iskra-$(date +%Y%m%d).log

# View all logs
ls -lh ~/.config/iskra/logs/

# Search for errors
grep "ERROR" ~/.config/iskra/logs/*.log

# Find specific operation
grep "processed" ~/.config/iskra/logs/*.log
```

### Log Format

Each log entry includes:

- 📅 Timestamp
- 📍 Operation type
- 📂 Repository path
- ✅ Success/failure status
- 📝 Details and error messages

**Example log entry:**

```
================================================================================
Run at: 2024-11-28T14:30:45.123456
Processed: 25/30 repositories
Base dir: /Users/noam/Projects
Mode: NORMAL
================================================================================
```

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Getting Started

1. **Fork the repository**

   ```bash
   gh repo fork NoamFav/Iskra
   ```

2. **Create a feature branch**

   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**

   - Write clean, documented code
   - Follow existing code style
   - Add tests if applicable

4. **Commit your changes**

   ```bash
   git commit -m "feat: add amazing feature"
   ```

5. **Push to your fork**

   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a Pull Request**
   - Describe your changes
   - Link related issues
   - Wait for review

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Iskra.git
cd Iskra

# Install in development mode
pip install -e ".[dev]"

# Run tests (when available)
pytest

# Format code
black src/
```

### Code Style

- **Python:** Follow PEP 8, use Black for formatting
- **Go:** Follow standard Go conventions, use `gofmt`
- **Commits:** Use Conventional Commits format
- **Documentation:** Update README and docstrings

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE.md](LICENSE.md) file for details.

**You are free to:**

- ✅ Use commercially
- ✅ Modify and adapt
- ✅ Distribute copies
- ✅ Use privately
- ✅ Sublicense

**Under the condition that:**

- 📝 License and copyright notice must be included

---

## 🙏 Acknowledgments

Iskra wouldn't be possible without these amazing projects:

- **[Rich](https://github.com/Textualize/rich)** - Beautiful terminal formatting
- **[Ollama](https://ollama.ai)** - Local AI model runtime
- **[onefetch](https://github.com/o2sh/onefetch)** - ASCII art for programming languages
- **[GitHub CLI](https://cli.github.com/)** - GitHub integration
- **[Click](https://click.palletsprojects.com/)** - CLI framework (via argparse)
- **[PyYAML](https://pyyaml.org/)** - YAML configuration parsing

Special thanks to the open-source community for inspiration and tools.

---

## 📞 Support

Need help? We're here for you!

### Documentation

- 📚 **Full Documentation**: [GitHub Wiki](https://github.com/NoamFav/Iskra#readme)
- 💡 **Usage Examples**: See the [examples/](examples/) directory
- 📝 **Changelog**: [CHANGELOG.md](CHANGELOG.md)

### Get Help

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/NoamFav/Iskra/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/NoamFav/Iskra/discussions)
- 📧 **Email Support**: [noamfav@nf-software.com](mailto:noamfav@nf-software.com)

### Stay Updated

- ⭐ **Star the repo** to follow development
- 👁️ **Watch releases** for updates
- 🐦 **Follow on Twitter**: [@NoamFav](https://twitter.com/NoamFav) (if applicable)

---

## 🗺️ Roadmap

### Completed in v1.0

- [x] Multiple AI provider support (Ollama, Claude, OpenAI)
- [x] Protected branch warnings
- [x] Dry-run mode
- [x] Show-diff before commit
- [x] Pre/post commit hooks
- [x] Auto-stash for safe pulls
- [x] Conflict detection
- [x] SSH key detection
- [x] Arbitrary command execution (`iskra exec`)

### Version 2.0 (Coming Soon)

- [ ] Interactive mode for repository selection
- [ ] Git worktree support
- [ ] Webhook integrations
- [ ] Team collaboration features

### Future Plans

- [ ] VS Code extension
- [ ] Web dashboard for monitoring
- [ ] Slack/Discord notifications
- [ ] Advanced analytics and reporting

See the [GitHub Issues](https://github.com/NoamFav/Iskra/issues) for the full development roadmap.

---

## 📈 Stats

<div align="center">

![Repos Managed](https://img.shields.io/badge/repos%20managed-100+-success?style=for-the-badge)
![Time Saved](https://img.shields.io/badge/time%20saved-hours%20daily-blue?style=for-the-badge)
![Commits Generated](https://img.shields.io/badge/commits%20generated-10k+-orange?style=for-the-badge)

</div>

---

<div align="center">

**Made with ⚡ and ☕ by [NoamFav](https://github.com/NoamFav)**

[⬆ Back to Top](#-iskra)

</div>
