package pulse

import (
	"fmt"
	"strings"
)

// ── tag ───────────────────────────────────────────────────────────────────────

// RunTag manages git tags.
// Usage:
//
//	iskra pulse tag                    → list tags
//	iskra pulse tag <name>             → create lightweight tag at HEAD
//	iskra pulse tag <name> -m <msg>    → create annotated tag
//	iskra pulse tag <name> <hash>      → tag a specific commit
//	iskra pulse tag --delete <name>    → delete a tag
//	iskra pulse tag --push [<name>]    → push tag(s) to origin
func RunTag(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	if len(args) == 0 {
		return listTags()
	}

	var deleteName, message, pushName, targetHash string
	var push bool
	var positional []string

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--delete", "-d":
			if i+1 < len(args) {
				i++
				deleteName = args[i]
			}
		case "--push":
			push = true
			if i+1 < len(args) && !strings.HasPrefix(args[i+1], "--") {
				i++
				pushName = args[i]
			}
		case "-m", "--message":
			if i+1 < len(args) {
				i++
				message = args[i]
			}
		default:
			positional = append(positional, args[i])
		}
	}

	if deleteName != "" {
		if !confirm(fmt.Sprintf("Delete tag %s?", red.Render(deleteName))) {
			infoMsg("Aborted.")
			return 0
		}
		if err := gitRun("tag", "-d", deleteName); err != nil {
			errMsg(fmt.Sprintf("Failed to delete tag: %s", deleteName))
			return 1
		}
		okMsg(fmt.Sprintf("Deleted tag %s", deleteName))
		return 0
	}

	if push {
		if pushName != "" {
			if err := gitRun("push", "origin", "refs/tags/"+pushName); err != nil {
				errMsg(fmt.Sprintf("Failed to push tag: %s", pushName))
				return 1
			}
			okMsg(fmt.Sprintf("Pushed tag %s to origin", pushName))
		} else {
			if err := gitRun("push", "origin", "--tags"); err != nil {
				errMsg("Failed to push tags")
				return 1
			}
			okMsg("Pushed all tags to origin")
		}
		return 0
	}

	if len(positional) == 0 {
		return listTags()
	}

	tagName := positional[0]
	if len(positional) > 1 {
		targetHash = positional[1]
	}

	// Create tag
	var tagArgs []string
	if message != "" {
		tagArgs = []string{"tag", "-a", tagName, "-m", message}
	} else {
		tagArgs = []string{"tag", tagName}
	}
	if targetHash != "" {
		tagArgs = append(tagArgs, targetHash)
	}

	if err := gitRun(tagArgs...); err != nil {
		errMsg(fmt.Sprintf("Failed to create tag: %s", tagName))
		return 1
	}

	kind := "lightweight"
	if message != "" {
		kind = "annotated"
	}
	okMsg(fmt.Sprintf("Created %s tag %s", kind, cyan.Render(tagName)))

	if confirm("Push tag to origin?") {
		if err := gitRun("push", "origin", "refs/tags/"+tagName); err != nil {
			errMsg("Failed to push tag")
			return 1
		}
		okMsg(fmt.Sprintf("Pushed %s to origin", tagName))
	}

	return 0
}

func listTags() int {
	out, err := gitOutput("tag", "--sort=-version:refname", "--format=%(refname:short)|||%(objecttype)|||%(taggerdate:short)|||%(subject)")
	if err != nil || strings.TrimSpace(out) == "" {
		infoMsg("No tags found")
		return 0
	}

	type tagEntry struct {
		name    string
		kind    string
		date    string
		subject string
	}

	var tags []tagEntry
	for line := range strings.SplitSeq(out, "\n") {
		parts := strings.SplitN(line, "|||", 4)
		if len(parts) < 4 || parts[0] == "" {
			continue
		}
		kind := "lightweight"
		if parts[1] == "tag" {
			kind = "annotated"
		}
		tags = append(tags, tagEntry{parts[0], kind, parts[2], parts[3]})
	}

	if len(tags) == 0 {
		infoMsg("No tags found")
		return 0
	}

	fmt.Println()
	fmt.Println(bold.Render("Tags:"))
	fmt.Println()

	// Sort by name descending (already done via --sort)
	for _, t := range tags {
		kindStr := dim.Render("light")
		if t.kind == "annotated" {
			kindStr = cyan.Render("annot")
		}
		dateStr := ""
		if t.date != "" {
			dateStr = dim.Render(t.date)
		}
		subj := ""
		if t.subject != "" {
			subj = "  " + dim.Render(t.subject)
		}
		fmt.Printf("  %s  %s  %s%s\n", yellow.Render(t.name), kindStr, dateStr, subj)
	}
	fmt.Println()
	return 0
}
