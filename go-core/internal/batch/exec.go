package batch

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/exec"
	"github.com/NoamFav/iskra/internal/scanner"
	"github.com/NoamFav/iskra/internal/ui"
)

// RunExec implements "iskra exec": run a shell command across repos.
func RunExec(cfgMgr *config.Manager, args []string, jsonOutput, quiet bool) int {
	if ui.HasHelpFlag(args) {
		printExecHelp()
		return 0
	}
	fs := flag.NewFlagSet("exec", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var parallel int
	var failFast bool
	var only, exclude string
	fs.IntVar(&parallel, "p", 1, "Parallel workers")
	fs.BoolVar(&failFast, "fail-fast", false, "Stop on first error")
	fs.StringVar(&only, "only", "", "Only pattern")
	fs.StringVar(&exclude, "exclude", "", "Exclude pattern")
	if err := fs.Parse(args); err != nil {
		printExecHelp()
		return 1
	}

	remaining := fs.Args()
	if len(remaining) == 0 {
		ui.ErrorMsg("No command specified")
		fmt.Println("Usage: iskra exec [flags] <command>")
		return 1
	}

	command := strings.Join(remaining, " ")
	repos := scanner.SelectRepos(cfgMgr, "", only, exclude)

	if len(repos) == 0 {
		ui.WarningMsg("No repositories found")
		return 0
	}

	opts := exec.Options{
		Parallel: parallel,
		FailFast: failFast,
		Quiet:    quiet,
	}

	result := exec.RunBatch(repos, command, opts)

	if jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		return 0
	}

	if !quiet {
		ui.CompactHeader()
		ui.InfoMsg(fmt.Sprintf("Running '%s' on %d repos", command, len(repos)))
		fmt.Println()
	}

	// Print results
	for _, r := range result.Results {
		if r.Success {
			fmt.Printf("%s %s\n", ui.DotSuccess, ui.Bold(r.Name))
		} else {
			fmt.Printf("%s %s %s\n", ui.DotError, ui.Bold(r.Name), ui.Err(fmt.Sprintf("(exit %d)", r.ExitCode)))
		}

		if r.Stdout != "" && !quiet {
			// Indent output
			lines := strings.Split(r.Stdout, "\n")
			for _, line := range lines {
				fmt.Printf("  %s\n", line)
			}
		}

		if r.Stderr != "" && !quiet {
			lines := strings.Split(r.Stderr, "\n")
			for _, line := range lines {
				fmt.Printf("  %s\n", ui.Err(line))
			}
		}
	}

	if !quiet {
		fmt.Println()
		ui.Summary("EXEC", result.ReposTotal, result.ReposSuccess, result.ReposFailed, result.Duration)
	}

	if result.ReposFailed > 0 {
		return 1
	}
	return 0
}

func printExecHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra exec") + " - Run a command across all tracked repos")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra exec [flags] <command>")
	fmt.Println()
	fmt.Println(ui.Bold("EXAMPLES:"))
	fmt.Println("    iskra exec git fetch")
	fmt.Println("    iskra exec -p 4 npm install")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -p <n>             Parallel workers (default: 1)")
	fmt.Println("    -fail-fast         Stop on first error")
	fmt.Println("    -only <pattern>    Only include repos matching pattern")
	fmt.Println("    -exclude <pattern> Exclude repos matching pattern")
	fmt.Println()
}
