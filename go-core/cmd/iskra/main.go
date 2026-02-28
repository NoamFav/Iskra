// iskra is the main Iskra CLI.
// Uses Lip Gloss for styled terminal output.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	osexec "os/exec"
	"strings"
	"time"

	"github.com/NoamFav/iskra/internal/clone"
	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/exec"
	ghcmd "github.com/NoamFav/iskra/internal/gh"
	"github.com/NoamFav/iskra/internal/info"
	initcmd "github.com/NoamFav/iskra/internal/init"
	"github.com/NoamFav/iskra/internal/processor"
	"github.com/NoamFav/iskra/internal/pulse"
	"github.com/NoamFav/iskra/internal/scanner"
	"github.com/NoamFav/iskra/internal/ui"
)

// version is set at build time via -ldflags "-X main.version=..."
// Falls back to "dev" for local builds without a tag.
var version = "dev"

// splitArgs separates global flags from the subcommand and its args.
// Scans ALL flags regardless of order — known global flags go to globalArgs,
// unknown flags go to cmdArgs (treated as implicit commit flags).
// Flags that consume a value (e.g. -m "msg") are forwarded with their value.
func splitArgs(argv []string) (globalArgs []string, cmd string, cmdArgs []string) {
	globalFlagNames := map[string]bool{
		"version": true, "v": true, "help": true, "h": true,
		"json": true, "minimal": true, "quiet": true, "q": true, "config": true,
	}
	// All flags (global or commit) that consume the next token as a value
	flagsWithValue := map[string]bool{
		"config":   true, // global
		"m":        true, "message": true, // commit
		"scan":     true, "only": true, "exclude": true, // commit filter
	}

	scanFlags := func(slice []string) (globals, rest []string) {
		j := 0
		for j < len(slice) {
			a := slice[j]
			if !strings.HasPrefix(a, "-") {
				rest = append(rest, slice[j:]...)
				return
			}
			n := strings.TrimLeft(a, "-")
			hasInline := false
			if eqIdx := strings.Index(n, "="); eqIdx >= 0 {
				n = n[:eqIdx]
				hasInline = true
			}
			if globalFlagNames[n] {
				globals = append(globals, a)
				if !hasInline && flagsWithValue[n] {
					j++
					if j < len(slice) {
						globals = append(globals, slice[j])
					}
				}
			} else {
				rest = append(rest, a)
				if !hasInline && flagsWithValue[n] {
					j++
					if j < len(slice) {
						rest = append(rest, slice[j])
					}
				}
			}
			j++
		}
		return
	}

	i := 0
	for i < len(argv) {
		arg := argv[i]
		if !strings.HasPrefix(arg, "-") {
			// Subcommand found — scan remaining args for any global flags mixed in
			cmd = arg
			g, rest := scanFlags(argv[i+1:])
			globalArgs = append(globalArgs, g...)
			cmdArgs = rest
			return
		}
		name := strings.TrimLeft(arg, "-")
		hasInlineValue := false
		if eqIdx := strings.Index(name, "="); eqIdx >= 0 {
			name = name[:eqIdx]
			hasInlineValue = true
		}
		if globalFlagNames[name] {
			globalArgs = append(globalArgs, arg)
			if !hasInlineValue && flagsWithValue[name] {
				i++
				if i < len(argv) {
					globalArgs = append(globalArgs, argv[i])
				}
			}
		} else {
			// Unknown root flag → commit flag
			cmdArgs = append(cmdArgs, arg)
			if !hasInlineValue && flagsWithValue[name] {
				i++
				if i < len(argv) {
					cmdArgs = append(cmdArgs, argv[i])
				}
			}
		}
		i++
	}
	return
}

