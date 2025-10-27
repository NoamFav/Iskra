package main

import (
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/NoamFav/autocommit/internal/git"
	"github.com/NoamFav/autocommit/internal/llm"
)

func firstLine(s string) string {
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		return strings.TrimSpace(s[:i])
	}
	return strings.TrimSpace(s)
}

func main() {
	var pull bool
	var msg string
	flag.BoolVar(&pull, "pull", false, "git pull before commit")
	flag.StringVar(&msg, "m", "auto-commit", "commit message or 'auto-commit'")
	flag.Parse()

	if pull {
		_ = git.Pull()
	}

	if err := git.AddAll(); err != nil {
		fmt.Println("git add failed:", err)
		os.Exit(1)
	}

	if strings.TrimSpace(git.StatusPorcelain()) == "" {
		fmt.Println("No changes to commit.")
		return
	}

	if msg == "auto-commit" {
		// Build a lightweight prompt using current branch + type + a truncated diff
		diff := git.StagedDiff()
		if diff == "" {
			diff = git.Diff()
		}
		if len(diff) > 2000 {
			diff = diff[:2000] + " ... (truncated)"
		}

		typ := git.DetectType()
		scope := git.Branch()
		prompt := fmt.Sprintf(`Write a conventional commit:
<type>(<scope>): <subject>

Type candidates: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
Use imperative mood. No period. Only output the final line.

Suggested type: %s
Scope: %s

Changes (truncated):
%s`, typ, scope, diff)

		gen := llm.AskOllama(prompt)
		msg = firstLine(gen)
		if msg == "" {
			msg = fmt.Sprintf("%s(%s): update", typ, scope)
		}
	}

	if err := git.Commit(msg); err != nil {
		fmt.Println("git commit failed:", err)
		os.Exit(1)
	}
	if err := git.Push(); err != nil {
		fmt.Println("git push failed:", err)
		os.Exit(1)
	}
	fmt.Println("Done.")
}
