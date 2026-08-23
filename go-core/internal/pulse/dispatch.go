package pulse

import "fmt"

// ── dispatch ──────────────────────────────────────────────────────────────────

// Dispatch routes "iskra pulse <subcommand>" to the right function.
// Returns exit code.
func Dispatch(sub string, args []string) int {
	switch sub {
	case "reset":
		return RunReset(args)
	case "switch", "sw":
		return RunSwitch(args)
	case "cherry-pick", "cp":
		return RunCherryPick(args)
	case "rebase", "rb":
		return RunRebase(args)
	case "tag":
		return RunTag(args)
	case "filter":
		return RunFilter(args)
	case "blame":
		return RunBlame(args)
	case "fixup":
		return RunFixup(args)
	case "help", "-h", "--help":
		printPulseHelp()
		return 0
	default:
		printPulseHelp()
		return 1
	}
}

func printPulseHelp() {
	fmt.Println()
	fmt.Println(bold.Render("iskra pulse") + " — mono-repo operations")
	fmt.Println()
	fmt.Println(dim.Render("  Usage: iskra pulse <subcommand> [args...]"))
	fmt.Println()

	cmds := [][]string{
		{"(no sub)", "Commit and push current repo"},
		{"reset", "Discard changes (file or all, staged or unstaged)"},
		{"switch", "Switch or create branches with listing UI"},
		{"cherry-pick", "Pick commits onto current branch"},
		{"rebase", "Rebase current branch onto a target"},
		{"tag", "Create, list, delete, and push tags"},
		{"fixup", "Squash staged changes into a past commit"},
		{"blame", "Per-line author view of a file"},
		{"filter", "Rewrite history (wraps git-filter-repo)"},
	}

	maxLen := 0
	for _, c := range cmds {
		if len(c[0]) > maxLen {
			maxLen = len(c[0])
		}
	}

	for _, c := range cmds {
		fmt.Printf("  %s  %s\n",
			cyan.Render(fmt.Sprintf("%-*s", maxLen, c[0])),
			dim.Render(c[1]),
		)
	}
	fmt.Println()
}
