package git

import (
	"bytes"

	"os/exec"
	"strings"
)

func Diff() string            { return runOut("git", "diff") }
func StagedDiff() string      { return runOut("git", "diff", "--staged") }
func StatusPorcelain() string { return runOut("git", "status", "--porcelain") }
func Branch() string          { return strings.TrimSpace(runOut("git", "rev-parse", "--abbrev-ref", "HEAD")) }
func AddAll() error           { return run("git", "add", ".") }
func Commit(msg string) error { return run("git", "commit", "-m", msg) }
func Push() error             { return run("git", "push") }
func Pull() error             { return run("git", "pull") }

func ChangedFiles() []string {
	out := runOut("git", "diff", "--name-only")
	var res []string
	for _, f := range strings.Split(strings.TrimSpace(out), "\n") {
		if f != "" {
			res = append(res, f)
		}
	}
	return res
}

func StagedFiles() []string {
	out := runOut("git", "diff", "--staged", "--name-only")
	var res []string
	for _, f := range strings.Split(strings.TrimSpace(out), "\n") {
		if f != "" {
			res = append(res, f)
		}
	}
	return res
}

func DetectType() string {
	diff := strings.ToLower(Diff() + StagedDiff())
	added := bytes.Count([]byte(diff), []byte("\n+"))
	removed := bytes.Count([]byte(diff), []byte("\n-"))

	switch {
	case strings.Contains(diff, "fix") || strings.Contains(diff, "bug"):
		return "fix"
	case strings.Contains(diff, "refactor"):
		return "refactor"
	case added > removed:
		return "feat"
	case removed > added:
		return "refactor"
	default:
		return "chore"
	}
}

func run(name string, args ...string) error {
	cmd := exec.Command(name, args...)
	cmd.Stdout, cmd.Stderr = nil, nil
	return cmd.Run()
}
func runOut(name string, args ...string) string {
	cmd := exec.Command(name, args...)
	b, _ := cmd.Output()
	return string(b)
}
