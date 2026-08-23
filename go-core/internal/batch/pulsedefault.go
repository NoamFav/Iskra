package batch

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"

	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/processor"
	"github.com/NoamFav/iskra/internal/scanner"
	"github.com/NoamFav/iskra/internal/ui"
)

// RunPulseDefault implements "iskra pulse" with no subcommand: commit+push
// the current repo only.
func RunPulseDefault(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	repo, err := scanner.GetCurrentRepo()
	if err != nil || repo == nil {
		ui.ErrorMsg("Not in a git repository")
		return 1
	}

	fs := flag.NewFlagSet("pulse", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
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
	if err := fs.Parse(args); err != nil {
		printPulseHelp()
		return 1
	}

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
