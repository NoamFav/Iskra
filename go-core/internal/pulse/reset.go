package pulse

import (
	"fmt"
	"strings"
)

// ── reset ─────────────────────────────────────────────────────────────────────

// RunReset discards changes in working tree.
// Usage: iskra pulse reset [<file>...] [--hard] [--staged]
//
//	--staged  : unstage files only (git restore --staged)
//	--hard    : full hard reset to HEAD (dangerous, requires confirm)
//	<files>   : restore specific files
func RunReset(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	var hard, staged bool
	var files []string
	for _, a := range args {
		switch a {
		case "--hard":
			hard = true
		case "--staged", "-s":
			staged = true
		default:
			files = append(files, a)
		}
	}

	if hard {
		branch := currentBranch()
		fmt.Println()
		fmt.Println(bold.Render("Hard reset to HEAD"))
		fmt.Println(dim.Render("  This will discard ALL uncommitted changes on ") + cyan.Render(branch))
		fmt.Println()
		if !confirm("Are you sure? This cannot be undone.") {
			infoMsg("Aborted.")
			return 0
		}
		if err := gitRun("reset", "--hard", "HEAD"); err != nil {
			errMsg("Hard reset failed")
			return 1
		}
		okMsg("Hard reset to HEAD complete")
		return 0
	}

	if len(files) == 0 {
		// Show status first
		showPendingFiles()
		fmt.Println()
		if !confirm("Discard all changes in working tree?") {
			infoMsg("Aborted.")
			return 0
		}
		if staged {
			if err := gitRun("restore", "--staged", "."); err != nil {
				errMsg("Failed to unstage")
				return 1
			}
			okMsg("All staged changes unstaged")
		} else {
			if err := gitRun("restore", "."); err != nil {
				errMsg("Failed to restore working tree")
				return 1
			}
			okMsg("Working tree restored to HEAD")
		}
		return 0
	}

	// File-specific reset
	for _, f := range files {
		if staged {
			if err := gitRun("restore", "--staged", f); err != nil {
				errMsg(fmt.Sprintf("Failed to unstage %s", f))
				return 1
			}
			okMsg(fmt.Sprintf("Unstaged: %s", f))
		} else {
			if err := gitRun("restore", f); err != nil {
				errMsg(fmt.Sprintf("Failed to restore %s", f))
				return 1
			}
			okMsg(fmt.Sprintf("Restored: %s", f))
		}
	}
	return 0
}

func showPendingFiles() {
	out, err := gitOutput("status", "--porcelain")
	if err != nil || out == "" {
		fmt.Println(dim.Render("  (no changes)"))
		return
	}
	for line := range strings.SplitSeq(out, "\n") {
		if len(line) < 3 {
			continue
		}
		xy := line[:2]
		file := strings.TrimSpace(line[3:])
		var marker string
		switch {
		case strings.ContainsAny(xy, "AM"):
			marker = green.Render(xy)
		case strings.ContainsAny(xy, "D"):
			marker = red.Render(xy)
		case strings.ContainsAny(xy, "?"):
			marker = dim.Render(xy)
		default:
			marker = yellow.Render(xy)
		}
		fmt.Printf("  %s  %s\n", marker, file)
	}
}
