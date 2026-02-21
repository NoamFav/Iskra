// Package gh implements iskra gh subcommands: info, open, prs.
// All GitHub API calls go through the gh CLI.
package gh

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"

	"github.com/NoamFav/iskra/internal/ui"
)

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
	if strings.HasPrefix(url, "git@github.com:") {
		return strings.TrimPrefix(url, "git@github.com:")
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
