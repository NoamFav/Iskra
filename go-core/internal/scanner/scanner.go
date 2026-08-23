// Package scanner handles finding git repositories in directories.
package scanner

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/remote"
	"github.com/NoamFav/iskra/internal/ui"
)

// HeavyDirs are directories that should never be scanned
var HeavyDirs = map[string]bool{
	"node_modules":  true,
	"dist":          true,
	"build":         true,
	"target":        true,
	"__pycache__":   true,
	".tox":          true,
	".nox":          true,
	"venv":          true,
	".venv":         true,
	"env":           true,
	".env":          true,
	".git":          true,
	".svn":          true,
	".hg":           true,
	"vendor":        true,
	"Pods":          true,
	".gradle":       true,
	".idea":         true,
	".vs":           true,
	"bin":           true,
	"obj":           true,
	"out":           true,
	".next":         true,
	".nuxt":         true,
	".cache":        true,
	"coverage":      true,
	".pytest_cache": true,
	".mypy_cache":   true,
	"__snapshots__": true,
	".terraform":    true,
	".serverless":   true,
	".aws-sam":      true,
	"cdk.out":       true,
	".docusaurus":   true,
	".turbo":        true,
	".nx":           true,
	"android":       true,
	".android":      true,
	"ios":           true,
	"windows":       true,
	"linux":         true,
	"macos":         true,
	".dart_tool":    true,
	".pub-cache":    true,
	"DerivedData":   true,
}

// Options for scanning
type Options struct {
	BaseDir         string
	MaxDepth        int
	FollowSymlinks  bool
	OnlyPatterns    []string
	ExcludePatterns []string
}

// Result represents a found repository
type Result struct {
	Path        string `json:"path"`
	Name        string `json:"name"`
	DisplayName string `json:"display_name"`
}

// matchAny checks if path matches any glob pattern
// MatchesPatterns returns true if name passes only/exclude pattern filters.
// Empty onlyPatterns means "match all". A name matching any excludePattern is excluded.
func MatchesPatterns(name string, onlyPatterns, excludePatterns []string) bool {
	if len(onlyPatterns) > 0 && !matchAny(name, onlyPatterns) {
		return false
	}
	if len(excludePatterns) > 0 && matchAny(name, excludePatterns) {
		return false
	}
	return true
}

func matchAny(path string, patterns []string) bool {
	for _, pattern := range patterns {
		matched, err := filepath.Match(pattern, path)
		if err == nil && matched {
			return true
		}
		// Also try matching against just the base name
		matched, err = filepath.Match(pattern, filepath.Base(path))
		if err == nil && matched {
			return true
		}
	}
	return false
}

// FindGitRepos finds all git repositories in the base directory
func FindGitRepos(opts Options) ([]Result, error) {
	baseDir := opts.BaseDir
	if baseDir == "" {
		var err error
		baseDir, err = os.Getwd()
		if err != nil {
			return nil, err
		}
	}

	// Expand ~
	if strings.HasPrefix(baseDir, "~") {
		home, err := os.UserHomeDir()
		if err != nil {
			return nil, err
		}
		baseDir = filepath.Join(home, baseDir[1:])
	}

	// Ensure absolute path
	baseDir, err := filepath.Abs(baseDir)
	if err != nil {
		return nil, err
	}

	if opts.MaxDepth == 0 {
		opts.MaxDepth = 3
	}

	var repos []Result

	err = walkDir(baseDir, baseDir, 0, opts, &repos)
	if err != nil {
		return nil, err
	}

	return repos, nil
}

func walkDir(current, base string, depth int, opts Options, repos *[]Result) error {
	if depth > opts.MaxDepth {
		return nil
	}

	entries, err := os.ReadDir(current)
	if err != nil {
		return nil // Skip dirs we can't read
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		name := entry.Name()

		// Skip hidden dirs (except we're looking for .git)
		if strings.HasPrefix(name, ".") {
			continue
		}

		// Skip heavy dirs
		if HeavyDirs[name] {
			continue
		}

		fullPath := filepath.Join(current, name)

		// Handle symlinks
		if entry.Type()&os.ModeSymlink != 0 {
			if !opts.FollowSymlinks {
				continue
			}
			// Resolve symlink
			resolved, err := filepath.EvalSymlinks(fullPath)
			if err != nil {
				continue
			}
			fullPath = resolved
		}

		// Check if this is a git repo
		if remote.IsGitRepo(fullPath) {
			// Apply filters
			relPath, _ := filepath.Rel(base, fullPath)
			displayName := relPath
			if displayName == "" {
				displayName = name
			}

			// Check only patterns
			if len(opts.OnlyPatterns) > 0 && !matchAny(name, opts.OnlyPatterns) {
				continue
			}

			// Check exclude patterns
			if len(opts.ExcludePatterns) > 0 && matchAny(name, opts.ExcludePatterns) {
				continue
			}

			*repos = append(*repos, Result{
				Path:        fullPath,
				Name:        name,
				DisplayName: displayName,
			})
			continue // Don't recurse into git repos
		}

		// Recurse
		walkDir(fullPath, base, depth+1, opts, repos)
	}

	return nil
}

// FindRepoInSubdirs looks for a specific repo by name
func FindRepoInSubdirs(baseDir, repoName string) string {
	repos, err := FindGitRepos(Options{
		BaseDir:  baseDir,
		MaxDepth: 5,
	})
	if err != nil {
		return ""
	}

	// Exact match first
	for _, r := range repos {
		if r.Name == repoName {
			return r.Path
		}
	}

	// Case-insensitive match
	lowerName := strings.ToLower(repoName)
	for _, r := range repos {
		if strings.ToLower(r.Name) == lowerName {
			return r.Path
		}
	}

	return ""
}