func main() {
	var (
		showVersion bool
		showHelp    bool
		jsonOutput  bool
		minimal     bool
		quiet       bool
		configDir   string
	)

	globalArgs, cmd, cmdArgs := splitArgs(os.Args[1:])

	fs := flag.NewFlagSet("iskra", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	fs.BoolVar(&showVersion, "version", false, "")
	fs.BoolVar(&showVersion, "v", false, "")
	fs.BoolVar(&showHelp, "help", false, "")
	fs.BoolVar(&showHelp, "h", false, "")
	fs.BoolVar(&jsonOutput, "json", false, "")
	fs.BoolVar(&minimal, "minimal", false, "")
	fs.BoolVar(&quiet, "quiet", false, "")
	fs.BoolVar(&quiet, "q", false, "")
	fs.StringVar(&configDir, "config", "", "")
	fs.Parse(globalArgs)

	if showVersion {
		fmt.Printf("iskra %s\n", version)
		return
	}

	if showHelp {
		printHelp()
		return
	}

	ui.SetMinimalMode(minimal)

	args := cmdArgs

	cfgMgr, err := config.NewManager(configDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading config: %v\n", err)
		os.Exit(1)
	}

	var exitCode int
	switch cmd {
	case "", "commit":
		exitCode = runCommit(cfgMgr, args, jsonOutput, quiet)
	case "status", "s":
		exitCode = runStatus(cfgMgr, args, jsonOutput, quiet)
	case "pulse", "p":
		exitCode = runPulseCmd(cfgMgr, args, jsonOutput, quiet)
	case "scan":
		exitCode = runScan(cfgMgr, args, jsonOutput)
	case "init", "list", "ls", "add", "remove", "rm":
		exitCode = runInit(cfgMgr, cmd, args, jsonOutput)
	case "exec":
		exitCode = runExec(cfgMgr, args, jsonOutput, quiet)
	case "sync":
		exitCode = runSync(cfgMgr, args, jsonOutput, quiet)
	case "sync-all":
		exitCode = runSyncAll(cfgMgr, args, jsonOutput, quiet)
	case "log":
		exitCode = runLog(args)
	case "info":
		exitCode = runInfo(jsonOutput, args)
	case "diff":
		exitCode = runDiff(args)
	case "branches", "br":
		exitCode = runBranches(args)
	case "stash":
		exitCode = runStash(args)
	case "gh":
		exitCode = runGH(args)
	case "clone":
		exitCode = runClone(args)
	case "help":
		printHelp()
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", cmd)
		printHelp()
		exitCode = 1
	}

	os.Exit(exitCode)
}

func printHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra") + " - Intelligent Git automation")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra [command] [flags]")
	fmt.Println("    iskra [flags]           (defaults to commit)")
	fmt.Println()
	fmt.Println(ui.Bold("COMMANDS:"))
	fmt.Println("    commit        Commit and push all tracked repos  (default)")
	fmt.Println("    status, s     Show status of all repos")
	fmt.Println("    pulse, p      Mono-repo operations (reset, switch, rebase, tag…)")
	fmt.Println("                  Run 'iskra pulse help' for subcommands")
	fmt.Println("    exec          Run a command across all repos")
	fmt.Println("    sync          Pull current repo")
	fmt.Println("    sync-all      Pull all tracked repos")
	fmt.Println("    scan          Scan directory for repos")
	fmt.Println("    log           Show git log (pretty)")
	fmt.Println("    info          Repository info (like onefetch)")
	fmt.Println("    diff          Show git diff (colored)")
	fmt.Println("    branches, br  List all branches")
	fmt.Println("    stash         Stash management (list, push, pop)")
	fmt.Println("    gh            GitHub integration (info, open, prs)")
	fmt.Println("    clone         Bulk clone GitHub repositories")
	fmt.Println("    init          Scan and track repositories")
	fmt.Println("    list, ls      List tracked repositories")
	fmt.Println("    add           Add a repository to tracking")
	fmt.Println("    remove, rm    Remove a repository from tracking")
	fmt.Println()
	fmt.Println(ui.Bold("GLOBAL FLAGS:"))
	fmt.Println("    -h, -help       Show help")
	fmt.Println("    -v, -version    Show version")
	fmt.Println("    -json           Output JSON")
	fmt.Println("    -minimal        No colors or icons")
	fmt.Println("    -q, -quiet      Quiet mode")
	fmt.Println()
	fmt.Println(ui.Bold("COMMIT FLAGS:") + ui.Mute("  (for 'iskra commit' or 'iskra' directly)"))
	fmt.Println("    -status-only    Only show status")
	fmt.Println("    -pull-only      Only pull")
	fmt.Println("    -pull           Pull before commit")
	fmt.Println("    -no-push        Don't push after commit")
	fmt.Println("    -no-ai-commit   Don't use AI")
	fmt.Println("    -m <message>    Custom commit message")
	fmt.Println("    -dry-run        Preview without changes")
	fmt.Println()
	fmt.Println(ui.Bold("FILTER FLAGS:") + ui.Mute("  (for 'iskra commit' or 'iskra' directly)"))
	fmt.Println("    -only <pattern>    Only include matching repos")
	fmt.Println("    -exclude <pattern> Exclude matching repos")
	fmt.Println("    -c, -has-changes   Only repos with changes")
	fmt.Println()
}

func printCommitHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra commit") + " - Commit and push all tracked repos")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra [commit] [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -status-only    Only show status, no commits")
	fmt.Println("    -pull-only      Only pull, no commits")
	fmt.Println("    -pull           Pull before committing")
	fmt.Println("    -no-push        Commit but don't push")
	fmt.Println("    -no-ai-commit   Skip AI, use smart message instead")
	fmt.Println("    -m <message>    Use a custom commit message")
	fmt.Println("    -dry-run        Preview what would happen, no changes")
	fmt.Println()
	fmt.Println(ui.Bold("FILTER FLAGS:"))
	fmt.Println("    -only <pattern>    Only include repos matching pattern")
	fmt.Println("    -exclude <pattern> Exclude repos matching pattern")
	fmt.Println("    -c, -has-changes   Only process repos with changes")
	fmt.Println()
}

func hasHelpFlag(args []string) bool {
	for _, a := range args {
		if a == "-h" || a == "-help" || a == "--help" {
			return true
		}
	}
	return false
}

func printStatusHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra status") + " - Show status of all tracked repos")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra status [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -only <pattern>    Only include repos matching pattern")
	fmt.Println("    -exclude <pattern> Exclude repos matching pattern")
	fmt.Println()
}

func printPulseHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra pulse") + " - Mono-repo operations")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra pulse [subcommand] [flags]")
	fmt.Println("    iskra pulse [flags]           (defaults to commit current repo)")
	fmt.Println()
	fmt.Println(ui.Bold("SUBCOMMANDS:"))
	fmt.Println("    reset         Reset staged or unstaged changes")
	fmt.Println("    switch, sw    Switch branches interactively")
	fmt.Println("    cherry-pick, cp  Cherry-pick a commit")
	fmt.Println("    rebase, rb    Interactive rebase helper")
	fmt.Println("    tag           List, create, delete, push tags")
	fmt.Println("    fixup         Fixup commit into an older one")
	fmt.Println("    blame         Per-line author view")
	fmt.Println("    filter        git filter-repo wrapper")
	fmt.Println()
	fmt.Println(ui.Bold("COMMIT FLAGS:") + ui.Mute("  (when no subcommand given)"))
	fmt.Println("    -status-only    Only show status")
	fmt.Println("    -pull           Pull before committing")
	fmt.Println("    -no-push        Commit but don't push")
	fmt.Println("    -no-ai-commit   Skip AI commit message")
	fmt.Println("    -m <message>    Custom commit message")
	fmt.Println("    -dry-run        Preview without changes")
	fmt.Println()
}

func printScanHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra scan") + " - Scan directory for git repositories")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra scan [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -dir <path>   Directory to scan (default: configured base dir)")
	fmt.Println("    -depth <n>    Max depth to search (default: 3)")
	fmt.Println()
}

func printInitHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra init") + " - Scan and track repositories")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra init [flags]")
	fmt.Println("    iskra list, ls [-all]")
	fmt.Println("    iskra add [path]")
	fmt.Println("    iskra remove, rm [path]")
	fmt.Println()
	fmt.Println(ui.Bold("INIT FLAGS:"))
	fmt.Println("    -base-dir <path>   Directory to scan for repos")
	fmt.Println("    -y, -yes           Accept all defaults")
	fmt.Println()
	fmt.Println(ui.Bold("LIST FLAGS:"))
	fmt.Println("    -all   Include inactive repos")
	fmt.Println()
}

func printExecHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra exec") + " - Run a command across all tracked repos")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra exec [flags] <command>")
	fmt.Println()
	fmt.Println(ui.Bold("EXAMPLES:"))
	fmt.Println("    iskra exec git fetch")
	fmt.Println("    iskra exec -p 4 npm install")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -p <n>             Parallel workers (default: 1)")
	fmt.Println("    -fail-fast         Stop on first error")
	fmt.Println("    -only <pattern>    Only include repos matching pattern")
	fmt.Println("    -exclude <pattern> Exclude repos matching pattern")
	fmt.Println()
}

func printSyncHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra sync") + " - Pull the current repository")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra sync")
	fmt.Println()
	fmt.Println("    Pulls the current git repo. No flags.")
	fmt.Println("    For all tracked repos, use: iskra sync-all")
	fmt.Println()
}

func printSyncAllHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra sync-all") + " - Pull all tracked repositories")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra sync-all [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -only <pattern>    Only include repos matching pattern")
	fmt.Println("    -exclude <pattern> Exclude repos matching pattern")
	fmt.Println()
}

func printLogHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra log") + " - Show git log (pretty formatted)")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra log [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -n <n>           Number of commits (default: 20)")
	fmt.Println("    -oneline         One line per commit")
	fmt.Println("    -graph           Show branch graph")
	fmt.Println("    -all             Include all branches")
	fmt.Println("    -author <name>   Filter by author")
	fmt.Println("    -since <date>    Commits since date (e.g. 2024-01-01)")
	fmt.Println("    -until <date>    Commits until date")
	fmt.Println("    -grep <text>     Search commit messages")
	fmt.Println()
}

func printDiffHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra diff") + " - Show git diff (colored)")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra diff [flags] [files...]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -staged, -cached   Show staged changes only")
	fmt.Println("    -stat              Show diffstat summary only")
	fmt.Println()
}

func printBranchesHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra branches") + " - List git branches")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra branches [flags]")
	fmt.Println("    iskra br [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -a, -all      Show all branches (local + remote)")
	fmt.Println("    -r, -remote   Show only remote branches")
	fmt.Println()
}

func printStashHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra stash") + " - Stash management")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra stash [subcommand] [args]")
	fmt.Println()
	fmt.Println(ui.Bold("SUBCOMMANDS:"))
	fmt.Println("    list, ls          List all stashes  (default)")
	fmt.Println("    push [message]    Stash current changes")
	fmt.Println("    pop [stash@{n}]   Pop top stash (or specific)")
	fmt.Println("    apply [stash@{n}] Apply stash without removing")
	fmt.Println("    drop [stash@{n}]  Delete a stash entry")
	fmt.Println("    show [stash@{n}]  Show stash diff")
	fmt.Println("    clear             Delete all stashes")
	fmt.Println()
}

func printGHHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra gh") + " - GitHub integration")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra gh <subcommand> [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("SUBCOMMANDS:"))
	fmt.Println("    info    Show GitHub info for current repo")
	fmt.Println("    open    Open repo page in browser")
	fmt.Println("    prs     List pull requests")
	fmt.Println()
	fmt.Println(ui.Bold("PRS FLAGS:"))
	fmt.Println("    -limit <n>          Max PRs to fetch (default: 50)")
	fmt.Println("    -state <s>          open|closed|merged|all (default: open)")
	fmt.Println("    -draft <s>          all|only|exclude (default: all)")
	fmt.Println("    -need-review        Only PRs awaiting review")
	fmt.Println("    -require-changes    Only PRs with changes requested")
	fmt.Println("    -open <n>           Open PR number in browser")
	fmt.Println()
}

func printCloneHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra clone") + " - Bulk clone GitHub repositories")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra clone [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -base-dir <path>   Where to clone repos (default: ~/Neoware)")
	fmt.Println("    -limit <n>         Max repos to fetch (default: 1000)")
	fmt.Println("    -filter-forks      Skip forked repositories")
	fmt.Println("    -only-stars <n>    Only repos with at least N stars")
	fmt.Println("    -exclude <list>    Comma-separated name patterns to exclude")
	fmt.Println()
}

func printInfoHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra info") + " - Repository info panel")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra info")
	fmt.Println()
	fmt.Println("    Shows repo stats: branch, upstream, open PRs, recent commits.")
	fmt.Println("    Must be run inside a git repository.")
	fmt.Println("    Use -json for machine-readable output.")
	fmt.Println()
}

func runCommit(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	for _, arg := range args {
		if arg == "-h" || arg == "-help" || arg == "--help" {
			printCommitHelp()
			return 0
		}
	}

	fs := flag.NewFlagSet("commit", flag.ContinueOnError)
	fs.SetOutput(io.Discard)

	var (
		statusOnly    bool
		pullOnly      bool
		pull          bool
		noPush        bool
		noAICommit    bool
		commitMessage string
		dryRun        bool
		hasChanges    bool
		scanDir       string
		only          string
		exclude       string
	)

	fs.BoolVar(&statusOnly, "status-only", false, "Only show status")
	fs.BoolVar(&pullOnly, "pull-only", false, "Only pull")
	fs.BoolVar(&pull, "pull", false, "Pull before commit")
	fs.BoolVar(&noPush, "no-push", false, "Don't push")
	fs.BoolVar(&noAICommit, "no-ai-commit", false, "No AI commit")
	fs.StringVar(&commitMessage, "message", "", "Commit message")
	fs.StringVar(&commitMessage, "m", "", "Commit message")
	fs.BoolVar(&dryRun, "dry-run", false, "Dry run")
	fs.BoolVar(&hasChanges, "has-changes", false, "Only repos with changes")
	fs.BoolVar(&hasChanges, "c", false, "Only repos with changes")
	fs.StringVar(&scanDir, "scan", "", "Scan directory")
	fs.StringVar(&only, "only", "", "Only pattern")
	fs.StringVar(&exclude, "exclude", "", "Exclude pattern")

	if err := fs.Parse(args); err != nil {
		fmt.Fprintf(os.Stderr, "Unknown flag: %s\n", err)
		printCommitHelp()
		return 1
	}

	repos := getRepos(cfgMgr, scanDir, only, exclude)
	if len(repos) == 0 {
		if !quiet {
			ui.WarningMsg("No repositories found")
		}
		return 0
	}

	proc := processor.NewProcessor(cfgMgr)
	opts := processor.Options{
		StatusOnly:    statusOnly,
		PullOnly:      pullOnly,
		Pull:          pull,
		NoPush:        noPush,
		NoAICommit:    noAICommit,
		CommitMessage: commitMessage,
		DryRun:        dryRun,
	}

	if jsonOutput {
		result := proc.ProcessBatch(repos, opts)
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		if result.ReposFailed > 0 {
			return 1
		}
		return 0
	}

	if !quiet {
		ui.Header()
		ui.InfoMsg(fmt.Sprintf("Found %d repositories", len(repos)))
		fmt.Println()
	}

	start := time.Now()
	var successCount, failCount int

	for i, repoPath := range repos {
		r := proc.ProcessRepo(repoPath, opts)
		printRepoResult(r, i+1, len(repos), quiet)
		if r.Status == "success" {
			successCount++
		} else {
			failCount++
		}
	}

	if !quiet {
		operation := "COMMIT"
		if statusOnly {
			operation = "STATUS"
		} else if pullOnly {
			operation = "PULL"
		}
		ui.Summary(operation, len(repos), successCount, failCount, time.Since(start).Milliseconds())
	}

	if failCount > 0 {
		return 1
	}
	return 0
}

