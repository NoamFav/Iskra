// Package ui provides styled terminal output using Charm's Lip Gloss.
package ui

import (
	"github.com/charmbracelet/lipgloss"
)

// Colors - semantic color palette
var (
	ColorPrimary   = lipgloss.Color("86")  // Cyan
	ColorSecondary = lipgloss.Color("226") // Yellow
	ColorSuccess   = lipgloss.Color("82")  // Green
	ColorError     = lipgloss.Color("196") // Red
	ColorWarning   = lipgloss.Color("214") // Orange
	ColorInfo      = lipgloss.Color("39")  // Blue
	ColorMuted     = lipgloss.Color("245") // Gray
	ColorWhite     = lipgloss.Color("255")
)

// Styles
var (
	TitleStyle   = lipgloss.NewStyle().Bold(true).Foreground(ColorPrimary)
	SuccessStyle = lipgloss.NewStyle().Foreground(ColorSuccess)
	ErrorStyle   = lipgloss.NewStyle().Foreground(ColorError)
	WarningStyle = lipgloss.NewStyle().Foreground(ColorWarning)
	InfoStyle    = lipgloss.NewStyle().Foreground(ColorInfo)
	MutedStyle   = lipgloss.NewStyle().Foreground(ColorMuted)
	BoldStyle    = lipgloss.NewStyle().Bold(true)

	// Status dots
	DotSuccess = SuccessStyle.Render("●")
	DotError   = ErrorStyle.Render("●")
	DotWarning = WarningStyle.Render("●")
	DotInfo    = InfoStyle.Render("●")
	DotMuted   = MutedStyle.Render("●")
)

// Icons - Nerd Font icons
type IconSet struct {
	Git, Folder, File, Success, Error, Warning, Info        string
	Branch, Commit, Push, Pull, Add, Modified, Deleted      string
	Untracked, Conflict, Clock, Rocket, Spark, Check, Cross string
	Arrow, Dots, Lock                                       string
}

var NerdIcons = IconSet{
	Git: "", Folder: "", File: "", Success: "", Error: "",
	Warning: "", Info: "", Branch: "", Commit: "", Push: "",
	Pull: "", Add: "", Modified: "󰏫", Deleted: "", Untracked: "",
	Conflict: "", Clock: "", Rocket: "", Spark: "", Check: "",
	Cross: "", Arrow: "", Dots: "", Lock: "",
}

var MinimalIcons = IconSet{
	Git: "[git]", Folder: "[dir]", File: "[file]", Success: "[ok]", Error: "[ERR]",
	Warning: "[!]", Info: "[i]", Branch: "->", Commit: "*", Push: "^",
	Pull: "v", Add: "+", Modified: "~", Deleted: "-", Untracked: "?",
	Conflict: "!", Clock: "@", Rocket: ">>", Spark: "*", Check: "[x]",
	Cross: "[X]", Arrow: "->", Dots: "...", Lock: "[lock]",
}

var Icons = NerdIcons
var minimalMode = false

func SetMinimalMode(minimal bool) {
	minimalMode = minimal
	if minimal {
		Icons = MinimalIcons
	} else {
		Icons = NerdIcons
	}
}

func IsMinimal() bool {
	return minimalMode
}

// Helper functions
func Success(text string) string { return SuccessStyle.Render(text) }
func Err(text string) string     { return ErrorStyle.Render(text) }
func Warn(text string) string    { return WarningStyle.Render(text) }
func Inf(text string) string     { return InfoStyle.Render(text) }
func Mute(text string) string    { return MutedStyle.Render(text) }
func Bold(text string) string    { return BoldStyle.Render(text) }
func Title(text string) string   { return TitleStyle.Render(text) }
