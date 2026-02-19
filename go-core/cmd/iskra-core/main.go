// iskra-core is the Go backend for Iskra.
// It handles git operations, AI commit messages, and repo processing.
// Outputs JSON for the Python frontend to render.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/processor"
	"github.com/NoamFav/iskra/internal/scanner"
)

// Command represents a subcommand
type Command struct {
	Name        string
	Description string
	Run         func(args []string) error
}

var commands = map[string]*Command{
	"process": {
		Name:        "process",
		Description: "Process repositories (commit/status/pull)",
		Run:         runProcess,
	},
	"scan": {
		Name:        "scan",
		Description: "Scan for git repositories",
		Run:         runScan,
	},
	"status": {
		Name:        "status",
		Description: "Get status of a repository",
		Run:         runStatus,
	},
	"config": {
		Name:        "config",
		Description: "Get current configuration",
		Run:         runConfig,
	},
}

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	cmdName := os.Args[1]
	cmd, ok := commands[cmdName]
	if !ok {
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", cmdName)
		printUsage()
		os.Exit(1)
	}

	if err := cmd.Run(os.Args[2:]); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("iskra-core - Iskra Go backend")
	fmt.Println()
	fmt.Println("Usage: iskra-core <command> [options]")
	fmt.Println()
	fmt.Println("Commands:")
	for _, cmd := range commands {
		fmt.Printf("  %-12s %s\n", cmd.Name, cmd.Description)
	}
}

func runProcess(args []string) error {
	fs := flag.NewFlagSet("process", flag.ExitOnError)

	// Repository selection
	var repos string
	var pulse bool
	var scanDir string

	fs.StringVar(&repos, "repos", "", "Comma-separated list of repo paths")
	fs.BoolVar(&pulse, "pulse", false, "Process current directory only")
	fs.StringVar(&scanDir, "scan", "", "Scan directory for repos")

	// Processing options
	var statusOnly, pullOnly, pull, noPush, noAICommit, dryRun, showDiff, compact bool
	var commitMessage string

	fs.BoolVar(&statusOnly, "status-only", false, "Only show status")
	fs.BoolVar(&pullOnly, "pull-only", false, "Only pull")
	fs.BoolVar(&pull, "pull", false, "Pull before commit")
	fs.BoolVar(&noPush, "no-push", false, "Don't push after commit")
	fs.BoolVar(&noAICommit, "no-ai-commit", false, "Don't use AI commit")
	fs.StringVar(&commitMessage, "message", "", "Custom commit message")
	fs.BoolVar(&dryRun, "dry-run", false, "Dry run mode")
	fs.BoolVar(&showDiff, "show-diff", false, "Show diff")
	fs.BoolVar(&compact, "compact", false, "Compact output")

	// Config
	var configDir string
	fs.StringVar(&configDir, "config-dir", "", "Config directory")

	fs.Parse(args)

	// Load config
	cfgMgr, err := config.NewManager(configDir)
	if err != nil {
		return err
	}

	// Determine repos to process
	var repoPaths []string

	if pulse {
		// Current directory
		repo, err := scanner.GetCurrentRepo()
		if err != nil || repo == nil {
			return fmt.Errorf("not in a git repository")
		}
		repoPaths = []string{repo.Path}
	} else if repos != "" {
		// Explicit list
		repoPaths = strings.Split(repos, ",")
	} else if scanDir != "" {
		// Scan directory
		found, err := scanner.FindGitRepos(scanner.Options{
			BaseDir:         scanDir,
			MaxDepth:        cfgMgr.GlobalConfig.MaxDepth,
			FollowSymlinks:  cfgMgr.GlobalConfig.FollowSymlinks,
			OnlyPatterns:    cfgMgr.GlobalConfig.OnlyPatterns,
			ExcludePatterns: cfgMgr.GlobalConfig.ExcludePatterns,
		})
		if err != nil {
			return err
		}
		for _, r := range found {
			repoPaths = append(repoPaths, r.Path)
		}
	} else {
		// Use tracked repos
		for _, repo := range cfgMgr.GetActiveRepos() {
			repoPaths = append(repoPaths, repo.Path)
		}
	}

	if len(repoPaths) == 0 {
		return fmt.Errorf("no repositories found")
	}

	// Create processor
	proc := processor.NewProcessor(cfgMgr)

	// Process
	opts := processor.Options{
		StatusOnly:    statusOnly,
		PullOnly:      pullOnly,
		Pull:          pull,
		NoPush:        noPush,
		NoAICommit:    noAICommit,
		CommitMessage: commitMessage,
		DryRun:        dryRun,
		ShowDiff:      showDiff,
		Compact:       compact,
	}

	result := proc.ProcessBatch(repoPaths, opts)

	// Output JSON
	return outputJSON(result)
}