func runStatus(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if hasHelpFlag(args) {
		printStatusHelp()
		return 0
	}
	fs := flag.NewFlagSet("status", flag.ExitOnError)
	var only, exclude string
	fs.StringVar(&only, "only", "", "Only pattern")
	fs.StringVar(&exclude, "exclude", "", "Exclude pattern")
	fs.Parse(args)

	repos := getRepos(cfgMgr, "", only, exclude)

	proc := processor.NewProcessor(cfgMgr)
	opts := processor.Options{StatusOnly: true}

	if jsonOutput {
		result := proc.ProcessBatch(repos, opts)
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		return 0
	}

	if !quiet {
		ui.CompactHeader()
	}

	for _, repoPath := range repos {
		result := proc.ProcessRepo(repoPath, opts)

		dot := ui.DotSuccess
		if result.Status != "success" {
			dot = ui.DotError
		} else if result.Changes != nil && result.Changes.Total > 0 {
			dot = ui.DotWarning
		}

		fmt.Printf("%s %s", dot, ui.Bold(result.Name))
		fmt.Printf(" [%s]", ui.Mute(result.Branch))

		if result.Changes != nil && result.Changes.Total > 0 {
			fmt.Printf(" %s", ui.Warn(fmt.Sprintf("%d changes", result.Changes.Total)))
		}

		if result.IsProtected {
			fmt.Printf(" %s", ui.Warn("protected"))
		}

		fmt.Println()
	}

	return 0
}

// runPulseCmd is the dispatcher for "iskra pulse [subcommand]".
// With no subcommand it runs the classic commit+push on the current repo.
// With a subcommand (reset, switch, cherry-pick, rebase, tag, fixup, blame, filter)
// it delegates to the pulse package.
func runPulseCmd(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if hasHelpFlag(args) {
		printPulseHelp()
		return 0
	}
	// If first arg is a known pulse subcommand, dispatch to pulse package
	if len(args) > 0 {
		sub := args[0]
		switch sub {
		case "reset",
			"switch", "sw",
			"cherry-pick", "cp",
			"rebase", "rb",
			"tag",
			"fixup",
			"blame",
			"filter",
			"help", "-h", "--help":
			return pulse.Dispatch(sub, args[1:])
		}
	}

	// No subcommand (or flags only) — classic pulse behaviour
	return runPulse(cfgMgr, args, jsonOutput, quiet)
}

func runPulse(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	repo, err := scanner.GetCurrentRepo()
	if err != nil || repo == nil {
		ui.ErrorMsg("Not in a git repository")
		return 1
	}

	fs := flag.NewFlagSet("pulse", flag.ExitOnError)
	var (
		statusOnly    bool
		pull          bool
		noPush        bool
		noAICommit    bool
		commitMessage string
		dryRun        bool
	)

	fs.BoolVar(&statusOnly, "status-only", false, "Only show status")
	fs.BoolVar(&pull, "pull", false, "Pull before commit")
	fs.BoolVar(&noPush, "no-push", false, "Don't push")
	fs.BoolVar(&noAICommit, "no-ai-commit", false, "No AI commit")
	fs.StringVar(&commitMessage, "message", "", "Commit message")
	fs.StringVar(&commitMessage, "m", "", "Commit message")
	fs.BoolVar(&dryRun, "dry-run", false, "Dry run")
	fs.Parse(args)

	proc := processor.NewProcessor(cfgMgr)
	opts := processor.Options{
		StatusOnly:    statusOnly,
		Pull:          pull,
		NoPush:        noPush,
		NoAICommit:    noAICommit,
		CommitMessage: commitMessage,
		DryRun:        dryRun,
	}

	if jsonOutput {
		result := proc.ProcessRepo(repo.Path, opts)
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		return 0
	}

	if !quiet {
		ui.CompactHeader()
	}

	result := proc.ProcessRepo(repo.Path, opts)
	printRepoResult(result, 1, 1, quiet)

	if result.Status != "success" {
		return 1
	}
	return 0
}

func runScan(cfgMgr *config.Manager, args []string, jsonOutput bool) int {
	if hasHelpFlag(args) {
		printScanHelp()
		return 0
	}
	fs := flag.NewFlagSet("scan", flag.ExitOnError)
	var baseDir string
	var maxDepth int
	fs.StringVar(&baseDir, "dir", "", "Base directory")
	fs.IntVar(&maxDepth, "depth", 3, "Max depth")
	fs.Parse(args)

	if baseDir == "" {
		baseDir = config.ExpandPath(cfgMgr.GlobalConfig.BaseDir)
	}

	repos, err := scanner.FindGitRepos(scanner.Options{
		BaseDir:  baseDir,
		MaxDepth: maxDepth,
	})
	if err != nil {
		ui.ErrorMsg(err.Error())
		return 1
	}

	if jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(map[string]interface{}{
			"base_dir": baseDir,
			"count":    len(repos),
			"repos":    repos,
		})
		return 0
	}

	fmt.Printf("%s Found %d repositories in %s\n\n", ui.Icons.Folder, len(repos), ui.Mute(baseDir))
	for _, repo := range repos {
		fmt.Printf("  %s %s\n", ui.Icons.Git, repo.DisplayName)
	}

	return 0
}

