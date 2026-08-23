package batch

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"

	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/processor"
	"github.com/NoamFav/iskra/internal/scanner"
	"github.com/NoamFav/iskra/internal/ui"
)

// RunStatus implements "iskra status".
func RunStatus(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if ui.HasHelpFlag(args) {
		printStatusHelp()
		return 0
	}
	fs := flag.NewFlagSet("status", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var only, exclude string
	fs.StringVar(&only, "only", "", "Only pattern")
	fs.StringVar(&exclude, "exclude", "", "Exclude pattern")
	if err := fs.Parse(args); err != nil {
		printStatusHelp()
		return 1
	}

	repos := scanner.SelectRepos(cfgMgr, "", only, exclude)

	proc := processor.NewProcessor(cfgMgr)
	opts := processor.Options{StatusOnly: true}

	if jsonOutput {
		result := proc.ProcessBatch(repos, opts)
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		return 0
	}

	if !quiet {
		ui.CompactHeader()
	}

	showDesc := cfgMgr.GlobalConfig.ShowDescriptions

	// Build a lookup from path → RepoInfo for descriptions
	repoInfoMap := make(map[string]*config.RepoInfo)
	for _, r := range cfgMgr.GetAllRepos() {
		repoInfoMap[r.Path] = r
	}

	// Sort repos by parent directory, then by name within each group
	sort.Slice(repos, func(i, j int) bool {
		pi := filepath.Dir(repos[i])
		pj := filepath.Dir(repos[j])
		if pi != pj {
			return pi < pj
		}
		return filepath.Base(repos[i]) < filepath.Base(repos[j])
	})

	currentGroup := ""

	for _, repoPath := range repos {
		parentDir := filepath.Base(filepath.Dir(repoPath))
		if parentDir != currentGroup {
			currentGroup = parentDir
			fmt.Printf("\n%s %s\n", ui.Icons.Folder, ui.Bold(currentGroup))
		}

		result := proc.ProcessRepo(repoPath, opts)
		info := repoInfoMap[repoPath]

		dot := ui.DotSuccess
		if result.Status != "success" {
			dot = ui.DotError
		} else if result.Changes != nil && result.Changes.Total > 0 {
			dot = ui.DotWarning
		}

		fmt.Printf("  %s %s", dot, ui.Bold(result.Name))
		fmt.Printf(" [%s]", ui.Mute(result.Branch))

		if result.Changes != nil && result.Changes.Total > 0 {
			fmt.Printf(" %s", ui.Warn(fmt.Sprintf("%d changes", result.Changes.Total)))
		}

		if result.IsProtected {
			fmt.Printf(" %s", ui.Warn("protected"))
		}

		if showDesc && info != nil && info.Description != "" {
			desc := info.Description
			if len(desc) > 50 {
				desc = desc[:47] + "..."
			}
			fmt.Printf(" %s", ui.Mute("— "+desc))
		}

		fmt.Println()
	}

	fmt.Println()
	return 0
}

func printStatusHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra status") + " - Show status of all tracked repos")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra status [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -only <pattern>    Only include repos matching pattern")
	fmt.Println("    -exclude <pattern> Exclude repos matching pattern")
	fmt.Println()
	fmt.Println(ui.Mute("  Repos are grouped by parent directory."))
	fmt.Println(ui.Mute("  Descriptions from GitHub shown when 'show_descriptions: true' in config."))
	fmt.Println()
}
