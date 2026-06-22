// Package init implements the iskra init family of subcommands:
// init, list (ls), add (a), remove (rm).
package init

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"

	"github.com/NoamFav/iskra/internal/config"
	ghcmd "github.com/NoamFav/iskra/internal/gh"
	"github.com/NoamFav/iskra/internal/scanner"
	"github.com/NoamFav/iskra/internal/ui"
)

// tildeify replaces the home directory prefix with ~.
func tildeify(path string) string {
	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		return path
	}
	if strings.HasPrefix(path, home) {
		return "~" + path[len(home):]
	}
	return path
}

// RepoGitInfo gathers branch/remote/HEAD for a repo path.
func RepoGitInfo(repoPath string) (branch, remoteURL, head string) {
	run := func(args ...string) string {
		out, err := exec.Command("git", append([]string{"-C", repoPath}, args...)...).Output()
		if err != nil {
			return ""
		}
		return strings.TrimSpace(string(out))
	}
	branch = run("rev-parse", "--abbrev-ref", "HEAD")
	remoteURL = run("remote", "get-url", "origin")
	head = run("rev-parse", "HEAD")
	return
}

// RunInit runs the interactive init flow: scan base_dir and track all found repos.
func RunInit(cfgMgr *config.Manager, baseDir string, yes bool) int {
	base := config.ExpandPath(baseDir)
	if base == "" {
		base = config.ExpandPath(cfgMgr.GlobalConfig.BaseDir)
	}

	ui.Header()
	fmt.Printf("%s Scanning %s for git repositories...\n\n", ui.Icons.Folder, ui.Bold(tildeify(base)))

	cfg := cfgMgr.GlobalConfig
	results, err := scanner.FindGitRepos(scanner.Options{
		BaseDir:         base,
		MaxDepth:        cfg.MaxDepth,
		FollowSymlinks:  cfg.FollowSymlinks,
		OnlyPatterns:    cfg.OnlyPatterns,
		ExcludePatterns: cfg.ExcludePatterns,
	})
	if err != nil {
		ui.ErrorMsg("Scan failed: " + err.Error())
		return 1
	}

	if len(results) == 0 {
		ui.WarningMsg("No git repositories found in " + tildeify(base))
		return 0
	}

	fmt.Printf("%s Found %s repositories\n\n", ui.Icons.Success, ui.Bold(fmt.Sprintf("%d", len(results))))

	// Preview first 5
	for i, r := range results {
		if i >= 5 {
			fmt.Printf("  ... and %d more\n", len(results)-5)
			break
		}
		rel, _ := filepath.Rel(base, r.Path)
		fmt.Printf("  %s %s\n", ui.Icons.Git, rel)
	}
	fmt.Println()

	if !yes {
		fmt.Printf("Track these %d repositories? [Y/n]: ", len(results))
		var resp string
		fmt.Scanln(&resp)
		resp = strings.ToLower(strings.TrimSpace(resp))
		if resp == "n" || resp == "no" {
			ui.WarningMsg("Cancelled")
			return 0
		}
	}

	// Fetch all GitHub descriptions in one call
	descriptions := ghcmd.FetchAllDescriptions(0)

	added := 0
	for _, r := range results {
		branch, remoteURL, head := RepoGitInfo(r.Path)
		name := filepath.Base(r.Path)
		info := &config.RepoInfo{
			Path:          r.Path,
			Name:          name,
			RemoteURL:     remoteURL,
			DefaultBranch: branch,
			LastCommit:    head,
			Description:   descriptions[name],
			Active:        true,
		}
		if cfgMgr.AddRepo(info) {
			added++
		}
	}

	if err := cfgMgr.SaveRepos(); err != nil {
		ui.ErrorMsg("Failed to save repos: " + err.Error())
		return 1
	}

	fmt.Printf("\n%s Tracked %s repositories\n", ui.Icons.Success, ui.Bold(fmt.Sprintf("%d", added)))
	fmt.Printf("%s Config: %s\n", ui.Inf(ui.Icons.Info), tildeify(cfgMgr.ConfigDir))
	return 0
}

