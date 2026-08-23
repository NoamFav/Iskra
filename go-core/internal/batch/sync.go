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

// RunSync implements "iskra sync": pull the current repo.
func RunSync(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if ui.HasHelpFlag(args) {
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
			ui.Operation(op.Type, op.Success, op.Message, op.Error)
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

// RunSyncAll implements "iskra sync-all": pull all tracked repos.
func RunSyncAll(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if ui.HasHelpFlag(args) {
		printSyncAllHelp()
		return 0
	}
	fs := flag.NewFlagSet("sync-all", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var only, exclude string
	fs.StringVar(&only, "only", "", "Only pattern")
	fs.StringVar(&exclude, "exclude", "", "Exclude pattern")
	if err := fs.Parse(args); err != nil {
		printSyncAllHelp()
		return 1
	}

	repos := scanner.SelectRepos(cfgMgr, "", only, exclude)

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
