package pulse

import (
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"

	"github.com/NoamFav/iskra/internal/ui"
)

// RunBranches implements "iskra branches".
func RunBranches(args []string) int {
	if ui.HasHelpFlag(args) {
		printBranchesHelp()
		return 0
	}
	fs := flag.NewFlagSet("branches", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var all, remote bool
	fs.BoolVar(&all, "all", false, "Show all branches")
	fs.BoolVar(&all, "a", false, "Show all branches")
	fs.BoolVar(&remote, "remote", false, "Show only remote branches")
	fs.BoolVar(&remote, "r", false, "Show only remote branches")
	if err := fs.Parse(args); err != nil {
		printBranchesHelp()
		return 1
	}

	gitArgs := []string{"branch", "-v", "--color=always"}

	if all {
		gitArgs = append(gitArgs, "-a")
	} else if remote {
		gitArgs = append(gitArgs, "-r")
	}

	cmd := exec.Command("git", gitArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return 1
	}
	return 0
}

func printBranchesHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra branches") + " - List git branches")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra branches [flags]")
	fmt.Println("    iskra br [flags]")
	fmt.Println()
	fmt.Println(ui.Bold("FLAGS:"))
	fmt.Println("    -a, -all      Show all branches (local + remote)")
	fmt.Println("    -r, -remote   Show only remote branches")
	fmt.Println()
}
