// iskra is the main Iskra CLI.
// Uses Lip Gloss for styled terminal output.
package main

import (
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/NoamFav/iskra/internal/batch"
	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/info"
	initcmd "github.com/NoamFav/iskra/internal/init"
	"github.com/NoamFav/iskra/internal/pulse"
	"github.com/NoamFav/iskra/internal/remote"
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

	args := cmdArgs

	if showHelp {
		if cmd == "" {
			printHelp()
			return
		}
		args = append([]string{"-h"}, args...)
	}

	ui.SetMinimalMode(minimal)

	cfgMgr, err := config.NewManager(configDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading config: %v\n", err)
		os.Exit(1)
	}

	var exitCode int
	switch cmd {
	case "", "commit":
		exitCode = batch.RunCommit(cfgMgr, args, jsonOutput, quiet)
	case "status", "s":
		exitCode = batch.RunStatus(cfgMgr, args, jsonOutput, quiet)
	case "pulse", "p":
		exitCode = runPulseCmd(cfgMgr, args, jsonOutput, quiet)
	case "scan":
		exitCode = scanner.RunScan(cfgMgr, args, jsonOutput)
	case "init", "list", "ls", "add", "remove", "rm", "verify":
		exitCode = initcmd.Dispatch(cfgMgr, cmd, args, jsonOutput)
	case "exec":
		exitCode = batch.RunExec(cfgMgr, args, jsonOutput, quiet)
	case "check":
		exitCode = scanner.RunCheck(cfgMgr, args)
	case "sync":
		exitCode = batch.RunSync(cfgMgr, args, jsonOutput, quiet)
	case "sync-all":
		exitCode = batch.RunSyncAll(cfgMgr, args, jsonOutput, quiet)
	case "log":
		exitCode = pulse.RunLog(args)
	case "info":
		exitCode = info.RunCLI(jsonOutput, args)
	case "diff":
		exitCode = pulse.RunDiff(args)
	case "branches", "br":
		exitCode = pulse.RunBranches(args)
	case "stash":
		exitCode = pulse.RunStash(args)
	case "gh":
		exitCode = remote.Dispatch(args)
	case "clone":
		exitCode = remote.RunCLI(args)
	case "help":
		printHelp()
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", cmd)
		printHelp()
		exitCode = 1
	}

	os.Exit(exitCode)
}

// runPulseCmd is the dispatcher for "iskra pulse [subcommand]".
// With no subcommand it runs the classic commit+push on the current repo.
// With a subcommand (reset, switch, cherry-pick, rebase, tag, fixup, blame, filter)
// it delegates to the pulse package.
func runPulseCmd(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if ui.HasHelpFlag(args) {
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
	return batch.RunPulseDefault(cfgMgr, args, jsonOutput, quiet)
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
	fmt.Println("    check         Check tracked repos still exist, untrack missing ones")
	fmt.Println("    log           Show git log (pretty)")
	fmt.Println("    info          Repository info (like onefetch)")
	fmt.Println("    diff          Show git diff (colored)")
	fmt.Println("    branches, br  List all branches")
	fmt.Println("    stash         Stash management (list, push, pop)")
	fmt.Println("    gh            GitHub integration (info, open, prs)")
	fmt.Println("    clone         Bulk clone GitHub repositories")
	fmt.Println("    init          Scan and track repositories")
	fmt.Println("    verify        Check and fix tracked repo info")
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
	fmt.Println(ui.Mute("  Run 'iskra <command> -h' for command-specific flags."))
	fmt.Println()
}