// GetCurrentRepo returns the git repo for the current directory
func GetCurrentRepo() (*Result, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return nil, err
	}

	// Walk up to find .git
	dir := cwd
	for {
		if remote.IsGitRepo(dir) {
			return &Result{
				Path:        dir,
				Name:        filepath.Base(dir),
				DisplayName: filepath.Base(dir),
			}, nil
		}

		parent := filepath.Dir(dir)
		if parent == dir {
			return nil, nil // Not in a git repo
		}
		dir = parent
	}
}

func CheckRepos(repos []string, cfgMgr *config.Manager) {
	for i, repoPath := range repos {
		if remote.IsGitRepo(repoPath) {
			fmt.Printf("%s %s exists and is a valid git repo\n", ui.DotSuccess, repoPath)
		} else {
			fmt.Printf("%s %s is missing or no longer a git repo\n", ui.DotError, repoPath)
			if confirm("Do you want to remove it from tracking?") {
				if cfgMgr.RemoveRepo(repoPath) {
					cfgMgr.SaveRepos()
				}
			}
		}

		if i < len(repos)-1 {
			time.Sleep(150 * time.Millisecond)
		}
	}
}

func confirm(prompt string) bool {
	sc := bufio.NewScanner(os.Stdin)
	for {
		fmt.Printf("%s [y/N]: ", prompt)
		if !sc.Scan() {
			return false
		}
		if sc.Err() != nil {
			return false
		}
		switch strings.ToLower(strings.TrimSpace(sc.Text())) {
		case "y", "yes":
			return true
		case "n", "no", "":
			return false
		default:
			fmt.Println("Please answer y or n.")
		}
	}
}

// SelectRepos resolves the set of repo paths a command should operate on:
// either a fresh scan of scanDir, or the tracked+active repos, filtered by
// only/exclude name patterns.
func SelectRepos(cfgMgr *config.Manager, scanDir, only, exclude string) []string {
	var repos []string

	var onlyPatterns, excludePatterns []string
	if only != "" {
		onlyPatterns = strings.Split(only, ",")
	}
	if exclude != "" {
		excludePatterns = strings.Split(exclude, ",")
	}

	if scanDir != "" {
		found, _ := FindGitRepos(Options{
			BaseDir:         scanDir,
			MaxDepth:        cfgMgr.GlobalConfig.MaxDepth,
			OnlyPatterns:    onlyPatterns,
			ExcludePatterns: excludePatterns,
		})
		for _, r := range found {
			repos = append(repos, r.Path)
		}
	} else {
		for _, repo := range cfgMgr.GetActiveRepos() {
			if !MatchesPatterns(repo.Name, onlyPatterns, excludePatterns) {
				continue
			}
			repos = append(repos, repo.Path)
		}
	}

	return repos
}

// RunScan implements "iskra scan": scan a directory for git repos.
func RunScan(cfgMgr *config.Manager, args []string, jsonOutput bool) int {
	if ui.HasHelpFlag(args) {
		printScanHelp()
		return 0
	}
	fs := flag.NewFlagSet("scan", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var baseDir string
	var maxDepth int
	fs.StringVar(&baseDir, "dir", "", "Base directory")
	fs.IntVar(&maxDepth, "depth", 3, "Max depth")
	if err := fs.Parse(args); err != nil {
		printScanHelp()
		return 1
	}

	if baseDir == "" {
		baseDir = config.ExpandPath(cfgMgr.GlobalConfig.BaseDir)
	}

	repos, err := FindGitRepos(Options{
		BaseDir:  baseDir,
		MaxDepth: maxDepth,
	})
	if err != nil {
		ui.ErrorMsg(err.Error())
		return 1
	}

	if jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(map[string]interface{}{
			"base_dir": baseDir,
			"count":    len(repos),
			"repos":    repos,
		})
		return 0
	}

	fmt.Printf("%s Found %d repositories in %s\n\n", ui.Icons.Folder, len(repos), ui.Mute(baseDir))
	for _, repo := range repos {
		fmt.Printf("  %s %s\n", ui.Icons.Git, repo.DisplayName)
	}

	return 0
}

func printScanHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra scan") + " - Scan directory for git repositories")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra scan [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -dir <path>   Directory to scan (default: configured base dir)")
	fmt.Println("    -depth <n>    Max depth to search (default: 3)")
	fmt.Println()
}

// RunCheck implements "iskra check": verify tracked repos still exist,
// offering to untrack any that are missing.
func RunCheck(cfgMgr *config.Manager, args []string) int {
	if ui.HasHelpFlag(args) {
		printCheckHelp()
		return 0
	}
	fs := flag.NewFlagSet("check", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var only, exclude string
	fs.StringVar(&only, "only", "", "Only pattern")
	fs.StringVar(&exclude, "exclude", "", "Exclude pattern")
	if err := fs.Parse(args); err != nil {
		printCheckHelp()
		return 1
	}

	repos := SelectRepos(cfgMgr, "", only, exclude)
	CheckRepos(repos, cfgMgr)
	return 0
}

func printCheckHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra check") + " - Check tracked repos still exist, offer to untrack missing ones")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra check [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -only <pattern>    Only include repos matching pattern")
	fmt.Println("    -exclude <pattern> Exclude repos matching pattern")
	fmt.Println()
}
