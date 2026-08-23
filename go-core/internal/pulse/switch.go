package pulse

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// ── switch ────────────────────────────────────────────────────────────────────

// RunSwitch checks out a branch with a nice listing UI.
// Usage: iskra pulse switch [<branch>] [--new|-b <name>] [--delete|-d <name>]
func RunSwitch(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	for _, a := range args {
		if a == "-h" || a == "--help" || a == "help" {
			fmt.Println()
			fmt.Println(bold.Render("iskra pulse switch") + " — branch management")
			fmt.Println()
			fmt.Println(dim.Render("  (no args)            ") + "Interactive branch picker")
			fmt.Println(dim.Render("  <branch>             ") + "Switch to branch")
			fmt.Println(dim.Render("  --new|-b <name>      ") + "Create and switch to new branch")
			fmt.Println(dim.Render("  --delete|-d <name>   ") + "Delete a branch")
			fmt.Println()
			return 0
		}
	}

	var newBranch, deleteBranch, target string
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--new", "-b":
			if i+1 < len(args) {
				i++
				newBranch = args[i]
			}
		case "--delete", "-d":
			if i+1 < len(args) {
				i++
				deleteBranch = args[i]
			}
		default:
			target = args[i]
		}
	}

	// Create new branch
	if newBranch != "" {
		infoMsg(fmt.Sprintf("Creating and switching to branch: %s", cyan.Render(newBranch)))
		if err := gitRun("switch", "-c", newBranch); err != nil {
			errMsg("Failed to create branch")
			return 1
		}
		okMsg(fmt.Sprintf("Switched to new branch %s", cyan.Render(newBranch)))
		return 0
	}

	// Delete branch
	if deleteBranch != "" {
		current := currentBranch()
		if deleteBranch == current {
			errMsg("Cannot delete the currently checked-out branch")
			return 1
		}
		if !confirm(fmt.Sprintf("Delete branch %s?", red.Render(deleteBranch))) {
			infoMsg("Aborted.")
			return 0
		}
		if err := gitRun("branch", "-d", deleteBranch); err != nil {
			// offer force delete
			if confirm(fmt.Sprintf("Branch not fully merged. Force delete %s?", red.Render(deleteBranch))) {
				if err2 := gitRun("branch", "-D", deleteBranch); err2 != nil {
					errMsg("Force delete failed")
					return 1
				}
			} else {
				return 1
			}
		}
		okMsg(fmt.Sprintf("Deleted branch %s", deleteBranch))
		return 0
	}

	// Switch to named branch
	if target != "" {
		if err := gitRun("switch", target); err != nil {
			// Might be a remote branch — try with --track
			if err2 := gitRun("switch", "--track", "origin/"+target); err2 != nil {
				errMsg(fmt.Sprintf("Branch not found: %s", target))
				return 1
			}
		}
		okMsg(fmt.Sprintf("Switched to %s", cyan.Render(target)))
		return 0
	}

	// No args — show branch list and let user pick
	return switchInteractive()
}

func switchInteractive() int {
	out, err := gitOutput("branch", "--all", "--format=%(refname:short)|||%(objectname:short)|||%(committerdate:relative)|||%(subject)")
	if err != nil {
		errMsg("Failed to list branches")
		return 1
	}

	current := currentBranch()

	type branchEntry struct {
		name    string
		hash    string
		when    string
		subject string
		remote  bool
	}

	var locals, remotes []branchEntry
	seen := make(map[string]bool)

	for line := range strings.SplitSeq(out, "\n") {
		parts := strings.SplitN(line, "|||", 4)
		if len(parts) < 4 {
			continue
		}
		name := parts[0]
		if strings.HasPrefix(name, "origin/HEAD") {
			continue
		}
		isRemote := strings.HasPrefix(name, "origin/")
		shortName := strings.TrimPrefix(name, "origin/")
		if seen[shortName] {
			continue
		}
		seen[shortName] = true
		e := branchEntry{
			name:    shortName,
			hash:    parts[1],
			when:    parts[2],
			subject: parts[3],
			remote:  isRemote && !seen[shortName+"_local"],
		}
		if isRemote {
			remotes = append(remotes, e)
		} else {
			locals = append(locals, e)
		}
	}

	fmt.Println()
	fmt.Println(bold.Render("Local branches:"))
	fmt.Println()
	for i, b := range locals {
		marker := "  "
		nameRender := b.name
		if b.name == current {
			marker = green.Render("* ")
			nameRender = green.Render(b.name)
		}
		subj := b.subject
		if len(subj) > 40 {
			subj = subj[:37] + "..."
		}
		fmt.Printf("  %s%2d  %s  %s  %s\n",
			marker,
			i+1,
			cyan.Render(b.hash),
			nameRender,
			dim.Render(subj),
		)
	}

	if len(remotes) > 0 {
		fmt.Println()
		fmt.Println(bold.Render("Remote branches:"))
		fmt.Println()
		for i, b := range remotes {
			subj := b.subject
			if len(subj) > 40 {
				subj = subj[:37] + "..."
			}
			fmt.Printf("  %2d  %s  %s  %s\n",
				len(locals)+i+1,
				cyan.Render(b.hash),
				yellow.Render(b.name),
				dim.Render(subj),
			)
		}
	}

	all := append(locals, remotes...)
	fmt.Println()
	fmt.Printf("%s ", yellow.Render("? Branch number (or name):"))
	reader := bufio.NewReader(os.Stdin)
	input, _ := reader.ReadString('\n')
	input = strings.TrimSpace(input)

	if input == "" || input == "q" {
		infoMsg("Aborted.")
		return 0
	}

	// Try as number
	if n, err := strconv.Atoi(input); err == nil {
		if n < 1 || n > len(all) {
			errMsg("Invalid number")
			return 1
		}
		target := all[n-1].name
		if target == current {
			infoMsg(fmt.Sprintf("Already on %s", cyan.Render(target)))
			return 0
		}
		if err := gitRun("switch", target); err != nil {
			if err2 := gitRun("switch", "--track", "origin/"+target); err2 != nil {
				errMsg(fmt.Sprintf("Failed to switch to %s", target))
				return 1
			}
		}
		okMsg(fmt.Sprintf("Switched to %s", cyan.Render(target)))
		return 0
	}

	// Try as name
	if err := gitRun("switch", input); err != nil {
		if err2 := gitRun("switch", "--track", "origin/"+input); err2 != nil {
			errMsg(fmt.Sprintf("Branch not found: %s", input))
			return 1
		}
	}
	okMsg(fmt.Sprintf("Switched to %s", cyan.Render(input)))
	return 0
}
