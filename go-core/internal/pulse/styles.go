// Package pulse provides mono-repo focused git subcommands.
// All commands operate on the current working directory's git repo.
// Invoked as: iskra pulse <subcommand> [args...]
package pulse

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strings"

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
