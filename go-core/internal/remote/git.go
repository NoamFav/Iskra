// Package remote provides operations against git and its hosted
// providers (GitHub via github.go, one file per provider).
//
// git.go: generic local git operations via exec commands (used by every
// provider file). We use exec instead of go-git for full git compatibility.
package remote

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
)

// Status represents the status of a file in git
type Status struct {
	Code     string `json:"code"`
	FilePath string `json:"path"`
}

// RepoState holds the current state of a repository
type RepoState struct {
	Path         string   `json:"path"`
	Name         string   `json:"name"`
	Branch       string   `json:"branch"`
	IsClean      bool     `json:"is_clean"`
	StatusOutput string   `json:"status_output"`
	ChangesCount int      `json:"changes_count"`
	Conflicts    []string `json:"conflicts,omitempty"`
	RemoteURL    string   `json:"remote_url,omitempty"`
	Ahead        int      `json:"ahead"`
	Behind       int      `json:"behind"`
}

// RunResult holds the result of a git command
type RunResult struct {
	Success bool   `json:"success"`
	Output  string `json:"output"`
	Error   string `json:"error,omitempty"`
}

// run executes a git command in the given directory
func run(dir string, args ...string) (string, error) {

	cmd := exec.Command("git", args...)
	cmd.Dir = dir

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	if err != nil {
		return stderr.String(), err
	}

	return strings.TrimSpace(stdout.String()), nil
}

// runWithResult executes a git command and returns a RunResult
func runWithResult(dir string, args ...string) RunResult {
	output, err := run(dir, args...)
	if err != nil {
		return RunResult{
			Success: false,
			Output:  output,
			Error:   err.Error(),
		}
	}
	return RunResult{
		Success: true,
		Output:  output,
	}
}

// IsGitRepo checks if a directory is a git repository
func IsGitRepo(path string) bool {
	gitDir := filepath.Join(path, ".git")
	info, err := os.Stat(gitDir)
	if err != nil {
		return false
	}
	return info.IsDir()
}

// GetCurrentBranch returns the current branch name
func GetCurrentBranch(dir string) (string, error) {
	return run(dir, "rev-parse", "--abbrev-ref", "HEAD")
}

// GetStatusPorcelain returns git status in porcelain format
func GetStatusPorcelain(dir string) (string, error) {
	return run(dir, "status", "--porcelain")
}

// HasChanges checks if there are uncommitted changes
func HasChanges(dir string) bool {
	output, err := GetStatusPorcelain(dir)
	if err != nil {
		return false
	}
	return strings.TrimSpace(output) != ""
}

// GetRemoteURL returns the remote origin URL
func GetRemoteURL(dir string) (string, error) {
	return run(dir, "remote", "get-url", "origin")
}

// IsSSHRemote checks if the remote uses SSH
func IsSSHRemote(dir string) bool {
	url, err := GetRemoteURL(dir)
	if err != nil {
		return false
	}
	return strings.HasPrefix(url, "git@") || strings.Contains(url, "ssh://")
}

// CheckSSHAgentHasKeys checks if ssh-agent has keys loaded
func CheckSSHAgentHasKeys() bool {
	cmd := exec.Command("ssh-add", "-l")
	err := cmd.Run()
	return err == nil
}

// GetDiff returns the diff of staged or unstaged changes
func GetDiff(dir string, staged bool) (string, error) {
	args := []string{"diff"}
	if staged {
		args = append(args, "--cached")
	}
	return run(dir, args...)
}

// GetDiffFull returns diff with full context
func GetDiffFull(dir string, staged bool) (string, error) {
	args := []string{"diff", "-U10"}
	if staged {
		args = append(args, "--cached")
	}
	return run(dir, args...)
}

// AddAll stages all changes
func AddAll(dir string) RunResult {
	return runWithResult(dir, "add", "-A")
}

// Commit creates a commit with the given message
func Commit(dir, message string) RunResult {
	return runWithResult(dir, "commit", "-m", message)
}

// Push pushes to origin
func Push(dir string) RunResult {
	return runWithResult(dir, "push")
}

// Pull pulls from origin
func Pull(dir string) RunResult {
	return runWithResult(dir, "pull")
}

// Stash stashes changes
func Stash(dir string) RunResult {
	return runWithResult(dir, "stash")
}

// StashPop pops stashed changes
func StashPop(dir string) RunResult {
	return runWithResult(dir, "stash", "pop")
}

// GetLastCommit returns info about the last commit
func GetLastCommit(dir string) (string, error) {
	return run(dir, "show", "--no-patch", "--format=%H|%s|%an|%ai")
}

// CheckForConflicts returns files with merge conflicts
func CheckForConflicts(dir string) []string {
	output, err := run(dir, "diff", "--name-only", "--diff-filter=U")
	if err != nil {
		return nil
	}
	if output == "" {
		return nil
	}
	return strings.Split(output, "\n")
}

