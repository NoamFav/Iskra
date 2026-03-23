// Package pulse provides mono-repo focused git subcommands.
// All commands operate on the current working directory's git repo.
// Invoked as: iskra pulse <subcommand> [args...]
package pulse

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

// ── styles ────────────────────────────────────────────────────────────────────

var (
	bold     = lipgloss.NewStyle().Bold(true)
	dim      = lipgloss.NewStyle().Foreground(lipgloss.Color("245"))
	green    = lipgloss.NewStyle().Foreground(lipgloss.Color("82"))
	red      = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	yellow   = lipgloss.NewStyle().Foreground(lipgloss.Color("226"))
	cyan     = lipgloss.NewStyle().Foreground(lipgloss.Color("86"))
	magenta  = lipgloss.NewStyle().Foreground(lipgloss.Color("213"))
	orange   = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	errStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)
)

func errMsg(msg string) {
	fmt.Fprintln(os.Stderr, errStyle.Render("✗ ")+msg)
}

func okMsg(msg string) {
	fmt.Println(green.Render("✓ ") + msg)
}

func infoMsg(msg string) {
	fmt.Println(cyan.Render("→ ") + msg)
}

// ── helpers ───────────────────────────────────────────────────────────────────

func repoRoot() (string, error) {
	cmd := exec.Command("git", "rev-parse", "--show-toplevel")
	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("not in a git repository")
	}
	return strings.TrimSpace(string(out)), nil
}

func currentBranch() string {
	cmd := exec.Command("git", "rev-parse", "--abbrev-ref", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return "unknown"
	}
	return strings.TrimSpace(string(out))
}

func confirm(prompt string) bool {
	fmt.Printf("%s [y/N] ", yellow.Render("? ")+prompt)
	reader := bufio.NewReader(os.Stdin)
	line, _ := reader.ReadString('\n')
	line = strings.TrimSpace(strings.ToLower(line))
	return line == "y" || line == "yes"
}

func gitRun(args ...string) error {
	cmd := exec.Command("git", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	return cmd.Run()
}

func gitOutput(args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	out, err := cmd.Output()
	return strings.TrimSpace(string(out)), err
}

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

// ── tag ───────────────────────────────────────────────────────────────────────

// RunTag manages git tags.
// Usage:
//
//	iskra pulse tag                    → list tags
//	iskra pulse tag <name>             → create lightweight tag at HEAD
//	iskra pulse tag <name> -m <msg>    → create annotated tag
//	iskra pulse tag <name> <hash>      → tag a specific commit
//	iskra pulse tag --delete <name>    → delete a tag
//	iskra pulse tag --push [<name>]    → push tag(s) to origin
func RunTag(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	if len(args) == 0 {
		return listTags()
	}

	var deleteName, message, pushName, targetHash string
	var push bool
	var positional []string

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--delete", "-d":
			if i+1 < len(args) {
				i++
				deleteName = args[i]
			}
		case "--push":
			push = true
			if i+1 < len(args) && !strings.HasPrefix(args[i+1], "--") {
				i++
				pushName = args[i]
			}
		case "-m", "--message":
			if i+1 < len(args) {
				i++
				message = args[i]
			}
		default:
			positional = append(positional, args[i])
		}
	}

	if deleteName != "" {
		if !confirm(fmt.Sprintf("Delete tag %s?", red.Render(deleteName))) {
			infoMsg("Aborted.")
			return 0
		}
		if err := gitRun("tag", "-d", deleteName); err != nil {
			errMsg(fmt.Sprintf("Failed to delete tag: %s", deleteName))
			return 1
		}
		okMsg(fmt.Sprintf("Deleted tag %s", deleteName))
		return 0
	}

	if push {
		if pushName != "" {
			if err := gitRun("push", "origin", "refs/tags/"+pushName); err != nil {
				errMsg(fmt.Sprintf("Failed to push tag: %s", pushName))
				return 1
			}
			okMsg(fmt.Sprintf("Pushed tag %s to origin", pushName))
		} else {
			if err := gitRun("push", "origin", "--tags"); err != nil {
				errMsg("Failed to push tags")
				return 1
			}
			okMsg("Pushed all tags to origin")
		}
		return 0
	}

	if len(positional) == 0 {
		return listTags()
	}

	tagName := positional[0]
	if len(positional) > 1 {
		targetHash = positional[1]
	}

	// Create tag
	var tagArgs []string
	if message != "" {
		tagArgs = []string{"tag", "-a", tagName, "-m", message}
	} else {
		tagArgs = []string{"tag", tagName}
	}
	if targetHash != "" {
		tagArgs = append(tagArgs, targetHash)
	}

	if err := gitRun(tagArgs...); err != nil {
		errMsg(fmt.Sprintf("Failed to create tag: %s", tagName))
		return 1
	}

	kind := "lightweight"
	if message != "" {
		kind = "annotated"
	}
	okMsg(fmt.Sprintf("Created %s tag %s", kind, cyan.Render(tagName)))

	if confirm("Push tag to origin?") {
		if err := gitRun("push", "origin", "refs/tags/"+tagName); err != nil {
			errMsg("Failed to push tag")
			return 1
		}
		okMsg(fmt.Sprintf("Pushed %s to origin", tagName))
	}

	return 0
}

