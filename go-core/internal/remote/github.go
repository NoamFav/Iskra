// github.go: the GitHub provider — iskra gh subcommands (info/open/prs) and
// iskra clone (bulk clone). All calls go through the gh CLI.
package remote

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/ui"
)

// Dispatch routes "iskra gh <subcommand>" to the right handler.
func Dispatch(args []string) int {
	if len(args) == 0 || ui.HasHelpFlag(args) {
		printGHHelp()
		return 0
	}

	repoPath := GitRoot(".")
	if repoPath == "" {
		ui.ErrorMsg("Not inside a git repository")
		return 1
	}

	sub := args[0]
	rest := args[1:]

	switch sub {
	case "info":
		return RunInfo(repoPath)
	case "open":
		return RunOpen(repoPath)
	case "prs":
		fs := flag.NewFlagSet("prs", flag.ContinueOnError)
		fs.SetOutput(io.Discard)
		limit := fs.Int("limit", 50, "Max PRs to fetch")
		state := fs.String("state", "open", "State: open|closed|merged|all")
		draft := fs.String("draft", "all", "Draft filter: all|only|exclude")
		needReview := fs.Bool("need-review", false, "Only PRs needing review")
		requireChanges := fs.Bool("require-changes", false, "Only PRs with changes requested")
		openNum := fs.Int("open", 0, "Open PR number in browser")
		if err := fs.Parse(rest); err != nil {
			printGHHelp()
			return 1
		}
		return RunPRs(repoPath, *limit, *state, *draft, *needReview, *requireChanges, *openNum)
	default:
		ui.ErrorMsg("Unknown gh subcommand: " + sub)
		return 1
	}
}

func printGHHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra gh") + " - GitHub integration")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra gh <subcommand> [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("SUBCOMMANDS:"))
	fmt.Println("    info    Show GitHub info for current repo")
	fmt.Println("    open    Open repo page in browser")
	fmt.Println("    prs     List pull requests")
	fmt.Println()
	fmt.Println(ui.Bold("PRS FLAGS:"))
	fmt.Println("    -limit <n>          Max PRs to fetch (default: 50)")
	fmt.Println("    -state <s>          open|closed|merged|all (default: open)")
	fmt.Println("    -draft <s>          all|only|exclude (default: all)")
	fmt.Println("    -need-review        Only PRs awaiting review")
	fmt.Println("    -require-changes    Only PRs with changes requested")
	fmt.Println("    -open <n>           Open PR number in browser")
	fmt.Println()
}

// GitRoot returns the git root of the given path, or "" if not a git repo.
func GitRoot(path string) string {
	out, err := exec.Command("git", "-C", path, "rev-parse", "--show-toplevel").Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}

// RemoteURL returns the origin remote URL, or "" if none.
func RemoteURL(repoPath string) string {
	out, err := exec.Command("git", "-C", repoPath, "remote", "get-url", "origin").Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}

// GithubSlug parses a git remote URL into owner/repo form, or "" if not GitHub.
func GithubSlug(remoteURL string) string {
	if !strings.Contains(remoteURL, "github.com") {
		return ""
	}
	url := strings.TrimRight(remoteURL, "/")
	url = strings.TrimSuffix(url, ".git")
	if after, ok := strings.CutPrefix(url, "git@github.com:"); ok {
		return after
	}
	if idx := strings.Index(url, "github.com/"); idx >= 0 {
		return url[idx+len("github.com/"):]
	}
	return ""
}

// RunInfo prints GitHub info for the current repo.
func RunInfo(repoPath string) int {
	remote := RemoteURL(repoPath)
	if remote == "" {
		ui.ErrorMsg("No 'origin' remote found")
		return 1
	}
	slug := GithubSlug(remote)
	slugStr := slug
	if slugStr == "" {
		slugStr = ui.Mute("not a GitHub repo")
	}

	fmt.Printf("\n  %-12s %s\n", ui.Bold("Path"), repoPath)
	fmt.Printf("  %-12s %s\n", ui.Bold("Remote"), remote)
	fmt.Printf("  %-12s %s\n\n", ui.Bold("Slug"), slugStr)
	return 0
}

