# TODO List for Auto-Commit Project

## Phase 1: Critical Fixes & Core Features (Week 1)

### 🐛 Bug Fixes

- [ ] **Fix `pull_repos.py` line 256**: Add `repo_dir = os.path.join(base_dir, repo_short_name)` before the `os.path.isdir()` check
- [ ] **Test Ollama fallback**: Ensure graceful failure when Ollama is offline/not installed
- [ ] **Test GitHub CLI dependency**: Add check for `gh` command and show helpful error if missing

### 🎯 Init & Tracking System (HIGH PRIORITY)

- [ ] **Create `~/.auto-commit/` config directory structure**
  ```
  ~/.auto-commit/
  ├── config.yaml          # Global settings
  ├── repos.json           # Tracked repositories
  └── logs/                # Operation logs
  ```
- [ ] **Implement `auto-commit init`**
  - Scan base directory for git repos
  - Save discovered repos to `repos.json`
  - Store: path, remote URL, default branch, last commit
- [ ] **Implement `auto-commit add <path>`**: Manually add repo to tracking
- [ ] **Implement `auto-commit remove <path>`**: Remove repo from tracking
- [ ] **Implement `auto-commit list`**: Show all tracked repos with status
- [ ] **Update `auto_commit.py`**: Use tracked repos instead of re-scanning every time

### 🔍 Status & Preview Features

- [ ] **Add `--status-only` flag**: Show git status across all repos without committing
- [ ] **Add `--dry-run` flag**: Preview what would be committed/pushed
- [ ] **Add `--diff` flag**: Show actual diff before committing
- [ ] **Create status summary table**: Show which repos have changes, are ahead/behind remote

### 📥 Pull Updates Enhancement

- [ ] **Fix `pull_repos.py`**: Actually update existing repos instead of just skipping
- [ ] **Add `--update` flag**: Pull latest changes for already-cloned repos
- [ ] **Add conflict detection**: Detect merge conflicts and report them
- [ ] **Add `--sync` mode**: Force update all repos to match remote state

## Phase 2: Enhanced Git Operations (Week 2)

### 🌿 Branch Management

- [ ] **Add branch detection warnings**: Warn before committing to `main`/`master`
- [ ] **Add `--branch` flag**: Create and switch to feature branch before committing
- [ ] **Add branch naming convention**: Auto-generate branch names like `feat/description`
- [ ] **Add `--create-pr` flag**: Create pull request after pushing (via `gh pr create`)

### 🔄 Go Binary Enhancements

- [ ] **Add `ai_commit status`**: Fast git status check
- [ ] **Add `ai_commit staged-files`**: List staged files (JSON output)
- [ ] **Add `ai_commit detect-type`**: Return commit type only
- [ ] **Add `ai_commit generate --dry-run`**: Generate message without committing
- [ ] **Add `--provider` flag**: Support multiple AI providers (ollama/claude/openai)
- [ ] **Add commit body generation**: Not just subject line

### 🛡️ Safety Features

- [ ] **Add confirmation prompts**: Ask before pushing to protected branches
- [ ] **Add `--interactive` mode**: Choose which repos to process
- [ ] **Add pre-commit validation**: Check for large files, secrets, TODO comments
- [ ] **Add rollback capability**: `auto-commit undo` to revert last operation
- [ ] **Add backup before operations**: Store git state before changes

## Phase 3: Configuration & Workflow (Week 3)

### ⚙️ Configuration System

- [ ] **Create `config.yaml` schema**:
  ```yaml
  base_dir: ~/Neoware
  max_depth: 3
  default_branch: main
  ai_provider: ollama
  commit_message_style: conventional
  protected_branches: [main, master, production]
  exclude_patterns: [tmp-*, test-*]
  ```
- [ ] **Add per-repo config**: `.auto-commit.yaml` in each repo
- [ ] **Add profile support**: `--profile work` vs `--profile personal`
- [ ] **Add environment variable support**: `AUTO_COMMIT_CONFIG_PATH`

### 📊 Reporting & Logging

- [ ] **Add operation logging**: Log all operations to `~/.auto-commit/logs/`
- [ ] **Add `--summary` flag**: Show statistics after operations
- [ ] **Add `auto-commit report`**: Generate activity report (commits, repos, time)
- [ ] **Add JSON export**: `--export-json` for programmatic access
- [ ] **Add colored diff output**: Better visualization of changes

### 🔍 Advanced Filtering

- [ ] **Add `--has-changes` filter**: Only process repos with uncommitted changes
- [ ] **Add `--behind-remote` filter**: Only repos that need pulling
- [ ] **Add `--modified-since` filter**: Process repos modified after date
- [ ] **Add `--file-pattern` filter**: Only commit files matching pattern

