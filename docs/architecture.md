# Iskra Architecture

## Overview

Iskra is a pure Go CLI tool for multi-repository Git management. A single binary handles all commands. There is no Python, no subprocesses, no JSON bridge.

```
iskra/
├── go-core/
│   ├── cmd/iskra/main.go       # CLI entry point & command routing
│   └── internal/
│       ├── config/             # Config + repo tracking
│       ├── git/                # Low-level git helpers
│       ├── ai/                 # Ollama integration
│       ├── processor/          # Batch repo processing
│       ├── scanner/            # Git repo discovery
│       ├── info/               # `iskra info` rendering
│       ├── pulse/              # `iskra pulse` subcommands
│       ├── gh/                 # GitHub CLI wrapper
│       ├── clone/              # Bulk repo cloning
│       ├── init/               # `iskra init` setup
│       ├── exec/               # `iskra exec` cross-repo execution
│       └── ui/                 # Lip Gloss styles & output helpers
├── script/install.sh           # Installer (download-first, source fallback)
├── Makefile                    # Dev targets: build/install/lint/release-local
└── .github/workflows/
    ├── ci.yml                  # go vet + build + smoke test on push/PR
    └── release.yml             # 4-platform binary release on v* tag
```

---

## Command Routing

```mermaid
flowchart TB
    User["iskra [command] [args]"] --> Main["cmd/iskra/main.go"]

    Main --> MultiRepo["Multi-repo commands"]
    Main --> PulseCmd["iskra pulse [sub]"]
    Main --> InfoCmd["iskra info"]

    subgraph MultiRepo["Multi-repo (across tracked repos)"]
        commit["commit / sync"]
        status["status"]
        log["log"]
        diff["diff"]
        stash["stash"]
        scan["scan"]
        exec["exec"]
        branches["branches / br"]
        list["list / ls"]
        add["add"]
        remove["remove / rm"]
        gh["gh info/open/prs"]
        clone["clone"]
        init["init"]
    end

    subgraph PulseCmd["iskra pulse (single repo)"]
        reset["reset"]
        switch["switch / sw"]
        cherry["cherry-pick / cp"]
        rebase["rebase / rb"]
        tag["tag"]
        fixup["fixup"]
        blame["blame"]
        filter["filter"]
    end
```

---

## Package Diagram

```mermaid
flowchart TB
    main["cmd/iskra/main.go"]

    main --> config
    main --> git
    main --> ai
    main --> processor
    main --> scanner
    main --> info
    main --> pulse
    main --> gh
    main --> clone
    main --> initcmd["init (as initcmd)"]
    main --> exec
    main --> ui

    processor --> config
    processor --> git
    processor --> ai
    processor --> scanner

    info --> git
    info --> ui

    pulse --> git

    gh --> git
    clone --> git
    initcmd --> config
    initcmd --> scanner
    exec --> config

    subgraph internal["internal/"]
        config
        git
        ai
        processor
        scanner
        info
        pulse
        gh
        clone
        initcmd
        exec
        ui
    end
```

---

## Data Flow — Multi-repo Operation

```mermaid
sequenceDiagram
    participant User
    participant Main as main.go
    participant Config as config
    participant Scanner as scanner
    participant Processor as processor
    participant Git as git
    participant AI as ai

    User->>Main: iskra commit
    Main->>Config: load ~/.config/iskra/config.yaml + repos.json
    Config-->>Main: ConfigManager + tracked repos

    Main->>Processor: ProcessBatch(repoPaths, opts)

    loop For each repo
        Processor->>Git: status, diff
        Git-->>Processor: changes

        opt Has changes
            Processor->>AI: GenerateCommitMessage(diff)
            AI-->>Processor: message (Ollama)
            Processor->>Git: add + commit + push
        end
    end

    Processor-->>Main: results
    Main-->>User: summary output
```

---

## Data Flow — `iskra pulse` Operation

```mermaid
sequenceDiagram
    participant User
    participant Main as main.go
    participant Pulse as pulse
    participant Git as git

    User->>Main: iskra pulse switch
    Main->>Pulse: Dispatch("switch", args)
    Pulse->>Git: list branches
    Git-->>Pulse: branch list
    Pulse-->>User: interactive picker
    User->>Pulse: select branch
    Pulse->>Git: git switch <branch>
    Git-->>User: switched
```

---

## `iskra info` Rendering

```mermaid
flowchart LR
    subgraph info["internal/info/"]
        infoGo["info.go\nfetch data"]
        displayGo["display.go\nrender output"]
        asciiGo["ascii.go\nASCII art"]
    end

    infoGo -->|RepoInfo struct| displayGo
    asciiGo -->|art lines| displayGo

    infoGo --> git["git helpers"]
    infoGo --> gh["gh CLI\n(open PRs)"]

    displayGo -->|visibleLen()| terminal["Terminal output\nANSI-aware borders"]
```

`display.go` uses `visibleLen()` to strip ANSI escape sequences before computing column widths, ensuring borders align correctly regardless of color codes.

---

## Config Files

| File | Purpose |
|------|---------|
| `~/.config/iskra/config.yaml` | Global config (base dir, AI provider, depth, patterns) |
| `~/.config/iskra/repos.json` | Tracked repository list |

---

## Build & Release

```mermaid
flowchart LR
    tag["git tag v*"] --> release["release.yml"]

    release --> linux_amd64["linux-amd64"]
    release --> linux_arm64["linux-arm64"]
    release --> macos_amd64["macos-amd64"]
    release --> macos_arm64["macos-arm64"]

    linux_amd64 & linux_arm64 --> ubuntu["ubuntu-latest runner"]
    macos_amd64 & macos_arm64 --> macos["macos-latest runner"]

    linux_amd64 & linux_arm64 & macos_amd64 & macos_arm64 --> release_gh["GitHub Release\n+ checksums.txt"]
```

Version string is injected at build time:
```
go build -ldflags "-X main.version=$(git describe --tags --always)"
```

---

## Key Design Decisions

- **`internal/init` → imported as `initcmd`** — avoids collision with Go's `init()` builtin
- **`iskra` = multi-repo, `iskra pulse` = single-repo** — clean namespace separation
- **Lip Gloss for styling** — terminal UI only; Bubble Tea is reserved for Zvezda (TUI companion)
- **Ollama as default AI provider** — local-first, no API key required
- **`gh` CLI as GitHub integration layer** — no direct GitHub API calls from Iskra
