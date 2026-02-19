// Package info provides repository statistics like onefetch.
package info

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

// RepoInfo holds all repository information
type RepoInfo struct {
	Name        string            `json:"name"`
	Path        string            `json:"path"`
	Branch      string            `json:"branch"`
	Head        string            `json:"head"`
	HeadRefs    string            `json:"head_refs"`
	Remote      string            `json:"remote,omitempty"`
	Commits     int               `json:"commits"`
	Branches    int               `json:"branches"`
	Tags        int               `json:"tags"`
	Authors     []Author          `json:"authors"`
	License     string            `json:"license,omitempty"`
	Created     string            `json:"created"`
	LastChange  string            `json:"last_change"`
	TotalLOC    int               `json:"total_loc"`
	Languages   map[string]int    `json:"languages"`
	TopLanguage string            `json:"top_language"`
	Size        string            `json:"size"`
	FileCount   int               `json:"file_count"`
	Version     string            `json:"version,omitempty"`
	Pending     PendingChanges    `json:"pending"`
}

// Author represents a contributor
type Author struct {
	Name    string `json:"name"`
	Commits int    `json:"commits"`
	Percent float64 `json:"percent"`
}

// PendingChanges represents uncommitted changes
type PendingChanges struct {
	Added   int `json:"added"`
	Deleted int `json:"deleted"`
	Files   int `json:"files"`
}

// Language extensions mapping
var langExtensions = map[string]string{
	".py":         "Python",
	".js":         "JavaScript",
	".ts":         "TypeScript",
	".tsx":        "TypeScript",
	".jsx":        "JavaScript",
	".go":         "Go",
	".rs":         "Rust",
	".c":          "C",
	".h":          "C",
	".cpp":        "C++",
	".cc":         "C++",
	".hpp":        "C++",
	".java":       "Java",
	".kt":         "Kotlin",
	".swift":      "Swift",
	".rb":         "Ruby",
	".php":        "PHP",
	".cs":         "C#",
	".lua":        "Lua",
	".sh":         "Shell",
	".bash":       "Shell",
	".zsh":        "Shell",
	".fish":       "Shell",
	".pl":         "Perl",
	".r":          "R",
	".R":          "R",
	".scala":      "Scala",
	".ex":         "Elixir",
	".exs":        "Elixir",
	".erl":        "Erlang",
	".hs":         "Haskell",
	".ml":         "OCaml",
	".fs":         "F#",
	".clj":        "Clojure",
	".vim":        "Vim Script",
	".el":         "Emacs Lisp",
	".dart":       "Dart",
	".zig":        "Zig",
	".nim":        "Nim",
	".v":          "V",
	".html":       "HTML",
	".css":        "CSS",
	".scss":       "SCSS",
	".sass":       "Sass",
	".less":       "Less",
	".vue":        "Vue",
	".svelte":     "Svelte",
	".json":       "JSON",
	".yaml":       "YAML",
	".yml":        "YAML",
	".toml":       "TOML",
	".xml":        "XML",
	".md":         "Markdown",
	".sql":        "SQL",
	".dockerfile": "Dockerfile",
}

// GetInfo gathers all repository information
func GetInfo() (*RepoInfo, error) {
	root, err := getRepoRoot()
	if err != nil {
		return nil, fmt.Errorf("not in a git repository")
	}

	info := &RepoInfo{
		Path:      root,
		Name:      filepath.Base(root),
		Languages: make(map[string]int),
	}

	// Gather git info
	info.Branch = getBranch()
	info.Head = getHead()
	info.HeadRefs = getHeadRefs()
	info.Remote = getRemoteURL()
	info.Commits = getCommitCount()
	info.Branches = getBranchCount()
	info.Tags = getTagCount()
	info.Authors = getAuthors(info.Commits)
	info.License = getLicense(root)
	info.Created = getRepoAge()
	info.LastChange = getLastChangeRelative()
	info.Version = getLatestVersion()
	info.Pending = getPendingChanges()

	// Count lines of code
	info.TotalLOC, info.Languages = countLinesOfCode(root)
	info.TopLanguage = getTopLanguage(info.Languages)

	// Get size
	info.Size, info.FileCount = getRepoSize(root)

	return info, nil
}

