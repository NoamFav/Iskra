// Package info provides repository statistics like onefetch.
package info

import (
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"

	"github.com/charmbracelet/lipgloss"
)

var (
	dimStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("245"))
	greenStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("82"))
	redStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	cyanStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("86"))
	yellowStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("226"))
	boldStyle   = lipgloss.NewStyle().Bold(true)
	boldCyan    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	magentaStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("213"))
	orangeStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	borderColor  = lipgloss.NewStyle().Foreground(lipgloss.Color("238"))
	labelStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("245")).Width(10)
)

// stripANSI removes ANSI escape sequences to get true visible width
func visibleLen(s string) int {
	inEscape := false
	width := 0
	for i := 0; i < len(s); {
		if s[i] == '\x1b' {
			inEscape = true
			i++
			continue
		}
		if inEscape {
			if s[i] == 'm' {
				inEscape = false
			}
			i++
			continue
		}
		r, size := utf8.DecodeRuneInString(s[i:])
		_ = r
		width++
		i += size
	}
	return width
}

func padRight(s string, width int) string {
	vis := visibleLen(s)
	if vis >= width {
		return s
	}
	return s + strings.Repeat(" ", width-vis)
}

// label renders a fixed-width dim label
func label(s string) string {
	return dimStyle.Render(fmt.Sprintf("%-10s", s))
}

