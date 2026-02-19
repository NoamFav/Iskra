// Package info provides repository statistics like onefetch.
package info

import (
	"fmt"
	"sort"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

var (
	dimStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("245"))
	greenStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("82"))
	redStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	cyanStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("86"))
	yellowStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("226"))
	boldStyle    = lipgloss.NewStyle().Bold(true)
	boldCyan     = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
)

// Display prints the repository info to stdout
func Display(info *RepoInfo) {
	fmt.Println()

	// Get ASCII art for top language
	art := GetASCIIArt(info.TopLanguage)
	artColor := GetLangColor(info.TopLanguage)
	artStyle := lipgloss.NewStyle().Foreground(artColor)

	// Build info lines
	var infoLines []string

	// HEAD line
	headLine := dimStyle.Render("HEAD") + "        " + yellowStyle.Render(info.Head)
	if info.HeadRefs != "" {
		headLine += " " + dimStyle.Render("("+info.HeadRefs+")")
	}
	infoLines = append(infoLines, headLine)

	// Branches/tags
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
		infoLines = append(infoLines, dimStyle.Render("Refs")+"        "+strings.Join(refParts, ", "))
	}

	// Pending changes
	if info.Pending.Added > 0 || info.Pending.Deleted > 0 {
		pending := dimStyle.Render("Pending") + "     " +
			greenStyle.Render(fmt.Sprintf("+%d", info.Pending.Added)) + " " +
			redStyle.Render(fmt.Sprintf("-%d", info.Pending.Deleted))
		infoLines = append(infoLines, pending)
	}

	// Version
	if info.Version != "" {
		infoLines = append(infoLines, dimStyle.Render("Version")+"     "+cyanStyle.Render(info.Version))
	}

	// Created & Last change
	infoLines = append(infoLines, dimStyle.Render("Created")+"     "+info.Created+" ago")
	infoLines = append(infoLines, dimStyle.Render("Changed")+"     "+info.LastChange)

	// Commits
	infoLines = append(infoLines, dimStyle.Render("Commits")+"     "+greenStyle.Render(fmt.Sprintf("%d", info.Commits)))

	// Lines of code + Size
	infoLines = append(infoLines, dimStyle.Render("Lines")+"       "+FormatNumber(info.TotalLOC)+"  "+dimStyle.Render("Size")+" "+info.Size)

	// Languages
	if len(info.Languages) > 0 {
		langLine := dimStyle.Render("Lang") + "        "
		topLangs := getTopLanguages(info.Languages, 3)
		var langParts []string
		for _, lc := range topLangs {
			pct := float64(lc.count) / float64(info.TotalLOC) * 100
			color := GetLangColor(lc.lang)
			style := lipgloss.NewStyle().Foreground(color)
			langParts = append(langParts, style.Render("●")+lc.lang+fmt.Sprintf(" %.0f%%", pct))
		}
		langLine += strings.Join(langParts, " ")
		infoLines = append(infoLines, langLine)
	}

	// Authors
	if len(info.Authors) > 0 {
		authLine := dimStyle.Render("Authors") + "     "
		var authParts []string
		for i, auth := range info.Authors {
			if i >= 2 {
				break
			}
			name := auth.Name
			if len(name) > 12 {
				name = name[:12]
			}
			authParts = append(authParts, greenStyle.Render(name)+fmt.Sprintf(" %.0f%%", auth.Percent))
		}
		authLine += strings.Join(authParts, " ")
		infoLines = append(infoLines, authLine)
	}

	// License
	if info.License != "" {
		infoLines = append(infoLines, dimStyle.Render("License")+"     "+greenStyle.Render(info.License))
	}

	// Pad to same length
	maxRows := max(len(art), len(infoLines))
	for len(art) < maxRows {
		art = append(art, "")
	}
	for len(infoLines) < maxRows {
		infoLines = append(infoLines, "")
	}

	// Calculate art width
	artWidth := 0
	for _, line := range art {
		if len(line) > artWidth {
			artWidth = len(line)
		}
	}
	artWidth += 4 // padding

	// Print side by side
	borderStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("86"))
	topBorder := borderStyle.Render("╭" + strings.Repeat("─", artWidth+50) + "╮")
	botBorder := borderStyle.Render("╰" + strings.Repeat("─", artWidth+50) + "╯")

	fmt.Println(topBorder)

	// Title
	title := boldCyan.Render(info.Name)
	titleLine := borderStyle.Render("│") + " " + title + strings.Repeat(" ", artWidth+48-len(info.Name)) + borderStyle.Render("│")
	fmt.Println(titleLine)
	fmt.Println(borderStyle.Render("│") + strings.Repeat(" ", artWidth+50) + borderStyle.Render("│"))

	for i := 0; i < maxRows; i++ {
		artLine := art[i]
		// Pad art line
		for len(artLine) < artWidth-2 {
			artLine += " "
		}

		infoLine := ""
		if i < len(infoLines) {
			infoLine = infoLines[i]
		}

		// We need to handle the visible width vs actual width (with ANSI codes)
		line := borderStyle.Render("│") + " " + artStyle.Render(artLine) + "  " + infoLine

		// Add padding and closing border
		// This is tricky with ANSI codes, so we just add some spaces
		fmt.Print(line)
		fmt.Println("  " + borderStyle.Render("│"))
	}

	fmt.Println(borderStyle.Render("│") + strings.Repeat(" ", artWidth+50) + borderStyle.Render("│"))

	// URL footer
	if info.Remote != "" {
		urlLine := borderStyle.Render("│") + " " + dimStyle.Render(info.Remote)
		padding := artWidth + 48 - len(info.Remote)
		if padding > 0 {
			urlLine += strings.Repeat(" ", padding)
		}
		urlLine += borderStyle.Render("│")
		fmt.Println(urlLine)
	}

	fmt.Println(botBorder)
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