func runInit(cfgMgr *config.Manager, cmd string, args []string, jsonOutput bool) int {
	if hasHelpFlag(args) {
		printInitHelp()
		return 0
	}
	switch cmd {
	case "list", "ls":
		fs := flag.NewFlagSet("list", flag.ExitOnError)
		all := fs.Bool("all", false, "Include inactive repos")
		fs.Parse(args)
		if jsonOutput {
			repos := cfgMgr.GetAllRepos()
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			enc.Encode(repos)
			return 0
		}
		return initcmd.RunList(cfgMgr, *all)

	case "add", "a":
		fs := flag.NewFlagSet("add", flag.ExitOnError)
		fs.Parse(args)
		path := "."
		if len(fs.Args()) > 0 {
			path = fs.Args()[0]
		}
		return initcmd.RunAdd(cfgMgr, path)

	case "remove", "rm":
		fs := flag.NewFlagSet("remove", flag.ExitOnError)
		fs.Parse(args)
		path := "."
		if len(fs.Args()) > 0 {
			path = fs.Args()[0]
		}
		return initcmd.RunRemove(cfgMgr, path)

	default: // "init"
		fs := flag.NewFlagSet("init", flag.ExitOnError)
		baseDir := fs.String("base-dir", "", "Base directory to scan")
		yes := fs.Bool("y", false, "Accept all defaults")
		fs.BoolVar(yes, "yes", false, "Accept all defaults")
		fs.Parse(args)
		if jsonOutput {
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			enc.Encode(map[string]interface{}{
				"config_dir":    cfgMgr.ConfigDir,
				"tracked_repos": cfgMgr.TrackedRepos,
				"global_config": cfgMgr.GlobalConfig,
			})
			return 0
		}
		return initcmd.RunInit(cfgMgr, *baseDir, *yes)
	}
}

func runExec(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if hasHelpFlag(args) {
		printExecHelp()
		return 0
	}
	fs := flag.NewFlagSet("exec", flag.ExitOnError)
	var parallel int
	var failFast bool
	var only, exclude string
	fs.IntVar(&parallel, "p", 1, "Parallel workers")
	fs.BoolVar(&failFast, "fail-fast", false, "Stop on first error")
	fs.StringVar(&only, "only", "", "Only pattern")
	fs.StringVar(&exclude, "exclude", "", "Exclude pattern")
	fs.Parse(args)

	remaining := fs.Args()
	if len(remaining) == 0 {
		ui.ErrorMsg("No command specified")
		fmt.Println("Usage: iskra exec [flags] <command>")
		return 1
	}

	command := strings.Join(remaining, " ")
	repos := getRepos(cfgMgr, "", only, exclude)

	if len(repos) == 0 {
		ui.WarningMsg("No repositories found")
		return 0
	}

	opts := exec.Options{
		Parallel: parallel,
		FailFast: failFast,
		Quiet:    quiet,
	}

	result := exec.RunBatch(repos, command, opts)

	if jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		return 0
	}

	if !quiet {
		ui.CompactHeader()
		ui.InfoMsg(fmt.Sprintf("Running '%s' on %d repos", command, len(repos)))
		fmt.Println()
	}

	// Print results
	for _, r := range result.Results {
		if r.Success {
			fmt.Printf("%s %s\n", ui.DotSuccess, ui.Bold(r.Name))
		} else {
			fmt.Printf("%s %s %s\n", ui.DotError, ui.Bold(r.Name), ui.Err(fmt.Sprintf("(exit %d)", r.ExitCode)))
		}

		if r.Stdout != "" && !quiet {
			// Indent output
			lines := strings.Split(r.Stdout, "\n")
			for _, line := range lines {
				fmt.Printf("  %s\n", line)
			}
		}

		if r.Stderr != "" && !quiet {
			lines := strings.Split(r.Stderr, "\n")
			for _, line := range lines {
				fmt.Printf("  %s\n", ui.Err(line))
			}
		}
	}

	if !quiet {
		fmt.Println()
		ui.Summary("EXEC", result.ReposTotal, result.ReposSuccess, result.ReposFailed, result.Duration)
	}

	if result.ReposFailed > 0 {
		return 1
	}
	return 0
}

func runSync(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if hasHelpFlag(args) {
		printSyncHelp()
		return 0
	}
	repo, err := scanner.GetCurrentRepo()
	if err != nil || repo == nil {
		ui.ErrorMsg("Not in a git repository")
		return 1
	}

	proc := processor.NewProcessor(cfgMgr)
	opts := processor.Options{PullOnly: true}

	if jsonOutput {
		result := proc.ProcessRepo(repo.Path, opts)
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		return 0
	}

	if !quiet {
		ui.CompactHeader()
	}

	result := proc.ProcessRepo(repo.Path, opts)

	if !quiet {
		ui.RepoHeader(result.Name, result.Path, result.Branch, result.IsProtected, 1, 1)
		for _, op := range result.Operations {
			ui.Operation(op.Type, op.Success, op.Message)
		}
	}

	if result.Status == "success" {
		if !quiet {
			ui.SuccessMsg("Synced successfully")
		}
		return 0
	}

	ui.ErrorMsg(result.Error)
	return 1
}