func getRepoRoot() (string, error) {
	cmd := exec.Command("git", "rev-parse", "--show-toplevel")
	out, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

func getBranch() string {
	cmd := exec.Command("git", "rev-parse", "--abbrev-ref", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return "unknown"
	}
	return strings.TrimSpace(string(out))
}

func getHead() string {
	cmd := exec.Command("git", "rev-parse", "--short", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return "unknown"
	}
	return strings.TrimSpace(string(out))
}

func getHeadRefs() string {
	cmd := exec.Command("git", "log", "-1", "--format=%D")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	refs := strings.TrimSpace(string(out))
	refs = strings.ReplaceAll(refs, "HEAD -> ", "")
	refs = strings.ReplaceAll(refs, "origin/", "")

	parts := strings.Split(refs, ", ")
	seen := make(map[string]bool)
	var unique []string
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" && !seen[p] {
			seen[p] = true
			unique = append(unique, p)
		}
	}
	if len(unique) > 3 {
		unique = unique[:3]
	}
	return strings.Join(unique, ", ")
}

func getRemoteURL() string {
	cmd := exec.Command("git", "remote", "get-url", "origin")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	url := strings.TrimSpace(string(out))
	// Clean up SSH URLs
	if strings.HasPrefix(url, "git@") {
		url = strings.Replace(url, ":", "/", 1)
		url = strings.Replace(url, "git@", "https://", 1)
	}
	url = strings.TrimSuffix(url, ".git")
	return url
}

func getCommitCount() int {
	cmd := exec.Command("git", "rev-list", "--count", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return 0
	}
	count, _ := strconv.Atoi(strings.TrimSpace(string(out)))
	return count
}

func getBranchCount() int {
	cmd := exec.Command("git", "branch", "--list")
	out, err := cmd.Output()
	if err != nil {
		return 0
	}
	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	count := 0
	for _, l := range lines {
		if strings.TrimSpace(l) != "" {
			count++
		}
	}
	return count
}

func getTagCount() int {
	cmd := exec.Command("git", "tag", "--list")
	out, err := cmd.Output()
	if err != nil {
		return 0
	}
	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	count := 0
	for _, l := range lines {
		if strings.TrimSpace(l) != "" {
			count++
		}
	}
	return count
}

func getAuthors(totalCommits int) []Author {
	cmd := exec.Command("git", "shortlog", "-sn", "--all", "--no-merges")
	out, err := cmd.Output()
	if err != nil {
		return nil
	}

	re := regexp.MustCompile(`^\s*(\d+)\s+(.+)$`)
	var authors []Author

	for _, line := range strings.Split(string(out), "\n") {
		match := re.FindStringSubmatch(line)
		if match != nil {
			count, _ := strconv.Atoi(match[1])
			name := strings.TrimSpace(match[2])
			pct := 0.0
			if totalCommits > 0 {
				pct = float64(count) / float64(totalCommits) * 100
			}
			authors = append(authors, Author{
				Name:    name,
				Commits: count,
				Percent: pct,
			})
		}
	}
	return authors
}

func getRepoAge() string {
	cmd := exec.Command("git", "log", "--reverse", "--format=%ai", "-1")
	out, err := cmd.Output()
	if err != nil {
		return "unknown"
	}

	dateStr := strings.TrimSpace(string(out))
	if len(dateStr) < 10 {
		return "unknown"
	}
	dateStr = dateStr[:10]

	firstDate, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return dateStr
	}

	diff := time.Since(firstDate)
	days := int(diff.Hours() / 24)

	if days < 30 {
		return fmt.Sprintf("%d days", days)
	} else if days < 365 {
		months := days / 30
		if months == 1 {
			return "1 month"
		}
		return fmt.Sprintf("%d months", months)
	} else {
		years := days / 365
		months := (days % 365) / 30
		if months > 0 {
			return fmt.Sprintf("%dy %dmo", years, months)
		}
		if years == 1 {
			return "1 year"
		}
		return fmt.Sprintf("%d years", years)
	}
}

func getLastChangeRelative() string {
	cmd := exec.Command("git", "log", "-1", "--format=%ar")
	out, err := cmd.Output()
	if err != nil {
		return "unknown"
	}
	return strings.TrimSpace(string(out))
}

func getLatestVersion() string {
	cmd := exec.Command("git", "describe", "--tags", "--abbrev=0")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}

func getPendingChanges() PendingChanges {
	cmd := exec.Command("git", "diff", "--shortstat")
	out, err := cmd.Output()
	if err != nil {
		return PendingChanges{}
	}

	text := string(out)
	pc := PendingChanges{}

	// Parse "3 files changed, 10 insertions(+), 5 deletions(-)"
	reFiles := regexp.MustCompile(`(\d+) file`)
	reInsert := regexp.MustCompile(`(\d+) insertion`)
	reDelete := regexp.MustCompile(`(\d+) deletion`)

	if match := reFiles.FindStringSubmatch(text); match != nil {
		pc.Files, _ = strconv.Atoi(match[1])
	}
	if match := reInsert.FindStringSubmatch(text); match != nil {
		pc.Added, _ = strconv.Atoi(match[1])
	}
	if match := reDelete.FindStringSubmatch(text); match != nil {
		pc.Deleted, _ = strconv.Atoi(match[1])
	}

	return pc
}

