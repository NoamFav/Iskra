// Package batch implements the iskra commands that operate across a
// selected set of tracked repos via the processor engine: commit, status,
// exec, sync, sync-all, and the default (no-subcommand) "iskra pulse"
// single-repo commit.
package batch

import (
	"fmt"

	"github.com/NoamFav/iskra/internal/processor"
	"github.com/NoamFav/iskra/internal/ui"
)

// printRepoResult prints a single repo's processing result.
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
		ui.Operation(op.Type, op.Success, op.Message, op.Error)
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