## Phase 4: Polish & Distribution (Week 4)

### 📝 Documentation

- [ ] **Write comprehensive README.md**:
  - Installation instructions
  - Quick start guide
  - All command examples
  - Configuration options
  - Troubleshooting section
- [ ] **Add `--help` improvements**: Better descriptions for all flags
- [ ] **Create CONTRIBUTING.md**: Guide for contributors
- [ ] **Add example configs**: In `examples/` directory
- [ ] **Create tutorial video/GIF**: Show tool in action

### 📦 Distribution & Setup

- [ ] **Complete `pyproject.toml`**: All metadata, dependencies, entry points
- [ ] **Add installation script**: `curl | sh` style installer
- [ ] **Test cross-platform**: Verify on Linux, macOS, Windows
- [ ] **Create release workflow**: GitHub Actions for building/releasing
- [ ] **Publish to PyPI**: Make `pip install auto-commit` work
- [ ] **Create Homebrew formula**: For easy macOS installation

### 🧪 Testing

- [ ] **Add unit tests**: Test git operations, filtering, config parsing
- [ ] **Add integration tests**: Test full workflows
- [ ] **Add mock tests**: Mock Ollama/GitHub API responses
- [ ] **Add CI pipeline**: Run tests on push
- [ ] **Test with multiple git configs**: Different user names, SSH vs HTTPS

## Phase 5: Advanced Features (Future)

### 🤖 Advanced AI Integration

- [ ] **Multi-provider support**: Claude API, OpenAI as fallbacks
- [ ] **Context from issue trackers**: Parse Jira/GitHub issue numbers
- [ ] **Commit message refinement**: Interactive improvement loop
- [ ] **Breaking change detection**: Auto-add BREAKING CHANGE markers
- [ ] **Learning from history**: Analyze past commits to match style

### 🔄 Automation

- [ ] **Add daemon mode**: `auto-commit daemon start` for scheduled runs
- [ ] **Add watch mode**: Monitor files and auto-commit on changes
- [ ] **Add webhook support**: Trigger on external events
- [ ] **Add cron integration**: Easy setup with crontab

### 🌐 Collaboration

- [ ] **Add team templates**: Share commit message templates
- [ ] **Add convention validation**: Enforce team commit standards
- [ ] **Add review mode**: Stage changes for review before commit
- [ ] **Add co-author support**: Automatically add co-authors

### 🔧 Git Worktree Support

- [ ] **Detect all worktrees**: List linked working trees
- [ ] **Process main + worktrees**: Commit in all linked trees
- [ ] **Worktree-aware operations**: Prevent conflicts between trees

## Quick Wins (Do These First!)

### This Weekend:

1. ✅ Fix the `pull_repos.py` bug (5 min)
2. ✅ Add `--dry-run` flag to both scripts (30 min)
3. ✅ Add `--status-only` flag (30 min)
4. ✅ Add basic logging to file (1 hour)

### Next Week:

5. ✅ Implement init/tracking system (4-6 hours)
6. ✅ Fix pull_repos to update existing repos (2 hours)
7. ✅ Add confirmation prompts for main/master (1 hour)
8. ✅ Write basic README (2 hours)

## Priority Matrix

| Priority | Feature                   | Effort | Impact |
| -------- | ------------------------- | ------ | ------ |
| 🔥 P0    | Fix pull_repos bug        | Low    | High   |
| 🔥 P0    | Init/tracking system      | Medium | High   |
| 🔥 P0    | --dry-run mode            | Low    | High   |
| 🚀 P1    | Status-only mode          | Low    | Medium |
| 🚀 P1    | Pull updates for existing | Medium | High   |
| 🚀 P1    | Configuration system      | Medium | Medium |
| 📝 P2    | Documentation             | Medium | High   |
| 📝 P2    | Better error handling     | Low    | Medium |
| 💡 P3    | Branch management         | Medium | Low    |
| 💡 P3    | Advanced AI features      | High   | Medium |

## Decision Points

**Before starting, decide:**

- [ ] Is this a personal tool or will you distribute it?

  - If personal: Skip testing, focus on features
  - If distribute: Prioritize docs, tests, packaging

- [ ] How much time per week can you dedicate?

  - 5 hours: Focus on P0 items only
  - 10 hours: P0 + P1
  - 20+ hours: Can tackle everything

- [ ] What's your main pain point currently?
  - Re-scanning repos every time? → Init system first
  - Accidentally pushing to main? → Safety features first
  - Ugly output? → Keep Python + Rich
  - Tool is slow? → Move more to Go

**What should I tackle first?** Pick your top 3 and I'll help you implement them!