// Display prints the repository info to stdout
func Display(info *RepoInfo) {
	fmt.Println()

	art := GetASCIIArt(info.TopLanguage)
	artColor := GetLangColor(info.TopLanguage)
	artStyle := lipgloss.NewStyle().Foreground(artColor)

	// Measure true art width (no ANSI in art strings)
	artWidth := 0
	for _, line := range art {
		if len(line) > artWidth {
			artWidth = len(line)
		}
	}

	// Info column width (visible chars)
	infoColWidth := 54

	// Total inner width: 2 (left pad) + artWidth + 2 (gap) + infoColWidth + 2 (right pad)
	innerWidth := 2 + artWidth + 2 + infoColWidth + 2

	// ── Build info lines ──────────────────────────────────────
	type infoLine struct {
		rendered string // may contain ANSI
		visLen   int
	}
	var lines []infoLine

	addLine := func(rendered string) {
		lines = append(lines, infoLine{rendered, visibleLen(rendered)})
	}

	addBlank := func() {
		lines = append(lines, infoLine{"", 0})
	}

	// Name / branch
	addLine(boldCyan.Render(info.Name) + dimStyle.Render("  on ") + greenStyle.Render(" "+info.Branch))

	// HEAD
	headVal := yellowStyle.Render(info.Head)
	if info.HeadRefs != "" {
		headVal += " " + dimStyle.Render("("+info.HeadRefs+")")
	}
	addLine(label("HEAD") + headVal)

	// Upstream ahead/behind
	if info.Upstream.Ahead > 0 || info.Upstream.Behind > 0 {
		var parts []string
		if info.Upstream.Ahead > 0 {
			parts = append(parts, greenStyle.Render(fmt.Sprintf("↑%d", info.Upstream.Ahead)))
		}
		if info.Upstream.Behind > 0 {
			parts = append(parts, redStyle.Render(fmt.Sprintf("↓%d", info.Upstream.Behind)))
		}
		addLine(label("Upstream") + strings.Join(parts, " "))
	} else {
		addLine(label("Upstream") + greenStyle.Render("✓ up to date"))
	}

	// Refs
	var refParts []string
	if info.Branches > 0 {
		s := "branch"
		if info.Branches > 1 {
			s = "branches"
		}
		refParts = append(refParts, fmt.Sprintf("%d %s", info.Branches, s))
	}
	if info.Tags > 0 {
		s := "tag"
		if info.Tags > 1 {
			s = "tags"
		}
		refParts = append(refParts, fmt.Sprintf("%d %s", info.Tags, s))
	}
	if len(refParts) > 0 {
		addLine(label("Refs") + strings.Join(refParts, ", "))
	}

	// Pending changes (staged + unstaged)
	if info.Pending.Files > 0 {
		pending := greenStyle.Render(fmt.Sprintf("+%d", info.Pending.Added)) + " " +
			redStyle.Render(fmt.Sprintf("-%d", info.Pending.Deleted)) +
			dimStyle.Render(fmt.Sprintf("  %d file", info.Pending.Files))
		if info.Pending.Files != 1 {
			pending += dimStyle.Render("s")
		}
		addLine(label("Pending") + pending)
	}

	// Version
	if info.Version != "" {
		addLine(label("Version") + cyanStyle.Render(info.Version))
	}

	// Open PRs (if gh available)
	if info.HasGH {
		if info.OpenPRs > 0 {
			addLine(label("Open PRs") + magentaStyle.Render(fmt.Sprintf("%d open", info.OpenPRs)))
		} else {
			addLine(label("Open PRs") + dimStyle.Render("none"))
		}
	}

	// Timestamps
	addLine(label("Created") + info.Created + " ago")
	addLine(label("Changed") + info.LastChange)

	// Commits
	addLine(label("Commits") + greenStyle.Render(fmt.Sprintf("%d", info.Commits)))

	// LOC + size
	addLine(label("Lines") + FormatNumber(info.TotalLOC) + dimStyle.Render("  size ") + info.Size)

	// Languages bar
	if len(info.Languages) > 0 {
		topLangs := getTopLanguages(info.Languages, 4)
		var langParts []string
		for _, lc := range topLangs {
			pct := float64(lc.count) / float64(info.TotalLOC) * 100
			color := GetLangColor(lc.lang)
			s := lipgloss.NewStyle().Foreground(color)
			langParts = append(langParts, s.Render("●")+lc.lang+fmt.Sprintf(" %.0f%%", pct))
		}
		addLine(label("Lang") + strings.Join(langParts, " "))
	}

	// Authors
	if len(info.Authors) > 0 {
		var authParts []string
		for i, auth := range info.Authors {
			if i >= 3 {
				break
			}
			name := auth.Name
			if len(name) > 14 {
				name = name[:14]
			}
			authParts = append(authParts, greenStyle.Render(name)+fmt.Sprintf(" %.0f%%", auth.Percent))
		}
		addLine(label("Authors") + strings.Join(authParts, " "))
	}

	// License
	if info.License != "" {
		addLine(label("License") + greenStyle.Render(info.License))
	}

	// Recent commits section
	if len(info.RecentCommits) > 0 {
		addBlank()
		addLine(boldStyle.Render("Recent commits"))
		for _, c := range info.RecentCommits {
			hashPart := yellowStyle.Render(c.Hash)
			whenPart := dimStyle.Render(c.When)
			subj := c.Subject
			// truncate subject to fit
			maxSubj := infoColWidth - 10 - 14
			if visibleLen(subj) > maxSubj {
				subj = subj[:maxSubj-1] + "…"
			}
			addLine("  " + hashPart + " " + subj + "  " + whenPart)
		}
	}

	// ── Render ─────────────────────────────────────────────────

	// Pad art and lines to same row count
	maxRows := max(len(art), len(lines))
	for len(art) < maxRows {
		art = append(art, "")
	}
	for len(lines) < maxRows {
		lines = append(lines, infoLine{"", 0})
	}

	border := borderColor

	topLine := border.Render("╭" + strings.Repeat("─", innerWidth) + "╮")
	botLine := border.Render("╰" + strings.Repeat("─", innerWidth) + "╯")
	emptyLine := border.Render("│") + strings.Repeat(" ", innerWidth) + border.Render("│")

	fmt.Println(topLine)

	// URL / remote as subtitle
	if info.Remote != "" {
		urlContent := "  " + dimStyle.Render(info.Remote)
		fmt.Println(border.Render("│") + padRight(urlContent, innerWidth) + border.Render("│"))
	}

	fmt.Println(emptyLine)

	for i := 0; i < maxRows; i++ {
		// Art side: pad to artWidth
		artLine := art[i]
		artPadded := artLine + strings.Repeat(" ", artWidth-len(artLine))

		// Info side
		infoRendered := lines[i].rendered

		// Compose: "│ " + art + "  " + info + padding + " │"
		leftPad := "  "
		gap := "  "
		rightPad := "  "

		content := leftPad + artStyle.Render(artPadded) + gap + infoRendered
		// pad to innerWidth
		visContent := 2 + artWidth + 2 + lines[i].visLen
		if visContent < innerWidth-2 {
			content += strings.Repeat(" ", innerWidth-2-visContent)
		}
		content += rightPad

		fmt.Println(border.Render("│") + content + border.Render("│"))
	}

	fmt.Println(emptyLine)
	fmt.Println(botLine)
	fmt.Println()
}

type langCount struct {
	lang  string
	count int
}

func getTopLanguages(languages map[string]int, n int) []langCount {
	var langs []langCount
	for l, c := range languages {
		langs = append(langs, langCount{l, c})
	}
	sort.Slice(langs, func(i, j int) bool {
		return langs[i].count > langs[j].count
	})
	if len(langs) > n {
		langs = langs[:n]
	}
	return langs
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