func listTags() int {
	out, err := gitOutput("tag", "--sort=-version:refname", "--format=%(refname:short)|||%(objecttype)|||%(taggerdate:short)|||%(subject)")
	if err != nil || strings.TrimSpace(out) == "" {
		infoMsg("No tags found")
		return 0
	}

	type tagEntry struct {
		name    string
		kind    string
		date    string
		subject string
	}

	var tags []tagEntry
	for line := range strings.SplitSeq(out, "\n") {
		parts := strings.SplitN(line, "|||", 4)
		if len(parts) < 4 || parts[0] == "" {
			continue
		}
		kind := "lightweight"
		if parts[1] == "tag" {
			kind = "annotated"
		}
		tags = append(tags, tagEntry{parts[0], kind, parts[2], parts[3]})
	}

	if len(tags) == 0 {
		infoMsg("No tags found")
		return 0
	}

	fmt.Println()
	fmt.Println(bold.Render("Tags:"))
	fmt.Println()

	// Sort by name descending (already done via --sort)
	for _, t := range tags {
		kindStr := dim.Render("light")
		if t.kind == "annotated" {
			kindStr = cyan.Render("annot")
		}
		dateStr := ""
		if t.date != "" {
			dateStr = dim.Render(t.date)
		}
		subj := ""
		if t.subject != "" {
			subj = "  " + dim.Render(t.subject)
		}
		fmt.Printf("  %s  %s  %s%s\n", yellow.Render(t.name), kindStr, dateStr, subj)
	}
	fmt.Println()
	return 0
}

// ── filter ────────────────────────────────────────────────────────────────────

// RunFilter provides a guided wrapper around git filter-repo.
// Requires git-filter-repo to be installed.
// Usage:
//
//	iskra pulse filter --path <path>           → keep only this path
//	iskra pulse filter --remove-path <path>    → remove a path from history
//	iskra pulse filter --replace-text <file>   → replace strings (from expressions file)
//	iskra pulse filter --strip-blobs-bigger-than <size>  → e.g. 10M
//	iskra pulse filter --email <old>=><new>    → rewrite committer email
func RunFilter(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	// Check git-filter-repo is available
	if _, err := exec.LookPath("git-filter-repo"); err != nil {
		errMsg("git-filter-repo is not installed")
		fmt.Println()
		fmt.Println(dim.Render("  Install it:"))
		fmt.Println("  " + cyan.Render("pip3 install git-filter-repo"))
		fmt.Println("  " + cyan.Render("brew install git-filter-repo"))
		fmt.Println()
		return 1
	}

	if len(args) == 0 {
		printFilterHelp()
		return 0
	}

	var keepPath, removePath, replaceFile, stripSize, emailRewrite string

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--path":
			if i+1 < len(args) {
				i++
				keepPath = args[i]
			}
		case "--remove-path":
			if i+1 < len(args) {
				i++
				removePath = args[i]
			}
		case "--replace-text":
			if i+1 < len(args) {
				i++
				replaceFile = args[i]
			}
		case "--strip-blobs-bigger-than":
			if i+1 < len(args) {
				i++
				stripSize = args[i]
			}
		case "--email":
			if i+1 < len(args) {
				i++
				emailRewrite = args[i]
			}
		}
	}

	// Build filter-repo args
	var filterArgs []string

	if keepPath != "" {
		filterArgs = append(filterArgs, "--path", keepPath)
	}
	if removePath != "" {
		filterArgs = append(filterArgs, "--path", removePath, "--invert-paths")
	}
	if replaceFile != "" {
		if _, err := os.Stat(replaceFile); err != nil {
			errMsg(fmt.Sprintf("Replace text file not found: %s", replaceFile))
			return 1
		}
		filterArgs = append(filterArgs, "--replace-text", replaceFile)
	}
	if stripSize != "" {
		filterArgs = append(filterArgs, "--strip-blobs-bigger-than", stripSize)
	}
	if emailRewrite != "" {
		// format: "old@email.com==>new@email.com"
		parts := strings.SplitN(emailRewrite, "==>", 2)
		if len(parts) != 2 {
			errMsg("Email format must be: old@email.com==>new@email.com")
			return 1
		}
		// use --email-callback with a mailmap-style replacement
		filterArgs = append(filterArgs, "--email-callback",
			fmt.Sprintf("return email if email != b'%s' else b'%s'", parts[0], parts[1]))
	}

	if len(filterArgs) == 0 {
		printFilterHelp()
		return 0
	}

	fmt.Println()
	fmt.Println(bold.Render("git-filter-repo") + "  " + dim.Render("(rewrites history — irreversible)"))
	fmt.Println()
	fmt.Printf("  Command: %s\n", cyan.Render("git-filter-repo "+strings.Join(filterArgs, " ")))
	fmt.Println()
	fmt.Println(red.Render("  ⚠  This rewrites commit history permanently."))
	fmt.Println(dim.Render("     Make a backup before proceeding."))
	fmt.Println()

	if !confirm("Proceed with filter-repo?") {
		infoMsg("Aborted.")
		return 0
	}

	cmd := exec.Command("git-filter-repo", filterArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	if err := cmd.Run(); err != nil {
		errMsg("filter-repo failed")
		return 1
	}

	okMsg("History rewrite complete")
	fmt.Println()
	fmt.Println(dim.Render("  Note: remote refs were removed (expected). Force-push if needed:"))
	fmt.Println("  " + cyan.Render("git remote add origin <url>"))
	fmt.Println("  " + cyan.Render("git push origin --force --all --tags"))
	fmt.Println()
	return 0
}