func runSyncAll(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if hasHelpFlag(args) {
		printSyncAllHelp()
		return 0
	}
	fs := flag.NewFlagSet("sync-all", flag.ExitOnError)
	var only, exclude string
	fs.StringVar(&only, "only", "", "Only pattern")
	fs.StringVar(&exclude, "exclude", "", "Exclude pattern")
	fs.Parse(args)

	repos := getRepos(cfgMgr, "", only, exclude)

	if len(repos) == 0 {
		ui.WarningMsg("No repositories found")
		return 0
	}

	proc := processor.NewProcessor(cfgMgr)
	opts := processor.Options{PullOnly: true}

	if jsonOutput {
		result := proc.ProcessBatch(repos, opts)
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		return 0
	}

	if !quiet {
		ui.CompactHeader()
		ui.InfoMsg(fmt.Sprintf("Syncing %d repositories", len(repos)))
		fmt.Println()
	}

	start := time.Now()
	var successCount, failCount int

	for _, repoPath := range repos {
		r := proc.ProcessRepo(repoPath, opts)
		if r.Status == "success" {
			fmt.Printf("%s %s\n", ui.DotSuccess, r.Name)
			successCount++
		} else {
			fmt.Printf("%s %s %s\n", ui.DotError, r.Name, ui.Err(r.Error))
			failCount++
		}
	}

	if !quiet {
		ui.Summary("SYNC", len(repos), successCount, failCount, time.Since(start).Milliseconds())
	}

	if failCount > 0 {
		return 1
	}
	return 0
}

func runLog(args []string) int {
	if hasHelpFlag(args) {
		printLogHelp()
		return 0
	}
	fs := flag.NewFlagSet("log", flag.ExitOnError)
	var n int
	var oneline, graph, all bool
	var author, since, until, grep string
	fs.IntVar(&n, "n", 20, "Number of commits")
	fs.BoolVar(&oneline, "oneline", false, "One line format")
	fs.BoolVar(&graph, "graph", false, "Show graph")
	fs.BoolVar(&all, "all", false, "All branches")
	fs.StringVar(&author, "author", "", "Filter by author")
	fs.StringVar(&since, "since", "", "Since date")
	fs.StringVar(&until, "until", "", "Until date")
	fs.StringVar(&grep, "grep", "", "Search commits")
	fs.Parse(args)

	// Build git log command
	gitArgs := []string{"log", fmt.Sprintf("-n%d", n)}

	if oneline {
		gitArgs = append(gitArgs, "--oneline")
	} else {
		gitArgs = append(gitArgs, "--format=%C(cyan)%h%Creset %C(yellow)%ad%Creset %s %C(green)<%an>%Creset", "--date=short")
	}

	if graph {
		gitArgs = append(gitArgs, "--graph")
	}
	if all {
		gitArgs = append(gitArgs, "--all")
	}
	if author != "" {
		gitArgs = append(gitArgs, "--author="+author)
	}
	if since != "" {
		gitArgs = append(gitArgs, "--since="+since)
	}
	if until != "" {
		gitArgs = append(gitArgs, "--until="+until)
	}
	if grep != "" {
		gitArgs = append(gitArgs, "--grep="+grep)
	}

	// Run git log
	cmd := osexec.Command("git", gitArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return 1
	}
	return 0
}

func runInfo(jsonOutput bool, args []string) int {
	if hasHelpFlag(args) {
		printInfoHelp()
		return 0
	}
	repoInfo, err := info.GetInfo()
	if err != nil {
		ui.ErrorMsg(err.Error())
		return 1
	}

	if jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(repoInfo)
		return 0
	}

	info.Display(repoInfo)
	return 0
}

func runDiff(args []string) int {
	if hasHelpFlag(args) {
		printDiffHelp()
		return 0
	}
	fs := flag.NewFlagSet("diff", flag.ExitOnError)
	var staged, cached bool
	var stat bool
	fs.BoolVar(&staged, "staged", false, "Show staged changes")
	fs.BoolVar(&cached, "cached", false, "Show staged changes (alias)")
	fs.BoolVar(&stat, "stat", false, "Show diffstat only")
	fs.Parse(args)

	gitArgs := []string{"diff", "--color=always"}

	if staged || cached {
		gitArgs = append(gitArgs, "--staged")
	}
	if stat {
		gitArgs = append(gitArgs, "--stat")
	}

	// Add remaining args (file paths)
	gitArgs = append(gitArgs, fs.Args()...)

	cmd := osexec.Command("git", gitArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return 1
	}
	return 0
}

func runBranches(args []string) int {
	if hasHelpFlag(args) {
		printBranchesHelp()
		return 0
	}
	fs := flag.NewFlagSet("branches", flag.ExitOnError)
	var all, remote bool
	fs.BoolVar(&all, "all", false, "Show all branches")
	fs.BoolVar(&all, "a", false, "Show all branches")
	fs.BoolVar(&remote, "remote", false, "Show only remote branches")
	fs.BoolVar(&remote, "r", false, "Show only remote branches")
	fs.Parse(args)

	gitArgs := []string{"branch", "-v", "--color=always"}

	if all {
		gitArgs = append(gitArgs, "-a")
	} else if remote {
		gitArgs = append(gitArgs, "-r")
	}

	cmd := osexec.Command("git", gitArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return 1
	}
	return 0
}

