package pulse

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
)

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
