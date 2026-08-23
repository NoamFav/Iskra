package pulse

import (
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"

	"github.com/NoamFav/iskra/internal/ui"
)

// RunDiff implements "iskra diff".
func RunDiff(args []string) int {
	if ui.HasHelpFlag(args) {
		printDiffHelp()
		return 0
	}
	fs := flag.NewFlagSet("diff", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var staged, cached bool
	var stat bool
	fs.BoolVar(&staged, "staged", false, "Show staged changes")
	fs.BoolVar(&cached, "cached", false, "Show staged changes (alias)")
	fs.BoolVar(&stat, "stat", false, "Show diffstat only")
	if err := fs.Parse(args); err != nil {
		printDiffHelp()
		return 1
	}

	gitArgs := []string{"diff", "--color=always"}

	if staged || cached {
		gitArgs = append(gitArgs, "--staged")
	}
	if stat {
		gitArgs = append(gitArgs, "--stat")
	}

	// Add remaining args (file paths)
	gitArgs = append(gitArgs, fs.Args()...)

	cmd := exec.Command("git", gitArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return 1
	}
	return 0
}

func printDiffHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra diff") + " - Show git diff (colored)")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra diff [flags] [files...]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -staged, -cached   Show staged changes only")
	fmt.Println("    -stat              Show diffstat summary only")
	fmt.Println()
}
