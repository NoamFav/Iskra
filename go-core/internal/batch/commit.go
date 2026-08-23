package batch

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/processor"
	"github.com/NoamFav/iskra/internal/scanner"
	"github.com/NoamFav/iskra/internal/ui"
)

// RunCommit implements "iskra commit" (also the default command).
func RunCommit(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
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

	repos := scanner.SelectRepos(cfgMgr, scanDir, only, exclude)
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
