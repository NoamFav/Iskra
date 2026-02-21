// Package clone implements iskra clone — bulk GitHub repo cloning via gh CLI.
package clone

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/NoamFav/iskra/internal/ui"
)

// GHRepo holds fields from `gh repo list --json`.
type GHRepo struct {
	NameWithOwner string `json:"nameWithOwner"`
	Name          string `json:"name"`
	Description   string `json:"description"`
	IsPrivate     bool   `json:"isPrivate"`
	IsFork        bool   `json:"isFork"`
	StargazerCount int   `json:"stargazerCount"`
	URL           string `json:"url"`
}

// Options configures the clone run.
type Options struct {
	BaseDir     string
	Limit       int
	FilterForks bool
	OnlyStars   int
	Exclude     []string
}

// matchAny returns true if name matches any of the glob patterns.
func matchAny(name string, patterns []string) bool {
	for _, pat := range patterns {
		matched, _ := filepath.Match(pat, name)
		if matched {
			return true
		}
		// Also match substring
		if strings.Contains(name, pat) {
			return true
		}
	}
	return false
}

// findRepoInSubdirs searches base for a dir named repoName.
func findRepoInSubdirs(base, repoName string) string {
	var found string
	filepath.WalkDir(base, func(path string, d fs.DirEntry, err error) error {
		if err != nil || !d.IsDir() {
			return nil
		}
		if d.Name() == repoName {
			// Confirm it's a git repo
			if _, err := os.Stat(filepath.Join(path, ".git")); err == nil {
				found = path
				return fs.SkipAll
			}
		}
		return nil
	})
	return found
}

// dirSize returns human-readable size of a directory.
func dirSize(path string) string {
	var total int64
	filepath.WalkDir(path, func(_ string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}
		if info, err := d.Info(); err == nil {
			total += info.Size()
		}
		return nil
	})
	switch {
	case total >= 1<<30:
		return fmt.Sprintf("%.2f GiB", float64(total)/(1<<30))
	case total >= 1<<20:
		return fmt.Sprintf("%.2f MiB", float64(total)/(1<<20))
	case total >= 1<<10:
		return fmt.Sprintf("%.2f KiB", float64(total)/(1<<10))
	default:
		return fmt.Sprintf("%d B", total)
	}
}

// FetchRepos fetches the user's GitHub repos via gh CLI.
func FetchRepos(opts Options) ([]GHRepo, error) {
	fields := "nameWithOwner,name,description,isPrivate,isFork,stargazerCount,url"
	cmd := exec.Command("gh", "repo", "list",
		"--limit", fmt.Sprintf("%d", opts.Limit),
		"--json", fields,
	)

	fmt.Printf("%s Fetching repositories from GitHub...\n", ui.Icons.Git)

	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("gh repo list failed: %w", err)
	}

	var repos []GHRepo
	if err := json.Unmarshal(out, &repos); err != nil {
		return nil, fmt.Errorf("parse error: %w", err)
	}

	// Apply filters
	var filtered []GHRepo
	for _, r := range repos {
		if opts.FilterForks && r.IsFork {
			continue
		}
		if opts.OnlyStars > 0 && r.StargazerCount < opts.OnlyStars {
			continue
		}
		if matchAny(r.NameWithOwner, opts.Exclude) {
			continue
		}
		filtered = append(filtered, r)
	}

	fmt.Printf("%s Found %s repositories\n\n", ui.Icons.Success, ui.Bold(fmt.Sprintf("%d", len(filtered))))
	return filtered, nil
}

// CloneRepo clones a single repo into baseDir. Returns true on success.
func CloneRepo(repo GHRepo, baseDir string, idx, total int) bool {
	shortName := repo.Name
	if shortName == "" {
		parts := strings.SplitN(repo.NameWithOwner, "/", 2)
		if len(parts) == 2 {
			shortName = parts[1]
		}
	}

	privStr := ui.Icons.File
	if repo.IsPrivate {
		privStr = ui.Icons.Lock
	}
	forkStr := ""
	if repo.IsFork {
		forkStr = " (fork)"
	}
	starStr := ""
	if repo.StargazerCount > 0 {
		starStr = fmt.Sprintf(" ★%d", repo.StargazerCount)
	}

	fmt.Printf("[%d/%d] %s %s%s%s\n", idx, total,
		privStr, ui.Bold(repo.NameWithOwner), forkStr, starStr)
	if repo.Description != "" {
		fmt.Printf("       %s\n", ui.Mute(repo.Description))
	}

	// Check if already exists
	if existing := findRepoInSubdirs(baseDir, shortName); existing != "" {
		rel, _ := filepath.Rel(baseDir, existing)
		fmt.Printf("       %s already exists at %s\n\n", ui.Warn(ui.Icons.Warning), rel)
		return true
	}

	start := time.Now()
	cmd := exec.Command("gh", "repo", "clone", repo.NameWithOwner)
	cmd.Dir = baseDir
	cmd.Stdout = nil
	out, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("       %s clone failed: %s\n\n", ui.Err(ui.Icons.Error), strings.TrimSpace(string(out)))
		return false
	}

	elapsed := time.Since(start).Round(time.Millisecond)
	repoDir := filepath.Join(baseDir, shortName)
	size := dirSize(repoDir)
	fmt.Printf("       %s cloned in %s (%s)\n\n", ui.Success(ui.Icons.Success), elapsed, size)
	return true
}

// Run executes the full clone flow.
func Run(opts Options) int {
	if err := os.MkdirAll(opts.BaseDir, 0755); err != nil {
		ui.ErrorMsg("Cannot create base dir: " + err.Error())
		return 1
	}

	repos, err := FetchRepos(opts)
	if err != nil {
		ui.ErrorMsg(err.Error())
		return 1
	}

	if len(repos) == 0 {
		ui.WarningMsg("No repositories to clone")
		return 0
	}

	success, total := 0, len(repos)
	for i, r := range repos {
		if CloneRepo(r, opts.BaseDir, i+1, total) {
			success++
		}
	}

	fmt.Printf("────────────────────────────────────────\n")
	if success == total {
		fmt.Printf("%s %s/%d repositories processed\n\n", ui.Icons.Success, ui.Success(fmt.Sprintf("%d", success)), total)
	} else {
		fmt.Printf("%s %d/%d repositories processed\n\n", ui.Icons.Warning, success, total)
	}
	return 0
}
