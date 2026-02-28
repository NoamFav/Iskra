# Changelog

All notable changes to Iskra will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

---

## [2.0.0] - 2026-02-26

Complete rewrite from Python to pure Go.

### Added

#### Core
- Pure Go binary — single `iskra` executable, no Python runtime required
- Version injection via `-ldflags "-X main.version=..."` from `git describe` at build time
- `iskra pulse` namespace for all single-repo (mono-repo) operations

#### Commands
- `iskra init` — interactive setup, registers base directory
- `iskra list` / `iskra ls` — list all tracked repositories
- `iskra add` — add a repository to tracking
- `iskra remove` / `iskra rm` — remove a repository from tracking
- `iskra gh info/open/prs` — GitHub info, open in browser, list PRs (via `gh` CLI)
- `iskra clone` — bulk-clone GitHub repos via `gh` CLI

#### `iskra pulse` subcommands
- `pulse reset` — staged reset, hard reset, or file-specific reset
- `pulse switch` — interactive branch picker, create branch (`-b`), delete (`-d`)
- `pulse cherry-pick` — interactive log picker or direct hash
- `pulse rebase` — guided rebase with `--abort`/`--continue`/`--skip` support
- `pulse tag` — list, create, delete, and push tags
- `pulse fixup` — staged changes → pick a commit → autosquash rebase
- `pulse blame` — per-line author view with color-coded output
- `pulse filter` — `git filter-repo` wrapper for history rewriting

#### `iskra info`
- ANSI-aware border rendering (`visibleLen()` strips escape sequences for correct math)
- Upstream status (ahead/behind remote)
- Open PRs count (via `gh` CLI)
- Recent commits section
- ASCII art header with repo name and current branch

#### CI/Release
- GitHub Actions CI (`ci.yml`) — `go vet`, build, smoke test on ubuntu + macos on every push/PR
- GitHub Actions release pipeline (`release.yml`) — builds 4 platform binaries on `v*` tag push
- Pre-built binaries: `linux-amd64`, `linux-arm64`, `macos-amd64`, `macos-arm64`
- Checksums file attached to every GitHub release

#### Tooling
- `Makefile` — `build`, `install`, `lint`, `release-local` targets
- `script/install.sh` rewritten: download pre-built binary first, fall back to `go build` from source

### Removed
- Entire Python codebase (`src/`, `setup.py`, `pyproject.toml`, `requirements.txt`, `MANIFEST.in`)
- `gocli/` hybrid launcher
- `tests/` Python test suite
- `iskra-core` JSON-backend binary (was internal, superseded by unified Go CLI)
- Stale v1.0.0 release tarballs

### Changed
- `install.sh` now targets `~/.local/bin/iskra` and supports download-first install
- README fully rewritten to reflect Go-only state

---

## [1.0.0] - 2025-02-11

Initial public release (Python).

### Added
- Multi-repository management via Python CLI
- AI-powered commit messages (Ollama, OpenAI, Claude)
- Repository tracking with `iskra-init`
- Batch commit/push across tracked repositories
- Dry-run mode, protected branch warnings, auto-stash, auto-pull
- Rich terminal UI with progress indicators
- `~/.config/iskra/config.yaml` global config + `.iskra.yaml` per-repo overrides

---

## Version History

| Version | Date       | Description                        |
|---------|------------|------------------------------------|
| 2.0.0   | 2026-02-26 | Pure Go rewrite, CI/release, pulse |
| 1.0.0   | 2025-02-11 | Initial Python release             |

---

[Unreleased]: https://github.com/NoamFav/Iskra/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/NoamFav/Iskra/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/NoamFav/Iskra/releases/tag/v1.0.0
