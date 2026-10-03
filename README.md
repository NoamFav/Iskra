<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/brand/banner-night.svg">
  <img alt="Iskra: Git automation for people who manage a lot of repos — AI-powered commits, bulk sync, and single-binary tooling in Go. Successor to Zvezda." src=".github/brand/banner-paper.svg" width="100%">
</picture>
<br><br>
<a href="#how-it-works"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-how-it-works-night.svg"><img alt="how it works" src=".github/brand/tab-how-it-works-paper.svg"></picture></a>
<a href="#installation"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-installation-night.svg"><img alt="installation" src=".github/brand/tab-installation-paper.svg"></picture></a>
<a href="#quick-start"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-quick-start-night.svg"><img alt="quick start" src=".github/brand/tab-quick-start-paper.svg"></picture></a>
<a href="#commands"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-commands-night.svg"><img alt="commands" src=".github/brand/tab-commands-paper.svg"></picture></a>
<a href="#flags"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-flags-night.svg"><img alt="flags" src=".github/brand/tab-flags-paper.svg"></picture></a>
<a href="#configuration"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-configuration-night.svg"><img alt="configuration" src=".github/brand/tab-configuration-paper.svg"></picture></a>
<a href="#ai-commit-messages"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-ai-commit-messages-night.svg"><img alt="ai commit messages" src=".github/brand/tab-ai-commit-messages-paper.svg"></picture></a>
<a href="#building-from-source"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-building-from-source-night.svg"><img alt="building from source" src=".github/brand/tab-building-from-source-paper.svg"></picture></a>
<a href="#contributing"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-contributing-night.svg"><img alt="contributing" src=".github/brand/tab-contributing-paper.svg"></picture></a>
<a href="#acknowledgements"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-acknowledgements-night.svg"><img alt="acknowledgements" src=".github/brand/tab-acknowledgements-paper.svg"></picture></a>
<a href="#license"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/tab-license-night.svg"><img alt="license" src=".github/brand/tab-license-paper.svg"></picture></a>
</div>

<br>

Iskra is a single Go binary that handles the tedious parts of git across all your repositories at once — AI-powered commits, bulk sync, status overview — while also giving you a clean set of single-repo tools under `iskra pulse`.

<p>
<a name="how-it-works"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-how-it-works-night.svg"><img alt="how it works" src=".github/brand/section-how-it-works-paper.svg" width="100%"></picture>
</p>

```mermaid
flowchart LR
    A([iskra init]) --> B[(tracked repos)]
    B --> C{iskra}
    C --> D[diff each repo]
    D --> E{has changes?}
    E -- no --> F([skip])
    E -- yes --> G{AI available?}
    G -- yes --> H[generate message]
    G -- no --> I[smart fallback]
    H --> J([commit + push])
    I --> J
```

<p>
<a name="installation"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-installation-night.svg"><img alt="installation" src=".github/brand/section-installation-paper.svg" width="100%"></picture>
</p>

**One-liner** (downloads pre-built binary, no Go required):

```bash
curl -fsSL https://raw.githubusercontent.com/NoamFav/Iskra/main/script/install.sh | bash
```

**From source** (requires Go 1.24+):
```bash
git clone https://github.com/NoamFav/Iskra
cd Iskra && make install
```

