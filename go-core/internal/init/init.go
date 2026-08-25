// Package init implements the iskra init family of subcommands:
// init, list (ls), add (a), remove (rm).
package init

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"

	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/remote"
	"github.com/NoamFav/iskra/internal/scanner"
	"github.com/NoamFav/iskra/internal/ui"
)

// Dispatch routes "iskra init/list/ls/add/remove/rm/verify" to the right
// handler, parsing each subcommand's own flags first.
func Dispatch(cfgMgr *config.Manager, cmd string, args []string, jsonOutput bool) int {
	if ui.HasHelpFlag(args) {
		printInitHelp()
		return 0
	}
	switch cmd {
	case "verify":
		return RunVerify(cfgMgr)

	case "list", "ls":
		fs := flag.NewFlagSet("list", flag.ContinueOnError)
		fs.SetOutput(io.Discard)
		all := fs.Bool("all", false, "Include inactive repos")
		if err := fs.Parse(args); err != nil {
			printInitHelp()
			return 1
		}
		if jsonOutput {
			repos := cfgMgr.GetAllRepos()
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			enc.Encode(repos)
			return 0
		}
		return RunList(cfgMgr, *all)

	case "add", "a":
		fs := flag.NewFlagSet("add", flag.ContinueOnError)
		fs.SetOutput(io.Discard)
		if err := fs.Parse(args); err != nil {
			printInitHelp()
			return 1
		}
		path := "."
		if len(fs.Args()) > 0 {
			path = fs.Args()[0]
		}
		return RunAdd(cfgMgr, path)

	case "remove", "rm":
		fs := flag.NewFlagSet("remove", flag.ContinueOnError)
		fs.SetOutput(io.Discard)
		if err := fs.Parse(args); err != nil {
			printInitHelp()
			return 1
		}
		path := "."
		if len(fs.Args()) > 0 {
			path = fs.Args()[0]
		}
		return RunRemove(cfgMgr, path)

	default: // "init"
		fs := flag.NewFlagSet("init", flag.ContinueOnError)
		fs.SetOutput(io.Discard)
		baseDir := fs.String("base-dir", "", "Base directory to scan")
		yes := fs.Bool("y", false, "Accept all defaults")
		fs.BoolVar(yes, "yes", false, "Accept all defaults")
		if err := fs.Parse(args); err != nil {
			printInitHelp()
			return 1
		}
		if jsonOutput {
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			enc.Encode(map[string]interface{}{
				"config_dir":    cfgMgr.ConfigDir,
				"tracked_repos": cfgMgr.TrackedRepos,
				"global_config": cfgMgr.GlobalConfig,
			})
			return 0
		}
		return RunInit(cfgMgr, *baseDir, *yes)
	}
}

func printInitHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra init") + " - Scan and track repositories")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra init [flags]")
	fmt.Println("    iskra verify")
	fmt.Println("    iskra list, ls [-all]")
	fmt.Println("    iskra add [path]")
	fmt.Println("    iskra remove, rm [path]")
	fmt.Println()
	fmt.Println(ui.Bold("INIT FLAGS:"))
	fmt.Println("    -base-dir <path>   Directory to scan for repos")
	fmt.Println("    -y, -yes           Accept all defaults")
	fmt.Println()
	fmt.Println(ui.Bold("VERIFY:"))
	fmt.Println("    Checks all tracked repos for missing or stale info")
	fmt.Println("    (branch, remote, description) and fixes it in-place.")
	fmt.Println("    Removes repos whose paths no longer exist.")
	fmt.Println()
	fmt.Println(ui.Bold("LIST FLAGS:"))
	fmt.Println("    -all   Include inactive repos")
	fmt.Println()
}

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

// resolveTrackPath: git root if path is inside a repo, otherwise just the
// absolute path, a plain directory can still be tracked via .iskra
func resolveTrackPath(path string) (string, error) {
	if out, err := exec.Command("git", "-C", path, "rev-parse", "--show-toplevel").Output(); err == nil {
		return strings.TrimSpace(string(out)), nil
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		return "", fmt.Errorf("cannot resolve path: %s", path)
	}
	if fi, err := os.Stat(abs); err != nil || !fi.IsDir() {
		return "", fmt.Errorf("not a directory: %s", path)
	}
	return abs, nil
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
	results, err := scanner.FindRepos(scanner.Options{
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
	descriptions := remote.FetchAllDescriptions(0)

	added := 0
	skipped := 0
	for _, r := range results {
		id, err := cfgMgr.EnsureMarker(r.Path)
		if err != nil {
			fmt.Printf("  %s %s: malformed .iskra marker, skipping (%s)\n", ui.DotWarning, tildeify(r.Path), err.Error())
			skipped++
			continue
		}
		branch, remoteURL, head := RepoGitInfo(r.Path)
		name := filepath.Base(r.Path)
		info := &config.RepoInfo{
			Path:          r.Path,
			Name:          name,
			ID:            id,
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

	if skipped > 0 {
		fmt.Printf("%s Skipped %s repositories with malformed markers\n", ui.Icons.Warning, ui.Bold(fmt.Sprintf("%d", skipped)))
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
	descriptions := remote.FetchAllDescriptions(0)

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

		if repo.ID == "" {
			if id, err := cfgMgr.EnsureMarker(repo.Path); err == nil {
				repo.ID = id
				changed = true
			}
		}

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

// RunAdd tracks a repo. doesn't actually have to be a repo, a plain
// directory works too, it just gets tracked via .iskra instead of git
func RunAdd(cfgMgr *config.Manager, path string) int {
	repoPath, err := resolveTrackPath(path)
	if err != nil {
		ui.ErrorMsg(err.Error())
		return 1
	}

	id, err := cfgMgr.EnsureMarker(repoPath)
	if err != nil {
		ui.ErrorMsg("Failed to create/read .iskra marker: " + err.Error())
		return 1
	}

	branch, remoteURL, head := RepoGitInfo(repoPath)
	info := &config.RepoInfo{
		Path:          repoPath,
		Name:          filepath.Base(repoPath),
		ID:            id,
		RemoteURL:     remoteURL,
		DefaultBranch: branch,
		LastCommit:    head,
		Description:   remote.RepoDescription(remoteURL),
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

// RunRemove untracks a repo but leaves .iskra alone, this only touches
// the central index, so re-adding the same directory later picks the
// same identity back up
func RunRemove(cfgMgr *config.Manager, path string) int {
	repoPath, err := resolveTrackPath(path)
	if err != nil {
		ui.ErrorMsg(err.Error())
		return 1
	}

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
