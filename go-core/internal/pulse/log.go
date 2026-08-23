package pulse

import (
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"

	"github.com/NoamFav/iskra/internal/ui"
)

// RunLog implements "iskra log".
func RunLog(args []string) int {
	if ui.HasHelpFlag(args) {
		printLogHelp()
		return 0
	}
	fs := flag.NewFlagSet("log", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var n int
	var oneline, graph, all bool
	var author, since, until, grep string
	fs.IntVar(&n, "n", 20, "Number of commits")
	fs.BoolVar(&oneline, "oneline", false, "One line format")
	fs.BoolVar(&graph, "graph", false, "Show graph")
	fs.BoolVar(&all, "all", false, "All branches")
	fs.StringVar(&author, "author", "", "Filter by author")
	fs.StringVar(&since, "since", "", "Since date")
	fs.StringVar(&until, "until", "", "Until date")
	fs.StringVar(&grep, "grep", "", "Search commits")
	if err := fs.Parse(args); err != nil {
		printLogHelp()
		return 1
	}

	// Build git log command
	gitArgs := []string{"log", fmt.Sprintf("-n%d", n)}

	if oneline {
		gitArgs = append(gitArgs, "--oneline")
	} else {
		gitArgs = append(gitArgs, "--format=%C(cyan)%h%Creset %C(yellow)%ad%Creset %s %C(green)<%an>%Creset", "--date=short")
	}

	if graph {
		gitArgs = append(gitArgs, "--graph")
	}
	if all {
		gitArgs = append(gitArgs, "--all")
	}
	if author != "" {
		gitArgs = append(gitArgs, "--author="+author)
	}
	if since != "" {
		gitArgs = append(gitArgs, "--since="+since)
	}
	if until != "" {
		gitArgs = append(gitArgs, "--until="+until)
	}
	if grep != "" {
		gitArgs = append(gitArgs, "--grep="+grep)
	}

	// Run git log
	cmd := exec.Command("git", gitArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return 1
	}
	return 0
}

func printLogHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra log") + " - Show git log (pretty formatted)")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra log [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -n <n>           Number of commits (default: 20)")
	fmt.Println("    -oneline         One line per commit")
	fmt.Println("    -graph           Show branch graph")
	fmt.Println("    -all             Include all branches")
	fmt.Println("    -author <name>   Filter by author")
	fmt.Println("    -since <date>    Commits since date (e.g. 2024-01-01)")
	fmt.Println("    -until <date>    Commits until date")
	fmt.Println("    -grep <text>     Search commit messages")
	fmt.Println()
}
