package pulse

import (
	"fmt"
	"os"
	"strings"
)

// ── rebase ────────────────────────────────────────────────────────────────────

// RunRebase provides a guided rebase experience.
// Usage: iskra pulse rebase [<base>] [--onto <newbase>] [--abort] [--continue] [--skip]
//
//	iskra pulse rebase           → rebase onto upstream (origin/<branch>)
//	iskra pulse rebase main      → rebase current branch onto main
//	iskra pulse rebase --abort   → abort in-progress rebase
//	iskra pulse rebase --continue→ continue after conflict resolution
func RunRebase(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	// Handle control flags first
	for _, a := range args {
		switch a {
		case "--abort":
			// Check if rebase is actually in progress
			root, _ := repoRoot()
			rebaseDir := root + "/.git/rebase-merge"
			rebaseApply := root + "/.git/rebase-apply"
			if _, err := os.Stat(rebaseDir); os.IsNotExist(err) {
				if _, err2 := os.Stat(rebaseApply); os.IsNotExist(err2) {
					infoMsg("No rebase in progress")
					return 0
				}
			}
			infoMsg("Aborting rebase...")
			if err := gitRun("rebase", "--abort"); err != nil {
				errMsg("Failed to abort rebase")
				return 1
			}
			okMsg("Rebase aborted")
			return 0
		case "--continue":
			infoMsg("Continuing rebase...")
			if err := gitRun("rebase", "--continue"); err != nil {
				errMsg("Rebase continue failed — fix remaining conflicts")
				return 1
			}
			okMsg("Rebase continued")
			return 0
		case "--skip":
			if err := gitRun("rebase", "--skip"); err != nil {
				errMsg("Rebase skip failed")
				return 1
			}
			okMsg("Commit skipped")
			return 0
		}
	}

	var onto, base string
	for i := 0; i < len(args); i++ {
		if args[i] == "--onto" && i+1 < len(args) {
			i++
			onto = args[i]
		} else if !strings.HasPrefix(args[i], "--") {
			base = args[i]
		}
	}

	current := currentBranch()

	// Default: rebase onto upstream
	if base == "" {
		// Try to find tracking branch
		upstream, err := gitOutput("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
		if err != nil || upstream == "" {
			errMsg("No upstream set. Specify a base: iskra pulse rebase <branch>")
			return 1
		}
		base = upstream
	}

	// Show commits that will be rebased
	out, _ := gitOutput("log", "--oneline", base+"..HEAD")
	commits := strings.Split(strings.TrimSpace(out), "\n")
	if out == "" || (len(commits) == 1 && commits[0] == "") {
		infoMsg(fmt.Sprintf("Nothing to rebase — %s is up to date with %s", cyan.Render(current), cyan.Render(base)))
		return 0
	}

	fmt.Println()
	fmt.Println(bold.Render(fmt.Sprintf("Rebase %s onto %s", cyan.Render(current), cyan.Render(base))))
	fmt.Println()
	fmt.Println(dim.Render(fmt.Sprintf("  %d commit(s) will be replayed:", len(commits))))
	for _, c := range commits {
		fmt.Printf("  %s %s\n", cyan.Render("◆"), c)
	}
	fmt.Println()

	if !confirm("Proceed with rebase?") {
		infoMsg("Aborted.")
		return 0
	}

	var rebaseArgs []string
	if onto != "" {
		rebaseArgs = []string{"rebase", "--onto", onto, base}
	} else {
		rebaseArgs = []string{"rebase", base}
	}

	if err := gitRun(rebaseArgs...); err != nil {
		fmt.Println()
		fmt.Println(red.Render("Rebase conflict detected."))
		fmt.Println(dim.Render("  Resolve conflicts, then:"))
		fmt.Println("  " + cyan.Render("iskra pulse rebase --continue"))
		fmt.Println("  " + cyan.Render("iskra pulse rebase --abort") + dim.Render("  (to cancel)"))
		return 1
	}

	okMsg(fmt.Sprintf("Rebase onto %s complete", base))
	return 0
}