// CheckWouldConflictOnPull checks if pull would cause conflicts
func CheckWouldConflictOnPull(dir string) bool {
	// Fetch first
	_, err := run(dir, "fetch")
	if err != nil {
		return false
	}

	// Try merge with --no-commit --no-ff
	_, err = run(dir, "merge", "--no-commit", "--no-ff", "FETCH_HEAD")
	if err != nil {
		// Abort the merge
		run(dir, "merge", "--abort")
		return true
	}

	// Abort the merge
	run(dir, "merge", "--abort")
	return false
}

// IsProtectedBranch checks if branch is in protected list
func IsProtectedBranch(branch string, protected []string) bool {
	return slices.Contains(protected, branch)
}

// GetAheadBehind returns how many commits ahead/behind of remote
func GetAheadBehind(dir string) (ahead, behind int) {
	output, err := run(dir, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
	if err != nil {
		return 0, 0
	}

	parts := strings.Fields(output)
	if len(parts) == 2 {
		// Parse ahead count
		if n, err := parseInt(parts[0]); err == nil {
			ahead = n
		}
		// Parse behind count
		if n, err := parseInt(parts[1]); err == nil {
			behind = n
		}
	}

	return
}

// Helper to parse int from string
func parseInt(s string) (int, error) {
	return strconv.Atoi(strings.TrimSpace(s))
}

// GetRepoState returns full repository state.
// Uses `git status --porcelain=v1 -b` to get branch, ahead/behind, file
// status, and conflicts in a single call. Only remote URL needs a second call.
func GetRepoState(dir string) (*RepoState, error) {
	name := filepath.Base(dir)

	// Single call: branch header + file statuses
	raw, err := run(dir, "status", "--porcelain=v1", "-b")
	if err != nil {
		return nil, err
	}

	var branch string
	var ahead, behind int
	var statusLines []string
	var conflicts []string

	lines := strings.Split(raw, "\n")
	for _, line := range lines {
		if strings.HasPrefix(line, "## ") {
			branch, ahead, behind = parseBranchHeader(line)
			continue
		}
		if line == "" {
			continue
		}
		statusLines = append(statusLines, line)
		if len(line) >= 2 && line[0] == 'U' || line[1] == 'U' ||
			(line[0] == 'A' && line[1] == 'A') ||
			(line[0] == 'D' && line[1] == 'D') {
			conflicts = append(conflicts, strings.TrimSpace(line[3:]))
		}
	}

	statusOutput := strings.Join(statusLines, "\n")
	changesCount := len(statusLines)

	remoteURL, _ := GetRemoteURL(dir)

	return &RepoState{
		Path:         dir,
		Name:         name,
		Branch:       branch,
		IsClean:      changesCount == 0,
		StatusOutput: statusOutput,
		ChangesCount: changesCount,
		Conflicts:    conflicts,
		RemoteURL:    remoteURL,
		Ahead:        ahead,
		Behind:       behind,
	}, nil
}

// parseBranchHeader parses the "## branch...tracking [ahead N, behind M]" line
// from `git status --porcelain -b`.
func parseBranchHeader(line string) (branch string, ahead, behind int) {
	// "## main...origin/main [ahead 2, behind 1]"
	// "## main...origin/main"
	// "## HEAD (no branch)"
	// "## main"
	header := strings.TrimPrefix(line, "## ")

	// Extract [ahead N, behind M] if present
	if idx := strings.Index(header, " ["); idx >= 0 {
		bracket := header[idx+2 : len(header)-1] // strip "[ ... ]"
		header = header[:idx]
		for _, part := range strings.Split(bracket, ", ") {
			part = strings.TrimSpace(part)
			if after, ok := strings.CutPrefix(part, "ahead "); ok {
				ahead, _ = strconv.Atoi(after)
			}
			if after, ok := strings.CutPrefix(part, "behind "); ok {
				behind, _ = strconv.Atoi(after)
			}
		}
	}

	// Extract branch name (before "..." tracking info)
	if idx := strings.Index(header, "..."); idx >= 0 {
		branch = header[:idx]
	} else {
		branch = header
	}

	return
}

// ParseStatus parses porcelain status output into Status structs
func ParseStatus(output string) []Status {
	if output == "" {
		return nil
	}

	var statuses []Status
	lines := strings.SplitSeq(output, "\n")
	for line := range lines {
		if len(line) < 4 {
			continue
		}
		statuses = append(statuses, Status{
			Code:     strings.TrimSpace(line[:2]),
			FilePath: strings.TrimSpace(line[3:]),
		})
	}
	return statuses
}

// RunHookCommand runs a pre/post commit hook command
func RunHookCommand(dir, command string) (int, string, string) {
	cmd := exec.Command("sh", "-c", command)
	cmd.Dir = dir

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	exitCode := 0
	if exitErr, ok := err.(*exec.ExitError); ok {
		exitCode = exitErr.ExitCode()
	} else if err != nil {
		exitCode = 1
	}

	return exitCode, stdout.String(), stderr.String()
}
