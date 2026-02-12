# Changelog

All notable changes to Iskra will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

---

## [1.0.0] - 2025-02-11

### Added

#### Core Features
- **Multi-repository management** - Track and process multiple Git repositories from a single command
- **AI-powered commit messages** - Intelligent commit message generation using local or cloud AI
- **Repository tracking** - Persistent tracking of repositories with `iskra-init`
- **Batch operations** - Commit and push across all tracked repositories simultaneously

#### AI Providers
- **Ollama** - Local AI model support (default provider)
- **OpenAI** - GPT-4o and GPT-4o-mini support
- **Claude** - Anthropic Claude API support
- **Smart fallback** - Automatic fallback to rule-based commit messages when AI unavailable

#### Git Operations
- **Auto-pull** - Optionally pull latest changes before committing
- **Auto-push** - Automatically push commits to remote
- **Auto-stash** - Stash local changes before pull, restore after
- **Conflict detection** - Warn about merge conflicts before operations
- **SSH key detection** - Warn if SSH remote but no keys in agent

#### Safety Features
- **Dry-run mode** - Preview operations without making changes
- **Protected branch warnings** - Confirmation required for main/master/production
- **Show-diff** - View changes before committing
- **Pre/post commit hooks** - Run custom commands before and after commits

#### UI/UX
- **Rich terminal UI** - Beautiful formatting with colors and icons
- **Progress indicators** - Real-time progress during batch operations
- **Tree view** - Visual representation of file changes
- **Detailed summaries** - Operation results and statistics

#### Configuration
- **Global config** - `~/.config/iskra/config.yaml`
- **Per-repository overrides** - `.iskra.yaml` in repository root
- **Environment variable support** - Configure via env vars
- **Glob pattern filtering** - Include/exclude repositories by pattern

#### Tools
- `iskra` - Main repository processing tool
- `iskra-init` - Configuration and repository tracking
- `ai_commit` - Standalone AI commit message generator
- `pull-repos` - GitHub repository cloning utility

### Technical
- Python 3.8+ support
- Go 1.22+ for AI commit binary
- Cross-platform (macOS, Linux, Windows)
- Modular architecture with separate core, UI, and API layers

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-02-11 | Initial public release |

---

[Unreleased]: https://github.com/NoamFav/Iskra/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/NoamFav/Iskra/releases/tag/v1.0.0
