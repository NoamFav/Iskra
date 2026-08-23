package pulse

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/NoamFav/iskra/internal/ui"
)

// RunStash implements "iskra stash".
func RunStash(args []string) int {
	if ui.HasHelpFlag(args) {
		printStashHelp()
		return 0
	}
	// Default to list if no subcommand
	subCmd := "list"
	if len(args) > 0 {
		subCmd = args[0]
		args = args[1:]
	}

	var gitArgs []string

	switch subCmd {
	case "list", "ls":
		gitArgs = []string{"stash", "list"}
	case "push", "save":
		gitArgs = []string{"stash", "push"}
		// Add message if provided
		if len(args) > 0 {
			gitArgs = append(gitArgs, "-m", strings.Join(args, " "))
		}
	case "pop":
		gitArgs = []string{"stash", "pop"}
		if len(args) > 0 {
			gitArgs = append(gitArgs, args[0])
		}
	case "apply":
		gitArgs = []string{"stash", "apply"}
		if len(args) > 0 {
			gitArgs = append(gitArgs, args[0])
		}
	case "drop":
		gitArgs = []string{"stash", "drop"}
		if len(args) > 0 {
			gitArgs = append(gitArgs, args[0])
		}
	case "show":
		gitArgs = []string{"stash", "show", "-p"}
		if len(args) > 0 {
			gitArgs = append(gitArgs, args[0])
		}
	case "clear":
		gitArgs = []string{"stash", "clear"}
	default:
		// Assume it's a stash reference like stash@{0}
		gitArgs = []string{"stash", "show", "-p", subCmd}
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

func printStashHelp() {
	fmt.Println()
	fmt.Println(ui.Title("⚡ Iskra stash") + " - Stash management")
	fmt.Println()
	fmt.Println(ui.Bold("USAGE:"))
	fmt.Println("    iskra stash [subcommand] [args]")
	fmt.Println()
	fmt.Println(ui.Bold("SUBCOMMANDS:"))
	fmt.Println("    list, ls          List all stashes  (default)")
	fmt.Println("    push [message]    Stash current changes")
	fmt.Println("    pop [stash@{n}]   Pop top stash (or specific)")
	fmt.Println("    apply [stash@{n}] Apply stash without removing")
	fmt.Println("    drop [stash@{n}]  Delete a stash entry")
	fmt.Println("    show [stash@{n}]  Show stash diff")
	fmt.Println("    clear             Delete all stashes")
	fmt.Println()
}
