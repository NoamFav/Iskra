package pulse

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

// ── blame ─────────────────────────────────────────────────────────────────────

// RunBlame shows a pretty per-line blame for a file.
// Usage: iskra pulse blame <file> [--lines <n>] [--since <rev>]
func RunBlame(args []string) int {
	if _, err := repoRoot(); err != nil {
		errMsg(err.Error())
		return 1
	}

	var file, since string
	var lineLimit int

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--lines", "-n":
			if i+1 < len(args) {
				i++
				lineLimit, _ = strconv.Atoi(args[i])
			}
		case "--since":
			if i+1 < len(args) {
				i++
				since = args[i]
			}
		default:
			if file == "" {
				file = args[i]
			}
		}
	}

	if file == "" {
		errMsg("Usage: iskra pulse blame <file> [--lines <n>] [--since <rev>]")
		return 1
	}

	// Resolve file: if relative, try from cwd first, then from repo root
	if !filepath.IsAbs(file) {
		if _, err := os.Stat(file); os.IsNotExist(err) {
			if root, err2 := repoRoot(); err2 == nil {
				file = filepath.Join(root, file)
			}
		}
	}

	blameArgs := []string{"blame", "--line-porcelain"}
	if since != "" {
		blameArgs = append(blameArgs, since+"..HEAD")
	}
	blameArgs = append(blameArgs, file)

	cmd := exec.Command("git", blameArgs...)
	out, err := cmd.Output()
	if err != nil {
		errMsg(fmt.Sprintf("Failed to blame %s: %v", file, err))
		return 1
	}

	type blameEntry struct {
		hash    string
		author  string
		date    string
		lineNum int
		content string
	}

	var entries []blameEntry
	var cur blameEntry
	authorColors := make(map[string]lipgloss.Color)
	colorPalette := []lipgloss.Color{"82", "39", "213", "226", "196", "86", "214", "201"}
	colorIdx := 0

	lines := strings.SplitSeq(string(out), "\n")
	for line := range lines {
		if len(line) == 0 {
			continue
		}
		if len(line) > 40 && !strings.HasPrefix(line, "\t") {
			fields := strings.Fields(line)
			if len(fields) >= 3 {
				hash := fields[0]
				if len(hash) == 40 {
					cur.hash = hash[:7]
					lineNum, _ := strconv.Atoi(fields[2])
					cur.lineNum = lineNum
				}
			}
		}
		if after, ok := strings.CutPrefix(line, "author "); ok {
			cur.author = after
			if _, ok := authorColors[cur.author]; !ok {
				authorColors[cur.author] = colorPalette[colorIdx%len(colorPalette)]
				colorIdx++
			}
		}
		if after, ok := strings.CutPrefix(line, "author-time "); ok {
			ts, _ := strconv.ParseInt(after, 10, 64)
			// format as YYYY-MM-DD
			cur.date = fmt.Sprintf("%d", ts) // will reformat below
			_ = ts
		}
		if after, ok := strings.CutPrefix(line, "committer-time "); ok {
			ts, _ := strconv.ParseInt(after, 10, 64)
			cur.date = time.Unix(ts, 0).UTC().Format("2006-01-02")
		}
		if after, ok := strings.CutPrefix(line, "\t"); ok {
			cur.content = after
			entries = append(entries, cur)
			cur = blameEntry{}
		}
	}

	if lineLimit > 0 && lineLimit < len(entries) {
		entries = entries[:lineLimit]
	}

	// Calculate author column width
	maxAuthorLen := 0
	for a := range authorColors {
		if len(a) > maxAuthorLen {
			maxAuthorLen = len(a)
		}
	}
	if maxAuthorLen > 14 {
		maxAuthorLen = 14
	}

	fmt.Println()
	fmt.Println(bold.Render(filepath.Base(file)))
	fmt.Println()

	prevHash := ""
	for _, e := range entries {
		hashStr := dim.Render(e.hash)
		if e.hash != prevHash {
			hashStr = yellow.Render(e.hash)
		}
		prevHash = e.hash

		author := e.author
		if len(author) > maxAuthorLen {
			author = author[:maxAuthorLen-1] + "…"
		}
		color := authorColors[e.author]
		authorStr := lipgloss.NewStyle().Foreground(color).Render(fmt.Sprintf("%-*s", maxAuthorLen, author))

		lineNumStr := dim.Render(fmt.Sprintf("%4d", e.lineNum))
		content := e.content
		// truncate very long lines
		if len(content) > 80 {
			content = content[:77] + "..."
		}

		fmt.Printf("  %s  %s  %s  %s\n", hashStr, authorStr, lineNumStr, content)
	}
	fmt.Println()
	return 0
}