// RunOpen opens the GitHub repo page in the default browser.
func RunOpen(repoPath string) int {
	remote := RemoteURL(repoPath)
	if remote == "" {
		ui.ErrorMsg("No 'origin' remote found")
		return 1
	}
	slug := GithubSlug(remote)
	if slug == "" {
		ui.ErrorMsg("Remote is not a GitHub URL")
		return 1
	}
	url := "https://github.com/" + slug
	fmt.Printf("%s Opening %s\n", ui.Icons.Arrow, ui.Inf(url))
	if err := exec.Command("open", url).Start(); err != nil {
		// fallback for Linux
		exec.Command("xdg-open", url).Start()
	}
	return 0
}

// RepoDescription fetches the GitHub description for a single repo via gh CLI.
// Prefer FetchAllDescriptions for batch operations.
func RepoDescription(remoteURL string) string {
	slug := GithubSlug(remoteURL)
	if slug == "" {
		return ""
	}
	out, err := exec.Command("gh", "repo", "view", slug, "--json", "description", "-q", ".description").Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}

// FetchAllDescriptions fetches all the authenticated user's repo descriptions
// in a single gh call. Returns a map from repo name → description.
func FetchAllDescriptions(limit int) map[string]string {
	if limit <= 0 {
		limit = 1000
	}
	out, err := exec.Command("gh", "repo", "list",
		"--limit", fmt.Sprintf("%d", limit),
		"--json", "name,description",
	).Output()
	if err != nil {
		return nil
	}

	var repos []struct {
		Name        string `json:"name"`
		Description string `json:"description"`
	}
	if err := json.Unmarshal(out, &repos); err != nil {
		return nil
	}

	m := make(map[string]string, len(repos))
	for _, r := range repos {
		if r.Description != "" {
			m[r.Name] = r.Description
		}
	}
	return m
}

// PR holds fields from `gh pr list --json`.
type PR struct {
	Number         int    `json:"number"`
	Title          string `json:"title"`
	State          string `json:"state"`
	IsDraft        bool   `json:"isDraft"`
	URL            string `json:"url"`
	ReviewDecision string `json:"reviewDecision"`
	Author         struct {
		Login string `json:"login"`
	} `json:"author"`
	HeadRefName string `json:"headRefName"`
	BaseRefName string `json:"baseRefName"`
}

