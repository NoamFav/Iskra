// Package ui provides styled CLI output.
package ui

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

// HasHelpFlag reports whether args contains a help flag.
func HasHelpFlag(args []string) bool {
	for _, a := range args {
		if a == "-h" || a == "-help" || a == "--help" {
			return true
		}
	}
	return false
}

// Header prints the Iskra header
func Header() {
	logo := `
  ██╗███████╗██╗  ██╗██████╗  █████╗
  ██║██╔════╝██║ ██╔╝██╔══██╗██╔══██╗
  ██║███████╗█████╔╝ ██████╔╝███████║
  ██║╚════██║██╔═██╗ ██╔══██╗██╔══██║
  ██║███████║██║  ██╗██║  ██║██║  ██║
  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝`

	fmt.Println(TitleStyle.Render(logo))
	fmt.Println()
	fmt.Printf("  %s\n", Mute("Intelligent Git automation with AI-powered commits"))
	fmt.Printf("  %s\n\n", Mute(time.Now().Format("2006-01-02 15:04:05")))
}

// CompactHeader prints a minimal header
func CompactHeader() {
	fmt.Printf("%s %s\n\n", Title("⚡ Iskra"), Mute(time.Now().Format("15:04:05")))
}

// RepoHeader prints a repository header
func RepoHeader(name, path, branch string, isProtected bool, index, total int) {
	// Name with icon
	fmt.Printf("\n%s %s", Icons.Git, Bold(name))

	// Protected badge
	if isProtected {
		badge := lipgloss.NewStyle().
			Background(ColorWarning).
			Foreground(lipgloss.Color("0")).
			Padding(0, 1).
			Render("protected")
		fmt.Printf(" %s", badge)
	}

	// Progress
	fmt.Printf(" %s\n", Mute(fmt.Sprintf("[%d/%d]", index, total)))

	// Path
	fmt.Printf("%s\n", Mute(path))

	// Branch
	fmt.Printf("  %s %s\n", Icons.Branch, branch)
}

// ChangesTree prints file changes as a tree
func ChangesTree(statusOutput string) {
	if statusOutput == "" {
		fmt.Printf("  %s %s\n", Icons.Check, Success("No changes"))
		return
	}

	lines := strings.Split(strings.TrimSpace(statusOutput), "\n")
	fmt.Printf("%d files changed\n", len(lines))

	for i, line := range lines {
		if len(line) < 4 {
			continue
		}

		code := strings.TrimSpace(line[:2])
		filepath := strings.TrimSpace(line[3:])

		// Tree branch
		branch := "├──"
		if i == len(lines)-1 {
			branch = "└──"
		}

		// Status icon and color
		var icon string
		var styled string
		switch {
		case code == "??":
			icon = Icons.Untracked
			styled = Warn(filepath)
		case code == "A" || code[0] == 'A':
			icon = Icons.Add
			styled = Success(filepath)
		case code == "M" || code[0] == 'M' || code[1] == 'M':
			icon = Icons.Modified
			styled = Inf(filepath)
		case code == "D" || code[0] == 'D':
			icon = Icons.Deleted
			styled = Err(filepath)
		default:
			icon = Icons.File
			styled = filepath
		}

		fmt.Printf("%s %s %s\n", Mute(branch), icon, styled)
	}
}

// Operation prints an operation result
func Operation(opType string, success bool, message string, errMsg string) {
	var icon string
	if success {
		icon = Icons.Success
		fmt.Printf("  %s %s", Success(icon), Bold(opType))
	} else {
		icon = Icons.Error
		fmt.Printf("  %s %s", Err(icon), Bold(opType))
	}

	if message != "" {
		fmt.Printf(" %s", Mute(message))
	}
	if errMsg != "" {
		fmt.Printf(" %s", Err(errMsg))
	}
	fmt.Println()
}

// CommitMessage prints the commit message
func CommitMessage(message string, isAI bool) {
	var title string
	if isAI {
		title = fmt.Sprintf("%s AI Generated Commit", Icons.Spark)
	} else {
		title = fmt.Sprintf("%s Commit", Icons.Commit)
	}

	box := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorSuccess).
		Padding(0, 1).
		Width(60)

	content := fmt.Sprintf("%s\n%s", Title(title), message)
	fmt.Println(box.Render(content))
}

// Summary prints the final summary
func Summary(operation string, total, success, failed int, elapsedMs int64) {
	divider := Mute(strings.Repeat("─", 60))
	fmt.Println()
	fmt.Println(divider)

	title := Bold(fmt.Sprintf("%s summary", strings.ToUpper(operation)))
	fmt.Println(title)

	elapsed := time.Duration(elapsedMs) * time.Millisecond

	var statusIcon string
	if failed == 0 {
		statusIcon = Icons.Success
		fmt.Printf("%s Repositories: %s\n",
			Success(statusIcon),
			Success(fmt.Sprintf("%d/%d success", success, total)),
		)
	} else {
		statusIcon = Icons.Warning
		fmt.Printf("%s Repositories: %s, %s\n",
			Warn(statusIcon),
			Success(fmt.Sprintf("%d success", success)),
			Err(fmt.Sprintf("%d failed", failed)),
		)
	}

	fmt.Printf("%s Elapsed: %s\n", Mute(Icons.Clock), Mute(elapsed.Round(time.Millisecond).String()))
}

// ProgressBar prints a progress indicator
func ProgressBar(current, total int) string {
	if total == 0 {
		return ""
	}
	pct := float64(current) / float64(total)
	width := 20
	filled := int(pct * float64(width))
	bar := strings.Repeat("█", filled) + strings.Repeat("░", width-filled)
	return fmt.Sprintf("[%s] %d/%d", Inf(bar), current, total)
}

// ErrorMsg prints an error
func ErrorMsg(msg string) {
	fmt.Printf("%s %s\n", Err(Icons.Error), msg)
}

// WarningMsg prints a warning
func WarningMsg(msg string) {
	fmt.Printf("%s %s\n", Warn(Icons.Warning), msg)
}

// InfoMsg prints info
func InfoMsg(msg string) {
	fmt.Printf("%s %s\n", Inf(Icons.Info), msg)
}

// SuccessMsg prints success
func SuccessMsg(msg string) {
	fmt.Printf("%s %s\n", Success(Icons.Success), msg)
}

// Elapsed prints elapsed time
func Elapsed(ms int64) {
	d := time.Duration(ms) * time.Millisecond
	fmt.Printf("  %s %s\n", Mute(Icons.Clock), Mute(d.Round(time.Millisecond).String()))
}