func runScan(args []string) error {
	fs := flag.NewFlagSet("scan", flag.ExitOnError)

	var baseDir string
	var maxDepth int
	var followSymlinks bool
	var only, exclude string

	fs.StringVar(&baseDir, "dir", "", "Base directory to scan")
	fs.IntVar(&maxDepth, "depth", 3, "Max depth")
	fs.BoolVar(&followSymlinks, "follow-symlinks", true, "Follow symlinks")
	fs.StringVar(&only, "only", "", "Only include patterns (comma-separated)")
	fs.StringVar(&exclude, "exclude", "", "Exclude patterns (comma-separated)")

	fs.Parse(args)

	if baseDir == "" {
		// Load config for default base dir
		cfgMgr, err := config.NewManager("")
		if err == nil {
			baseDir = config.ExpandPath(cfgMgr.GlobalConfig.BaseDir)
		}
	}

	if baseDir == "" {
		cwd, _ := os.Getwd()
		baseDir = cwd
	}

	var onlyPatterns, excludePatterns []string
	if only != "" {
		onlyPatterns = strings.Split(only, ",")
	}
	if exclude != "" {
		excludePatterns = strings.Split(exclude, ",")
	}

	repos, err := scanner.FindGitRepos(scanner.Options{
		BaseDir:         baseDir,
		MaxDepth:        maxDepth,
		FollowSymlinks:  followSymlinks,
		OnlyPatterns:    onlyPatterns,
		ExcludePatterns: excludePatterns,
	})
	if err != nil {
		return err
	}

	return outputJSON(map[string]interface{}{
		"success":   true,
		"base_dir":  baseDir,
		"count":     len(repos),
		"repos":     repos,
	})
}

func runStatus(args []string) error {
	fs := flag.NewFlagSet("status", flag.ExitOnError)

	var repoPath string
	fs.StringVar(&repoPath, "repo", "", "Repository path (default: current dir)")

	fs.Parse(args)

	if repoPath == "" {
		repo, err := scanner.GetCurrentRepo()
		if err != nil || repo == nil {
			return fmt.Errorf("not in a git repository")
		}
		repoPath = repo.Path
	}

	cfgMgr, err := config.NewManager("")
	if err != nil {
		return err
	}

	proc := processor.NewProcessor(cfgMgr)
	result := proc.ProcessRepo(repoPath, processor.Options{StatusOnly: true})

	return outputJSON(result)
}

func runConfig(args []string) error {
	fs := flag.NewFlagSet("config", flag.ExitOnError)

	var configDir string
	fs.StringVar(&configDir, "config-dir", "", "Config directory")

	fs.Parse(args)

	cfgMgr, err := config.NewManager(configDir)
	if err != nil {
		return err
	}

	return outputJSON(map[string]interface{}{
		"config_dir":    cfgMgr.ConfigDir,
		"global_config": cfgMgr.GlobalConfig,
		"ui_config":     cfgMgr.UIConfig,
		"tracked_repos": cfgMgr.TrackedRepos,
	})
}

func outputJSON(v interface{}) error {
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(v)
}