// RunVerify checks all tracked repos for missing or stale info and fixes it in-place.
func RunVerify(cfgMgr *config.Manager) int {
	repos := cfgMgr.GetAllRepos()
	if len(repos) == 0 {
		ui.WarningMsg("No tracked repositories. Run 'iskra init' to scan.")
		return 0
	}

	fmt.Printf("%s Verifying %d tracked repositories...\n\n", ui.Icons.Info, len(repos))

	// Fetch all GitHub descriptions in one call
	descriptions := ghcmd.FetchAllDescriptions(0)

	var updated, removed int

	for _, repo := range repos {
		// Check if the repo still exists on disk
		if _, err := os.Stat(repo.Path); os.IsNotExist(err) {
			fmt.Printf("  %s %s %s\n", ui.DotError, ui.Bold(repo.Name), ui.Err("path not found — removing"))
			cfgMgr.RemoveRepo(repo.Path)
			removed++
			continue
		}

		branch, remoteURL, head := RepoGitInfo(repo.Path)
		changed := false

		if branch != "" && branch != repo.DefaultBranch {
			repo.DefaultBranch = branch
			changed = true
		}

		if remoteURL != "" && remoteURL != repo.RemoteURL {
			repo.RemoteURL = remoteURL
			changed = true
		}

		if head != "" && head != repo.LastCommit {
			repo.LastCommit = head
			changed = true
		}

		if repo.Description == "" {
			if desc := descriptions[repo.Name]; desc != "" {
				repo.Description = desc
				changed = true
			}
		}

		if changed {
			cfgMgr.AddRepo(repo)
			updated++
			fmt.Printf("  %s %s %s\n", ui.DotWarning, ui.Bold(repo.Name), ui.Mute("updated"))
		} else {
			fmt.Printf("  %s %s\n", ui.DotSuccess, repo.Name)
		}
	}

	if err := cfgMgr.SaveRepos(); err != nil {
		ui.ErrorMsg("Failed to save: " + err.Error())
		return 1
	}

	fmt.Println()
	if updated == 0 && removed == 0 {
		ui.SuccessMsg("All repos up to date")
	} else {
		if updated > 0 {
			fmt.Printf("%s Updated %d repo(s)\n", ui.Icons.Success, updated)
		}
		if removed > 0 {
			fmt.Printf("%s Removed %d missing repo(s)\n", ui.Icons.Warning, removed)
		}
	}
	return 0
}

// RunList prints all tracked repositories in a table.
func RunList(cfgMgr *config.Manager, all bool) int {
	var repos []*config.RepoInfo
	if all {
		repos = cfgMgr.GetAllRepos()
	} else {
		repos = cfgMgr.GetActiveRepos()
	}

	if len(repos) == 0 {
		ui.WarningMsg("No tracked repositories. Run 'iskra init' to scan.")
		return 0
	}

	// Sort by name
	sort.Slice(repos, func(i, j int) bool {
		return repos[i].Name < repos[j].Name
	})

	// Column widths
	maxName := 4
	maxPath := 4
	maxBranch := 6
	for _, r := range repos {
		if len(r.Name) > maxName {
			maxName = len(r.Name)
		}
		if len(tildeify(r.Path)) > maxPath {
			maxPath = len(tildeify(r.Path))
		}
		if len(r.DefaultBranch) > maxBranch {
			maxBranch = len(r.DefaultBranch)
		}
	}
	// Cap path display width
	if maxPath > 50 {
		maxPath = 50
	}

	// Header
	fmt.Printf("\n  %-*s  %-*s  %-*s  %s\n",
		maxName, ui.Bold("Name"),
		maxPath, ui.Bold("Path"),
		maxBranch, ui.Bold("Branch"),
		ui.Bold("Status"),
	)
	fmt.Printf("  %s\n", strings.Repeat("─", maxName+maxPath+maxBranch+20))

	for _, r := range repos {
		path := tildeify(r.Path)
		if len(path) > maxPath {
			path = "…" + path[len(path)-maxPath+1:]
		}
		status := ui.Success("active")
		if !r.Active {
			status = ui.Err("inactive")
		}
		fmt.Printf("  %-*s  %-*s  %-*s  %s\n",
			maxName, r.Name,
			maxPath, path,
			maxBranch, r.DefaultBranch,
			status,
		)
	}
	fmt.Printf("\n  %d repositories\n\n", len(repos))
	return 0
}

// RunAdd adds a single repository to tracking.
func RunAdd(cfgMgr *config.Manager, path string) int {
	// Resolve git root
	out, err := exec.Command("git", "-C", path, "rev-parse", "--show-toplevel").Output()
	if err != nil {
		ui.ErrorMsg(fmt.Sprintf("Not a git repository: %s", path))
		return 1
	}
	repoPath := strings.TrimSpace(string(out))

	branch, remoteURL, head := RepoGitInfo(repoPath)
	info := &config.RepoInfo{
		Path:          repoPath,
		Name:          filepath.Base(repoPath),
		RemoteURL:     remoteURL,
		DefaultBranch: branch,
		LastCommit:    head,
		Description:   ghcmd.RepoDescription(remoteURL),
		Active:        true,
	}

	added := cfgMgr.AddRepo(info)
	if err := cfgMgr.SaveRepos(); err != nil {
		ui.ErrorMsg("Failed to save: " + err.Error())
		return 1
	}

	if added {
		fmt.Printf("%s Added %s\n", ui.Icons.Success, ui.Bold(info.Name))
	} else {
		ui.WarningMsg(info.Name + " is already tracked (updated)")
	}
	return 0
}

// RunRemove removes a repository from tracking.
func RunRemove(cfgMgr *config.Manager, path string) int {
	// Resolve git root
	out, err := exec.Command("git", "-C", path, "rev-parse", "--show-toplevel").Output()
	if err != nil {
		ui.ErrorMsg(fmt.Sprintf("Not a git repository: %s", path))
		return 1
	}
	repoPath := strings.TrimSpace(string(out))

	removed := cfgMgr.RemoveRepo(repoPath)
	if !removed {
		ui.WarningMsg(filepath.Base(repoPath) + " is not tracked")
		return 0
	}

	if err := cfgMgr.SaveRepos(); err != nil {
		ui.ErrorMsg("Failed to save: " + err.Error())
		return 1
	}

	fmt.Printf("%s Removed %s\n", ui.Icons.Success, ui.Bold(filepath.Base(repoPath)))
	return 0
}