**Manual** — grab a tarball from [Releases](https://github.com/NoamFav/Iskra/releases), extract, and move `iskra` to somewhere on your `$PATH`.

### Dependencies

| Tool | Required for |
|------|-------------|
| `git` | Everything |
| `ollama` | AI commit messages (default provider) |
| `gh` | `iskra gh`, `iskra clone` |

<p>
<a name="quick-start"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-quick-start-night.svg"><img alt="quick start" src=".github/brand/section-quick-start-paper.svg" width="100%"></picture>
</p>

```bash
iskra init        # 1. scan a directory and track all repos found
iskra status      # 2. see what's going on across all of them
iskra             # 3. commit and push everything
```

Iskra remembers your repos in `~/.config/iskra/repos.json` and processes them every time you run `iskra`.

<p>
<a name="commands"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-commands-night.svg"><img alt="commands" src=".github/brand/section-commands-paper.svg" width="100%"></picture>
</p>

```mermaid
graph LR
    root(("⚡ iskra")):::root

    root --> MR["🗂 Multi-repo"]:::group
    root --> TR["📌 Tracking"]:::group
    root --> SR["📦 Single-repo"]:::group
    root --> GH["🐙 GitHub"]:::group
    root --> IN["🔍 Inspection"]:::group

    MR --> mr1[status]:::cmd
    MR --> mr2[sync-all]:::cmd
    MR --> mr3[exec]:::cmd
    MR --> mr4[scan]:::cmd

    TR --> tr1[init]:::cmd
    TR --> tr2[list / ls]:::cmd
    TR --> tr3[add]:::cmd
    TR --> tr4[remove / rm]:::cmd

    SR --> pulse["pulse"]:::sub
    pulse --> p1[switch]:::cmd
    pulse --> p2[rebase]:::cmd
    pulse --> p3[reset]:::cmd
    pulse --> p4[stash]:::cmd
    pulse --> p5[tag]:::cmd
    pulse --> p6[fixup]:::cmd
    pulse --> p7[blame]:::cmd
    pulse --> p8[cherry-pick]:::cmd

    GH --> gh1[gh info]:::cmd
    GH --> gh2[gh open]:::cmd
    GH --> gh3[gh prs]:::cmd
    GH --> gh4[clone]:::cmd

    IN --> in1[log]:::cmd
    IN --> in2[diff]:::cmd
    IN --> in3[info]:::cmd
    IN --> in4[branches]:::cmd
    IN --> in5[stash]:::cmd

    classDef root fill:#86CFAC,color:#000,font-weight:bold,stroke:#86CFAC
    classDef group fill:#2d333b,color:#cdd9e5,font-weight:bold,stroke:#444c56
    classDef sub fill:#388bfd,color:#fff,font-weight:bold,stroke:#388bfd
    classDef cmd fill:#1c2128,color:#adbac7,stroke:#373e47
```

### Multi-repo

```bash
iskra                        # Commit + push all repos (AI messages)
iskra status                 # Status overview across all repos
iskra sync-all               # Pull all tracked repos
iskra exec "git fetch --all" # Run any command across all repos
iskra scan [dir]             # Scan directory, show found repos
```

### Repo tracking

```bash
iskra init [dir]    # Scan a directory and track all found git repos
iskra list          # List tracked repos  (alias: iskra ls)
iskra add [path]    # Add a repo to tracking
iskra remove [path] # Remove a repo  (alias: iskra rm)
```

### Single-repo — `iskra pulse`

`pulse` with no subcommand commits + pushes the **current** repo only.

```bash
iskra pulse                  # Commit + push current repo
iskra pulse -m "fix: typo"   # With manual message
iskra pulse --no-push        # Commit only
iskra pulse --pull           # Pull first, then commit + push
iskra pulse --dry-run        # Preview, no changes
```

<details>
<summary><b>pulse subcommands</b></summary>

```bash
iskra pulse reset [file]                 # Discard changes (staged, unstaged, or hard reset)
iskra pulse switch [branch]             # Interactive branch picker / create / delete
iskra pulse rebase [base]               # Guided rebase with conflict recovery hints
iskra pulse cherry-pick [hash]          # Pick commits with interactive log view
iskra pulse tag [name]                  # Create, list, delete, push tags
iskra pulse fixup [hash]                # Squash staged changes into a past commit
iskra pulse blame <file>                # Per-line author view with color-coded authors
iskra pulse filter --remove-path <path> # Rewrite history (wraps git-filter-repo)
```

</details>

### GitHub integration

> Requires the [`gh`](https://cli.github.com/) CLI.

```bash
iskra gh info           # Repo stats, stars, watchers, open issues
iskra gh open           # Open repo in browser
iskra gh prs            # List open pull requests
iskra gh prs --open 42  # Open PR #42 in browser

iskra clone [dir]                        # Bulk-clone all your GitHub repos
iskra clone --filter-forks --only-stars 5
```

### Inspection

```bash
iskra log       # Pretty git log for current repo
iskra diff      # Colored diff
iskra info      # Rich repo stats (language breakdown, recent commits, upstream)
iskra branches  # List all branches  (alias: iskra br)
iskra stash     # Stash management (list / push / pop)
```

<p>
<a name="flags"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-flags-night.svg"><img alt="flags" src=".github/brand/section-flags-paper.svg" width="100%"></picture>
</p>

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview — no changes made |
| `--no-ai-commit` | Skip AI, prompt for message |
| `-m "message"` | Use this commit message |
| `--pull` | Pull before committing |
| `--no-push` | Commit but don't push |
| `--only a,b` | Filter to specific repos by name |
| `--json` | Output JSON |
| `--minimal` | No colors or icons (good for CI) |
| `-q` | Quiet mode |

<p>
<a name="configuration"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-configuration-night.svg"><img alt="configuration" src=".github/brand/section-configuration-paper.svg" width="100%"></picture>
</p>

Config lives at `~/.config/iskra/config.yaml`. Created automatically on first run.

```yaml
# Where to scan for repos during `iskra init`
base_dir: ~/code
max_depth: 3

# Git behaviour
auto_pull: true
auto_push: true
default_branch: main
protected_branches: [main, master, production]

# AI commits
use_ai_commit: true
commit_message_style: conventional   # or: simple
ai_provider: ollama                  # or: openai, claude

# Ollama (default — runs locally, free)
ollama_url: http://127.0.0.1:11434
ollama_model: mistral

# OpenAI (set OPENAI_API_KEY env var or add key here)
# ai_provider: openai
# openai_model: gpt-4o-mini

# Claude (set ANTHROPIC_API_KEY env var or add key here)
# ai_provider: claude
# claude_model: claude-opus-4-5

# Safety
require_confirmation: true
dry_run: false
```

### Per-repo overrides

Drop a `.iskra.yaml` in any repo root to override global settings for that repo:

```yaml
auto_push: false
use_ai_commit: false
protected_branches: [main, develop, staging]
```

<p>
<a name="ai-commit-messages"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-ai-commit-messages-night.svg"><img alt="ai commit messages" src=".github/brand/section-ai-commit-messages-paper.svg" width="100%"></picture>
</p>

Iskra generates [Conventional Commits](https://www.conventionalcommits.org/) from your diff:

```
feat(auth): add OAuth2 login flow
fix(api): handle nil pointer in user handler
docs: update installation instructions
refactor(db): simplify query builder
```

| Provider | Setup |
|----------|-------|
| **Ollama** (default, local) | `brew install ollama && ollama pull mistral` |
| **OpenAI** | `export OPENAI_API_KEY=sk-...` |
| **Claude** | `export ANTHROPIC_API_KEY=sk-ant-...` |

If AI generation fails for any reason, Iskra falls back to a smart conventional message generated from the diff — it never blocks you.

<p>
<a name="building-from-source"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-building-from-source-night.svg"><img alt="building from source" src=".github/brand/section-building-from-source-paper.svg" width="100%"></picture>
</p>

```bash
git clone https://github.com/NoamFav/Iskra
cd Iskra

make build      # → bin/iskra
make install    # build + copy to ~/.local/bin/iskra
make lint       # go vet ./...
```

The version string is injected from the git tag at build time via `-ldflags "-X main.version=..."`.

<p>
<a name="contributing"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-contributing-night.svg"><img alt="contributing" src=".github/brand/section-contributing-paper.svg" width="100%"></picture>
</p>

1. Fork → branch → commit (use `iskra pulse` 😄)
2. Code is pure Go in `go-core/`. Follow standard Go conventions (`gofmt`, `go vet`).
3. PRs welcome — check [open issues](https://github.com/NoamFav/Iskra/issues) for ideas.

<p>
<a name="acknowledgements"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-acknowledgements-night.svg"><img alt="acknowledgements" src=".github/brand/section-acknowledgements-paper.svg" width="100%"></picture>
</p>

- [onefetch](https://github.com/o2sh/onefetch) — inspiration for `iskra info`
- [Lip Gloss](https://github.com/charmbracelet/lipgloss) — terminal styling
- [Ollama](https://ollama.ai) — local AI runtime
- [gh](https://cli.github.com/) — GitHub CLI integration

<p>
<a name="license"></a>
<picture><source media="(prefers-color-scheme: dark)" srcset=".github/brand/section-license-night.svg"><img alt="license" src=".github/brand/section-license-paper.svg" width="100%"></picture>
</p>

Apache 2.0 — see [LICENSE](LICENSE).

<div align="center">
Made with ⚡ by <a href="https://github.com/NoamFav">NoamFav</a>
</div>

<br>

<a href="https://nf-software.com">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/brand/footer-night.svg">
  <img alt="NF Software" src=".github/brand/footer-paper.svg" width="100%">
</picture>
</a>