func printFilterHelp() {
	fmt.Println()
	fmt.Println(bold.Render("iskra pulse filter") + " — git history rewriting")
	fmt.Println()
	fmt.Println(dim.Render("  Requires: ") + cyan.Render("git-filter-repo"))
	fmt.Println()
	fmt.Println(bold.Render("Usage:"))
	fmt.Println()
	fmt.Printf("  %s  %s\n", cyan.Render("--path <dir>"), dim.Render("Keep only this path in history"))
	fmt.Printf("  %s  %s\n", cyan.Render("--remove-path <path>"), dim.Render("Erase a path from all history"))
	fmt.Printf("  %s  %s\n", cyan.Render("--replace-text <file>"), dim.Render("Rewrite strings (one 'old==>new' per line)"))
	fmt.Printf("  %s  %s\n", cyan.Render("--strip-blobs-bigger-than <size>"), dim.Render("Remove large files (e.g. 10M)"))
	fmt.Printf("  %s  %s\n", cyan.Render("--email old==>new"), dim.Render("Rewrite committer email across history"))
	fmt.Println()
}

// ── blame ─────────────────────────────────────────────────────────────────────

// RunBlame shows a pretty per-line blame for a file.
// Usage: iskra pulse blame <file> [--lines <n>] [--since <rev>]
func RunBlame(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	var file, since string
	var lineLimit int

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--lines", "-n":
			if i+1 < len(args) {
				i++
				lineLimit, _ = strconv.Atoi(args[i])
			}
		case "--since":
			if i+1 < len(args) {
				i++
				since = args[i]
			}
		default:
			if file == "" {
				file = args[i]
			}
		}
	}

	if file == "" {
		errMsg("Usage: iskra pulse blame <file> [--lines <n>] [--since <rev>]")
		return 1
	}

	// Resolve file: if relative, try from cwd first, then from repo root
	if !filepath.IsAbs(file) {
		if _, err := os.Stat(file); os.IsNotExist(err) {
			if root, err2 := repoRoot(); err2 == nil {
				file = filepath.Join(root, file)
			}
		}
	}

	blameArgs := []string{"blame", "--line-porcelain"}
	if since != "" {
		blameArgs = append(blameArgs, since+"..HEAD")
	}
	blameArgs = append(blameArgs, file)

	cmd := exec.Command("git", blameArgs...)
	out, err := cmd.Output()
	if err != nil {
		errMsg(fmt.Sprintf("Failed to blame %s: %v", file, err))
		return 1
	}

	type blameEntry struct {
		hash    string
		author  string
		date    string
		lineNum int
		content string
	}

	var entries []blameEntry
	var cur blameEntry
	authorColors := make(map[string]lipgloss.Color)
	colorPalette := []lipgloss.Color{"82", "39", "213", "226", "196", "86", "214", "201"}
	colorIdx := 0

	lines := strings.SplitSeq(string(out), "\n")
	for line := range lines {
		if len(line) == 0 {
			continue
		}
		if len(line) > 40 && !strings.HasPrefix(line, "\t") {
			fields := strings.Fields(line)
			if len(fields) >= 3 {
				hash := fields[0]
				if len(hash) == 40 {
					cur.hash = hash[:7]
					lineNum, _ := strconv.Atoi(fields[2])
					cur.lineNum = lineNum
				}
			}
		}
		if after, ok := strings.CutPrefix(line, "author "); ok {
			cur.author = after
			if _, ok := authorColors[cur.author]; !ok {
				authorColors[cur.author] = colorPalette[colorIdx%len(colorPalette)]
				colorIdx++
			}
		}
		if after, ok := strings.CutPrefix(line, "author-time "); ok {
			ts, _ := strconv.ParseInt(after, 10, 64)
			// format as YYYY-MM-DD
			cur.date = fmt.Sprintf("%d", ts) // will reformat below
			_ = ts
		}
		if after, ok := strings.CutPrefix(line, "committer-time "); ok {
			ts, _ := strconv.ParseInt(after, 10, 64)
			cur.date = time.Unix(ts, 0).UTC().Format("2006-01-02")
		}
		if after, ok := strings.CutPrefix(line, "\t"); ok {
			cur.content = after
			entries = append(entries, cur)
			cur = blameEntry{}
		}
	}

	if lineLimit > 0 && lineLimit < len(entries) {
		entries = entries[:lineLimit]
	}

	// Calculate author column width
	maxAuthorLen := 0
	for a := range authorColors {
		if len(a) > maxAuthorLen {
			maxAuthorLen = len(a)
		}
	}
	if maxAuthorLen > 14 {
		maxAuthorLen = 14
	}

	fmt.Println()
	fmt.Println(bold.Render(filepath.Base(file)))
	fmt.Println()

	prevHash := ""
	for _, e := range entries {
		hashStr := dim.Render(e.hash)
		if e.hash != prevHash {
			hashStr = yellow.Render(e.hash)
		}
		prevHash = e.hash

		author := e.author
		if len(author) > maxAuthorLen {
			author = author[:maxAuthorLen-1] + "…"
		}
		color := authorColors[e.author]
		authorStr := lipgloss.NewStyle().Foreground(color).Render(fmt.Sprintf("%-*s", maxAuthorLen, author))

		lineNumStr := dim.Render(fmt.Sprintf("%4d", e.lineNum))
		content := e.content
		// truncate very long lines
		if len(content) > 80 {
			content = content[:77] + "..."
		}

		fmt.Printf("  %s  %s  %s  %s\n", hashStr, authorStr, lineNumStr, content)
	}
	fmt.Println()
	return 0
}

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

