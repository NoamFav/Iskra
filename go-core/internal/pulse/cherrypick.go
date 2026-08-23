package pulse

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// ── cherry-pick ───────────────────────────────────────────────────────────────

// RunCherryPick cherry-picks one or more commits with a log preview.
// Usage: iskra pulse cherry-pick <hash> [<hash>...] [--no-commit]
func RunCherryPick(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	var noCommit bool
	var hashes []string
	for _, a := range args {
		if a == "--no-commit" || a == "-n" {
			noCommit = true
		} else {
			hashes = append(hashes, a)
		}
	}

	if len(hashes) == 0 {
		// Show recent log and ask
		return cherryPickInteractive()
	}

	// Show what we're about to pick
	fmt.Println()
	fmt.Println(bold.Render("Cherry-picking:"))
	for _, h := range hashes {
		out, err := gitOutput("log", "-1", "--pretty=format:%h %s (%ar)", h)
		if err != nil {
			errMsg(fmt.Sprintf("Commit not found: %s", h))
			return 1
		}
		fmt.Printf("  %s %s\n", cyan.Render("◆"), out)
	}
	fmt.Println()

	if !confirm(fmt.Sprintf("Cherry-pick %d commit(s) onto %s?", len(hashes), cyan.Render(currentBranch()))) {
		infoMsg("Aborted.")
		return 0
	}

	gitArgs := []string{"cherry-pick"}
	if noCommit {
		gitArgs = append(gitArgs, "--no-commit")
	}
	gitArgs = append(gitArgs, hashes...)

	if err := gitRun(gitArgs...); err != nil {
		errMsg("Cherry-pick failed — resolve conflicts then run: git cherry-pick --continue")
		return 1
	}
	okMsg("Cherry-pick complete")
	return 0
}

func cherryPickInteractive() int {
	// show log of all branches to pick from
	out, err := gitOutput("log", "--all", "--oneline", "--decorate", "-20")
	if err != nil {
		errMsg("Failed to get log")
		return 1
	}

	fmt.Println()
	fmt.Println(bold.Render("Recent commits (all branches):"))
	fmt.Println()
	lines := strings.Split(out, "\n")
	for i, line := range lines {
		fmt.Printf("  %2d  %s\n", i+1, line)
	}
	fmt.Println()
	fmt.Printf("%s ", yellow.Render("? Commit number(s) to cherry-pick (space-separated):"))
	reader := bufio.NewReader(os.Stdin)
	input, _ := reader.ReadString('\n')
	input = strings.TrimSpace(input)
	if input == "" {
		infoMsg("Aborted.")
		return 0
	}

	var hashes []string
	for tok := range strings.FieldsSeq(input) {
		if n, err := strconv.Atoi(tok); err == nil {
			if n >= 1 && n <= len(lines) {
				// extract hash (first word)
				hash := strings.Fields(lines[n-1])[0]
				hashes = append(hashes, hash)
			}
		} else {
			hashes = append(hashes, tok)
		}
	}

	if len(hashes) == 0 {
		errMsg("No valid commits selected")
		return 1
	}

	return RunCherryPick(hashes)
}