// RunPRs lists or opens a pull request for the current repo.
func RunPRs(repoPath string, limit int, state, draft string, needReview, requireChanges bool, openNumber int) int {
	remote := RemoteURL(repoPath)
	if remote == "" {
		ui.ErrorMsg("No 'origin' remote found")
		return 1
	}
	slug := GithubSlug(remote)
	if slug == "" {
		ui.ErrorMsg("Remote is not a GitHub URL")
		return 1
	}

	fields := "number,title,state,isDraft,url,author,createdAt,reviewDecision,headRefName,baseRefName"
	cmd := exec.Command("gh", "pr", "list",
		"--repo", slug,
		"--limit", fmt.Sprintf("%d", limit),
		"--state", state,
		"--json", fields,
	)

	fmt.Printf("%s Fetching PRs for %s...\n", ui.Icons.Git, ui.Bold(slug))

	out, err := cmd.Output()
	if err != nil {
		ui.ErrorMsg("gh pr list failed: " + err.Error())
		return 1
	}

	var prs []PR
	if err := json.Unmarshal(out, &prs); err != nil {
		ui.ErrorMsg("Failed to parse gh output: " + err.Error())
		return 1
	}

	// Apply filters
	var filtered []PR
	for _, pr := range prs {
		if draft == "only" && !pr.IsDraft {
			continue
		}
		if draft == "exclude" && pr.IsDraft {
			continue
		}
		if needReview && pr.ReviewDecision != "" && pr.ReviewDecision != "REVIEW_REQUIRED" {
			continue
		}
		if requireChanges && pr.ReviewDecision != "CHANGES_REQUESTED" {
			continue
		}
		filtered = append(filtered, pr)
	}

	// Open a specific PR in browser
	if openNumber > 0 {
		for _, pr := range filtered {
			if pr.Number == openNumber {
				fmt.Printf("%s Opening %s\n", ui.Icons.Arrow, ui.Inf(pr.URL))
				if err := exec.Command("open", pr.URL).Start(); err != nil {
					exec.Command("xdg-open", pr.URL).Start()
				}
				return 0
			}
		}
		ui.ErrorMsg(fmt.Sprintf("PR #%d not found", openNumber))
		return 1
	}

	if len(filtered) == 0 {
		ui.WarningMsg("No pull requests found")
		return 0
	}

	// Print table
	fmt.Printf("\n  %s Pull Requests — %s (%d)\n\n", ui.Icons.Git, ui.Bold(slug), len(filtered))
	fmt.Printf("  %-6s  %-50s  %-8s  %-5s  %s\n",
		ui.Bold("#"), ui.Bold("Title"), ui.Bold("State"), ui.Bold("Draft"), ui.Bold("Review"))
	fmt.Printf("  %s\n", strings.Repeat("─", 85))

	for _, pr := range filtered {
		draft := ""
		if pr.IsDraft {
			draft = "yes"
		}
		title := pr.Title
		if len(title) > 50 {
			title = title[:47] + "..."
		}
		stateStr := pr.State
		switch strings.ToLower(pr.State) {
		case "open":
			stateStr = ui.Success(pr.State)
		case "closed":
			stateStr = ui.Mute(pr.State)
		case "merged":
			stateStr = ui.Inf(pr.State)
		}
		fmt.Printf("  %-6d  %-50s  %-8s  %-5s  %s\n",
			pr.Number, title, stateStr, draft, pr.ReviewDecision)
	}
	fmt.Println()
	return 0
}

// RunCLI implements "iskra clone".
func RunCLI(args []string) int {
	if ui.HasHelpFlag(args) {
		printCloneHelp()
		return 0
	}
	flags := flag.NewFlagSet("clone", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	baseDir := flags.String("base-dir", "~/Neoware", "Base directory for cloned repos")
	limit := flags.Int("limit", 1000, "Max repos to fetch")
	filterForks := flags.Bool("filter-forks", false, "Skip forked repositories")
	onlyStars := flags.Int("only-stars", 0, "Only repos with at least N stars")
	exclude := flags.String("exclude", "", "Comma-separated name patterns to exclude")
	if err := flags.Parse(args); err != nil {
		printCloneHelp()
		return 1
	}

	var excludePatterns []string
	if *exclude != "" {
		excludePatterns = strings.Split(*exclude, ",")
	}

	return Run(CloneOptions{
		BaseDir:     config.ExpandPath(*baseDir),
		Limit:       *limit,
		FilterForks: *filterForks,
		OnlyStars:   *onlyStars,
		Exclude:     excludePatterns,
	})
}

func printCloneHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra clone") + " - Bulk clone GitHub repositories")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra clone [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -base-dir <path>   Where to clone repos (default: ~/Neoware)")
	fmt.Println("    -limit <n>         Max repos to fetch (default: 1000)")
	fmt.Println("    -filter-forks      Skip forked repositories")
	fmt.Println("    -only-stars <n>    Only repos with at least N stars")
	fmt.Println("    -exclude <list>    Comma-separated name patterns to exclude")
	fmt.Println()
}

// GHRepo holds fields from `gh repo list --json`.
type GHRepo struct {
	NameWithOwner  string `json:"nameWithOwner"`
	Name           string `json:"name"`
	Description    string `json:"description"`
	IsPrivate      bool   `json:"isPrivate"`
	IsFork         bool   `json:"isFork"`
	StargazerCount int    `json:"stargazerCount"`
	URL            string `json:"url"`
}

// CloneOptions configures the clone run.
type CloneOptions struct {
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
func FetchRepos(opts CloneOptions) ([]GHRepo, error) {
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
func Run(opts CloneOptions) int {
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