// ── dispatch ──────────────────────────────────────────────────────────────────

// Dispatch routes "iskra pulse <subcommand>" to the right function.
// Returns exit code.
func Dispatch(sub string, args []string) int {
	switch sub {
	case "reset":
		return RunReset(args)
	case "switch", "sw":
		return RunSwitch(args)
	case "cherry-pick", "cp":
		return RunCherryPick(args)
	case "rebase", "rb":
		return RunRebase(args)
	case "tag":
		return RunTag(args)
	case "filter":
		return RunFilter(args)
	case "blame":
		return RunBlame(args)
	case "fixup":
		return RunFixup(args)
	case "help", "-h", "--help":
		printPulseHelp()
		return 0
	default:
		printPulseHelp()
		return 1
	}
}

func printPulseHelp() {
	fmt.Println()
	fmt.Println(bold.Render("iskra pulse") + " — mono-repo operations")
	fmt.Println()
	fmt.Println(dim.Render("  Usage: iskra pulse <subcommand> [args...]"))
	fmt.Println()

	cmds := [][]string{
		{"(no sub)", "Commit and push current repo"},
		{"reset", "Discard changes (file or all, staged or unstaged)"},
		{"switch", "Switch or create branches with listing UI"},
		{"cherry-pick", "Pick commits onto current branch"},
		{"rebase", "Rebase current branch onto a target"},
		{"tag", "Create, list, delete, and push tags"},
		{"fixup", "Squash staged changes into a past commit"},
		{"blame", "Per-line author view of a file"},
		{"filter", "Rewrite history (wraps git-filter-repo)"},
	}

	maxLen := 0
	for _, c := range cmds {
		if len(c[0]) > maxLen {
			maxLen = len(c[0])
		}
	}

	for _, c := range cmds {
		fmt.Printf("  %s  %s\n",
			cyan.Render(fmt.Sprintf("%-*s", maxLen, c[0])),
			dim.Render(c[1]),
		)
	}
	fmt.Println()

	// Show sort order
	_ = sort.Search // imported for use in switchInteractive
}
