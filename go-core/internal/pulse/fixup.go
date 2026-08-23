package pulse

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
)

// ── fixup ─────────────────────────────────────────────────────────────────────

// RunFixup squashes staged changes into a past commit.
// Usage: iskra pulse fixup [<hash>]
func RunFixup(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	// Check there are staged changes
	staged, err := gitOutput("diff", "--cached", "--name-only")
	if err != nil || staged == "" {
		errMsg("No staged changes to fixup — stage files first with: git add <files>")
		return 1
	}

	stagedFiles := strings.Split(staged, "\n")
	fmt.Println()
	fmt.Println(bold.Render("Staged changes to fixup:"))
	for _, f := range stagedFiles {
		if f != "" {
			fmt.Printf("  %s  %s\n", green.Render("+"), f)
		}
	}
	fmt.Println()

	var targetHash string
	if len(args) > 0 {
		targetHash = args[0]
	}

	if targetHash == "" {
		// Show recent commits to pick from
		out, _ := gitOutput("log", "--oneline", "-15")
		fmt.Println(bold.Render("Pick commit to fixup into:"))
		fmt.Println()
		logLines := strings.Split(out, "\n")
		for i, line := range logLines {
			if line != "" {
				fmt.Printf("  %2d  %s\n", i+1, line)
			}
		}
		fmt.Println()
		fmt.Printf("%s ", yellow.Render("? Commit number or hash:"))
		reader := bufio.NewReader(os.Stdin)
		input, _ := reader.ReadString('\n')
		input = strings.TrimSpace(input)
		if input == "" {
			infoMsg("Aborted.")
			return 0
		}
		if n, err := strconv.Atoi(input); err == nil {
			if n >= 1 && n <= len(logLines) {
				targetHash = strings.Fields(logLines[n-1])[0]
			}
		} else {
			targetHash = input
		}
	}

	// Show the commit
	commitInfo, err := gitOutput("log", "-1", "--oneline", targetHash)
	if err != nil {
		errMsg(fmt.Sprintf("Commit not found: %s", targetHash))
		return 1
	}
	fmt.Printf("\n  Fixup into: %s\n\n", cyan.Render(commitInfo))

	if !confirm("Squash staged changes into this commit? (rewrites history)") {
		infoMsg("Aborted.")
		return 0
	}

	// Create fixup commit then autosquash
	if err := gitRun("commit", "--fixup", targetHash); err != nil {
		errMsg("Failed to create fixup commit")
		return 1
	}

	// Rebase with autosquash — non-interactive
	env := append(os.Environ(), "GIT_SEQUENCE_EDITOR=true")
	cmd := exec.Command("git", "rebase", "--interactive", "--autosquash", targetHash+"^")
	cmd.Env = env
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		errMsg("Autosquash rebase failed")
		return 1
	}

	okMsg(fmt.Sprintf("Fixup squashed into %s", cyan.Render(commitInfo)))
	return 0
}