func getLicense(root string) string {
	licenseFiles := []string{"LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"}

	for _, name := range licenseFiles {
		path := filepath.Join(root, name)
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}

		content := strings.ToLower(string(data[:min(500, len(data))]))

		switch {
		case strings.Contains(content, "mit license") || strings.Contains(content, "permission is hereby granted"):
			return "MIT"
		case strings.Contains(content, "apache license"):
			return "Apache 2.0"
		case strings.Contains(content, "gnu general public license"):
			if strings.Contains(content, "version 3") {
				return "GPL-3.0"
			} else if strings.Contains(content, "version 2") {
				return "GPL-2.0"
			}
			return "GPL"
		case strings.Contains(content, "bsd"):
			if strings.Contains(content, "3-clause") || strings.Contains(content, "three-clause") {
				return "BSD-3-Clause"
			} else if strings.Contains(content, "2-clause") || strings.Contains(content, "two-clause") {
				return "BSD-2-Clause"
			}
			return "BSD"
		case strings.Contains(content, "mozilla public license"):
			return "MPL-2.0"
		case strings.Contains(content, "unlicense") || strings.Contains(content, "public domain"):
			return "Unlicense"
		case strings.Contains(content, "isc license"):
			return "ISC"
		default:
			return "Custom"
		}
	}

	return ""
}

func countLinesOfCode(root string) (int, map[string]int) {
	byLang := make(map[string]int)

	// Get tracked files
	cmd := exec.Command("git", "ls-files")
	cmd.Dir = root
	out, err := cmd.Output()
	if err != nil {
		return 0, byLang
	}

	for _, relPath := range strings.Split(string(out), "\n") {
		relPath = strings.TrimSpace(relPath)
		if relPath == "" {
			continue
		}

		path := filepath.Join(root, relPath)
		ext := strings.ToLower(filepath.Ext(relPath))

		// Check for Dockerfile
		if ext == "" && strings.ToLower(filepath.Base(relPath)) == "dockerfile" {
			ext = ".dockerfile"
		}

		lang, ok := langExtensions[ext]
		if !ok {
			continue
		}

		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}

		lines := bytes.Count(data, []byte("\n"))
		if len(data) > 0 && data[len(data)-1] != '\n' {
			lines++
		}

		byLang[lang] += lines
	}

	total := 0
	for _, count := range byLang {
		total += count
	}

	return total, byLang
}

func getTopLanguage(languages map[string]int) string {
	if len(languages) == 0 {
		return ""
	}

	type langCount struct {
		lang  string
		count int
	}
	var langs []langCount
	for l, c := range languages {
		langs = append(langs, langCount{l, c})
	}
	sort.Slice(langs, func(i, j int) bool {
		return langs[i].count > langs[j].count
	})

	return langs[0].lang
}

func getRepoSize(root string) (string, int) {
	cmd := exec.Command("git", "ls-files")
	cmd.Dir = root
	out, err := cmd.Output()
	if err != nil {
		return "0 B", 0
	}

	files := strings.Split(strings.TrimSpace(string(out)), "\n")
	fileCount := 0
	var totalSize int64

	for _, relPath := range files {
		if relPath == "" {
			continue
		}
		fileCount++

		path := filepath.Join(root, relPath)
		info, err := os.Stat(path)
		if err != nil {
			continue
		}
		totalSize += info.Size()
	}

	var sizeStr string
	switch {
	case totalSize >= 1024*1024*1024:
		sizeStr = fmt.Sprintf("%.2f GiB", float64(totalSize)/(1024*1024*1024))
	case totalSize >= 1024*1024:
		sizeStr = fmt.Sprintf("%.2f MiB", float64(totalSize)/(1024*1024))
	case totalSize >= 1024:
		sizeStr = fmt.Sprintf("%.2f KiB", float64(totalSize)/1024)
	default:
		sizeStr = fmt.Sprintf("%d B", totalSize)
	}

	return sizeStr, fileCount
}

// FormatNumber formats a number with K/M suffix
func FormatNumber(n int) string {
	if n >= 1_000_000 {
		return fmt.Sprintf("%.1fM", float64(n)/1_000_000)
	} else if n >= 1_000 {
		return fmt.Sprintf("%.1fK", float64(n)/1_000)
	}
	return strconv.Itoa(n)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