func runStash(args []string) int {
	if hasHelpFlag(args) {
		printStashHelp()
		return 0
	}
	// Default to list if no subcommand
	subCmd := "list"
	if len(args) > 0 {
		subCmd = args[0]
		args = args[1:]
	}

	var gitArgs []string

	switch subCmd {
	case "list", "ls":
		gitArgs = []string{"stash", "list"}
	case "push", "save":
		gitArgs = []string{"stash", "push"}
		// Add message if provided
		if len(args) > 0 {
			gitArgs = append(gitArgs, "-m", strings.Join(args, " "))
		}
	case "pop":
		gitArgs = []string{"stash", "pop"}
		if len(args) > 0 {
			gitArgs = append(gitArgs, args[0])
		}
	case "apply":
		gitArgs = []string{"stash", "apply"}
		if len(args) > 0 {
			gitArgs = append(gitArgs, args[0])
		}
	case "drop":
		gitArgs = []string{"stash", "drop"}
		if len(args) > 0 {
			gitArgs = append(gitArgs, args[0])
		}
	case "show":
		gitArgs = []string{"stash", "show", "-p"}
		if len(args) > 0 {
			gitArgs = append(gitArgs, args[0])
		}
	case "clear":
		gitArgs = []string{"stash", "clear"}
	default:
		// Assume it's a stash reference like stash@{0}
		gitArgs = []string{"stash", "show", "-p", subCmd}
	}

	cmd := osexec.Command("git", gitArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return 1
	}
	return 0
}

func printRepoResult(result *processor.RepoResult, index, total int, quiet bool) {
	if quiet {
		status := "✓"
		if result.Status != "success" {
			status = "✗"
		}
		fmt.Printf("%s %s\n", status, result.Name)
		return
	}

	ui.RepoHeader(result.Name, result.Path, result.Branch, result.IsProtected, index, total)

	if result.Changes != nil && result.Changes.Total > 0 {
		fmt.Printf("  %d files changed\n", result.Changes.Total)
	} else {
		ui.SuccessMsg("Clean")
	}

	for _, op := range result.Operations {
		ui.Operation(op.Type, op.Success, op.Message)
	}

	if result.Commit != nil {
		fmt.Println()
		ui.CommitMessage(result.Commit.Message, result.Commit.IsAI)
	}

	fmt.Println()
	if result.Status == "success" {
		ui.SuccessMsg(fmt.Sprintf("completed in %dms", result.ElapsedMs))
	} else if result.Error != "" {
		ui.ErrorMsg(result.Error)
	}
	fmt.Println()
}

func getRepos(cfgMgr *config.Manager, scanDir, only, exclude string) []string {
	var repos []string

	var onlyPatterns, excludePatterns []string
	if only != "" {
		onlyPatterns = strings.Split(only, ",")
	}
	if exclude != "" {
		excludePatterns = strings.Split(exclude, ",")
	}

	if scanDir != "" {
		found, _ := scanner.FindGitRepos(scanner.Options{
			BaseDir:         scanDir,
			MaxDepth:        cfgMgr.GlobalConfig.MaxDepth,
			OnlyPatterns:    onlyPatterns,
			ExcludePatterns: excludePatterns,
		})
		for _, r := range found {
			repos = append(repos, r.Path)
		}
	} else {
		for _, repo := range cfgMgr.GetActiveRepos() {
			if !scanner.MatchesPatterns(repo.Name, onlyPatterns, excludePatterns) {
				continue
			}
			repos = append(repos, repo.Path)
		}
	}

	return repos
}

func runGH(args []string) int {
	if len(args) == 0 || hasHelpFlag(args) {
		printGHHelp()
		return 0
	}

	repoPath := ghcmd.GitRoot(".")
	if repoPath == "" {
		ui.ErrorMsg("Not inside a git repository")
		return 1
	}

	sub := args[0]
	rest := args[1:]

	switch sub {
	case "info":
		return ghcmd.RunInfo(repoPath)
	case "open":
		return ghcmd.RunOpen(repoPath)
	case "prs":
		fs := flag.NewFlagSet("prs", flag.ExitOnError)
		limit := fs.Int("limit", 50, "Max PRs to fetch")
		state := fs.String("state", "open", "State: open|closed|merged|all")
		draft := fs.String("draft", "all", "Draft filter: all|only|exclude")
		needReview := fs.Bool("need-review", false, "Only PRs needing review")
		requireChanges := fs.Bool("require-changes", false, "Only PRs with changes requested")
		openNum := fs.Int("open", 0, "Open PR number in browser")
		fs.Parse(rest)
		return ghcmd.RunPRs(repoPath, *limit, *state, *draft, *needReview, *requireChanges, *openNum)
	default:
		ui.ErrorMsg("Unknown gh subcommand: " + sub)
		return 1
	}
}

func runClone(args []string) int {
	if hasHelpFlag(args) {
		printCloneHelp()
		return 0
	}
	fs := flag.NewFlagSet("clone", flag.ExitOnError)
	baseDir := fs.String("base-dir", "~/Neoware", "Base directory for cloned repos")
	limit := fs.Int("limit", 1000, "Max repos to fetch")
	filterForks := fs.Bool("filter-forks", false, "Skip forked repositories")
	onlyStars := fs.Int("only-stars", 0, "Only repos with at least N stars")
	exclude := fs.String("exclude", "", "Comma-separated name patterns to exclude")
	fs.Parse(args)

	var excludePatterns []string
	if *exclude != "" {
		excludePatterns = strings.Split(*exclude, ",")
	}

	return clone.Run(clone.Options{
		BaseDir:     config.ExpandPath(*baseDir),
		Limit:       *limit,
		FilterForks: *filterForks,
		OnlyStars:   *onlyStars,
		Exclude:     excludePatterns,
	})
}
