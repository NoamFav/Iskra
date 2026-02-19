// Package config handles loading and managing Iskra configuration.
// Maintains compatibility with the Python YAML structure.
package config

import (
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// GlobalConfig holds all global settings - mirrors Python's GlobalConfig
type GlobalConfig struct {
	// Directory settings
	BaseDir        string   `yaml:"base_dir" json:"base_dir"`
	ConfigDir      string   `yaml:"config_dir" json:"config_dir"`
	MaxDepth       int      `yaml:"max_depth" json:"max_depth"`
	FollowSymlinks bool     `yaml:"follow_symlinks" json:"follow_symlinks"`
	ExcludePatterns []string `yaml:"exclude_patterns" json:"exclude_patterns"`
	OnlyPatterns    []string `yaml:"only_patterns" json:"only_patterns"`

	// Git settings
	DefaultBranch     string   `yaml:"default_branch" json:"default_branch"`
	ProtectedBranches []string `yaml:"protected_branches" json:"protected_branches"`
	AutoPull          bool     `yaml:"auto_pull" json:"auto_pull"`
	AutoPush          bool     `yaml:"auto_push" json:"auto_push"`
	AutoStash         bool     `yaml:"auto_stash" json:"auto_stash"`

	// AI settings
	UseAICommit        bool   `yaml:"use_ai_commit" json:"use_ai_commit"`
	CommitMessageStyle string `yaml:"commit_message_style" json:"commit_message_style"`
	AIProvider         string `yaml:"ai_provider" json:"ai_provider"`
	OpenAIAPIKey       string `yaml:"openai_api_key" json:"openai_api_key,omitempty"`
	OpenAIModel        string `yaml:"openai_model" json:"openai_model"`
	ClaudeAPIKey       string `yaml:"claude_api_key" json:"claude_api_key,omitempty"`
	ClaudeModel        string `yaml:"claude_model" json:"claude_model"`

	// Safety settings
	RequireConfirmation          bool `yaml:"require_confirmation" json:"require_confirmation"`
	RequireConfirmationProtected bool `yaml:"require_confirmation_for_protected" json:"require_confirmation_for_protected"`
	DryRun                       bool `yaml:"dry_run" json:"dry_run"`
	CheckSSHKeys                 bool `yaml:"check_ssh_keys" json:"check_ssh_keys"`
	WarnConflicts                bool `yaml:"warn_conflicts" json:"warn_conflicts"`

	// Display settings
	ShowDiff  bool `yaml:"show_diff" json:"show_diff"`
	Verbose   bool `yaml:"verbose" json:"verbose"`
	UseRichUI bool `yaml:"use_rich_ui" json:"use_rich_ui"`

	// Filtering
	SkipReposWithoutChanges bool `yaml:"skip_repos_without_changes" json:"skip_repos_without_changes"`
	SkipReposAheadOfRemote  bool `yaml:"skip_repos_ahead_of_remote" json:"skip_repos_ahead_of_remote"`

	// macOS specific
	HandleGitignore bool `yaml:"handle_gitignore" json:"handle_gitignore"`
	RemoveDSStore   bool `yaml:"remove_ds_store" json:"remove_ds_store"`
}

// RepoInfo holds info about a tracked repository
type RepoInfo struct {
	Path          string `json:"path"`
	Name          string `json:"name"`
	RemoteURL     string `json:"remote_url,omitempty"`
	DefaultBranch string `json:"default_branch,omitempty"`
	LastCommit    string `json:"last_commit,omitempty"`
	LastUpdated   string `json:"last_updated,omitempty"`
	Active        bool   `json:"active"`
}

// RepoConfig holds per-repository overrides
type RepoConfig struct {
	ProtectedBranches    []string `yaml:"protected_branches,omitempty" json:"protected_branches,omitempty"`
	UseAICommit          *bool    `yaml:"use_ai_commit,omitempty" json:"use_ai_commit,omitempty"`
	CommitMessageStyle   string   `yaml:"commit_message_style,omitempty" json:"commit_message_style,omitempty"`
	RequireConfirmation  *bool    `yaml:"require_confirmation,omitempty" json:"require_confirmation,omitempty"`
	AutoPull             *bool    `yaml:"auto_pull,omitempty" json:"auto_pull,omitempty"`
	AutoPush             *bool    `yaml:"auto_push,omitempty" json:"auto_push,omitempty"`
	ExcludeFiles         []string `yaml:"exclude_files,omitempty" json:"exclude_files,omitempty"`
	CustomCommitTemplate string   `yaml:"custom_commit_template,omitempty" json:"custom_commit_template,omitempty"`
	PreCommitCommand     string   `yaml:"pre_commit_command,omitempty" json:"pre_commit_command,omitempty"`
	PostCommitCommand    string   `yaml:"post_commit_command,omitempty" json:"post_commit_command,omitempty"`
}

// Theme holds UI theming options
type Theme struct {
	Theme        string            `yaml:"theme" json:"theme"`
	IconsEnabled bool              `yaml:"icons_enabled" json:"icons_enabled"`
	Colors       map[string]string `yaml:"colors,omitempty" json:"colors,omitempty"`
}

// Manager handles config loading and saving
type Manager struct {
	ConfigDir    string
	GlobalConfig *GlobalConfig
	TrackedRepos map[string]*RepoInfo
	UIConfig     *Theme
}

// DefaultGlobalConfig returns sensible defaults
func DefaultGlobalConfig() *GlobalConfig {
	return &GlobalConfig{
		BaseDir:                      "~/Neoware",
		ConfigDir:                    "~/.config/iskra",
		MaxDepth:                     3,
		FollowSymlinks:               true,
		ExcludePatterns:              []string{},
		OnlyPatterns:                 []string{},
		DefaultBranch:                "main",
		ProtectedBranches:            []string{"main", "master", "production"},
		AutoPull:                     true,
		AutoPush:                     true,
		AutoStash:                    false,
		UseAICommit:                  true,
		CommitMessageStyle:           "conventional",
		AIProvider:                   "ollama",
		OpenAIModel:                  "gpt-4o-mini",
		ClaudeModel:                  "claude-sonnet-4-20250514",
		RequireConfirmation:          true,
		RequireConfirmationProtected: true,
		DryRun:                       false,
		CheckSSHKeys:                 true,
		WarnConflicts:                true,
		ShowDiff:                     false,
		Verbose:                      false,
		UseRichUI:                    true,
		SkipReposWithoutChanges:      false,
		SkipReposAheadOfRemote:       false,
		HandleGitignore:              false,
		RemoveDSStore:                false,
	}
}

// DefaultTheme returns default UI theme
func DefaultTheme() *Theme {
	return &Theme{
		Theme:        "default",
		IconsEnabled: true,
		Colors:       nil,
	}
}

// NewManager creates a new config manager
func NewManager(configDir string) (*Manager, error) {
	if configDir == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return nil, err
		}
		configDir = filepath.Join(home, ".config", "iskra")
	}

	// Expand ~ if present
	if len(configDir) > 0 && configDir[0] == '~' {
		home, err := os.UserHomeDir()
		if err != nil {
			return nil, err
		}
		configDir = filepath.Join(home, configDir[1:])
	}

	m := &Manager{
		ConfigDir:    configDir,
		GlobalConfig: DefaultGlobalConfig(),
		TrackedRepos: make(map[string]*RepoInfo),
		UIConfig:     DefaultTheme(),
	}

	if err := m.ensureStructure(); err != nil {
		return nil, err
	}

	if err := m.loadGlobalConfig(); err != nil {
		// Use defaults on error, don't fail
		m.GlobalConfig = DefaultGlobalConfig()
	}

	if err := m.loadTrackedRepos(); err != nil {
		m.TrackedRepos = make(map[string]*RepoInfo)
	}

	if err := m.loadUIConfig(); err != nil {
		m.UIConfig = DefaultTheme()
	}

	return m, nil
}

func (m *Manager) ensureStructure() error {
	// Create config dir
	if err := os.MkdirAll(m.ConfigDir, 0755); err != nil {
		return err
	}

	// Create logs dir
	logsDir := filepath.Join(m.ConfigDir, "logs")
	if err := os.MkdirAll(logsDir, 0755); err != nil {
		return err
	}

	return nil
}

func (m *Manager) configFile() string {
	return filepath.Join(m.ConfigDir, "config.yaml")
}

func (m *Manager) reposFile() string {
	return filepath.Join(m.ConfigDir, "repos.json")
}

func (m *Manager) uiFile() string {
	return filepath.Join(m.ConfigDir, "ui.yaml")
}

func (m *Manager) loadGlobalConfig() error {
	data, err := os.ReadFile(m.configFile())
	if err != nil {
		if os.IsNotExist(err) {
			return nil // Use defaults
		}
		return err
	}

	return yaml.Unmarshal(data, m.GlobalConfig)
}

func (m *Manager) loadTrackedRepos() error {
	data, err := os.ReadFile(m.reposFile())
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	// Parse JSON manually since we need string keys
	var repos map[string]*RepoInfo
	if err := yaml.Unmarshal(data, &repos); err != nil {
		return err
	}
	m.TrackedRepos = repos
	return nil
}

func (m *Manager) loadUIConfig() error {
	data, err := os.ReadFile(m.uiFile())
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	return yaml.Unmarshal(data, m.UIConfig)
}

// LoadRepoConfig loads per-repo .iskra.yaml if it exists
func (m *Manager) LoadRepoConfig(repoPath string) (*RepoConfig, error) {
	configPath := filepath.Join(repoPath, ".iskra.yaml")
	data, err := os.ReadFile(configPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}

	var cfg RepoConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}

// MergeConfig merges global config with per-repo overrides
func (m *Manager) MergeConfig(repoPath string) *GlobalConfig {
	// Start with a copy of global config
	merged := *m.GlobalConfig

	repoConfig, err := m.LoadRepoConfig(repoPath)
	if err != nil || repoConfig == nil {
		return &merged
	}

	// Apply overrides
	if repoConfig.ProtectedBranches != nil {
		merged.ProtectedBranches = repoConfig.ProtectedBranches
	}
	if repoConfig.UseAICommit != nil {
		merged.UseAICommit = *repoConfig.UseAICommit
	}
	if repoConfig.CommitMessageStyle != "" {
		merged.CommitMessageStyle = repoConfig.CommitMessageStyle
	}
	if repoConfig.RequireConfirmation != nil {
		merged.RequireConfirmation = *repoConfig.RequireConfirmation
	}
	if repoConfig.AutoPull != nil {
		merged.AutoPull = *repoConfig.AutoPull
	}
	if repoConfig.AutoPush != nil {
		merged.AutoPush = *repoConfig.AutoPush
	}

	return &merged
}

// GetActiveRepos returns all active tracked repositories
func (m *Manager) GetActiveRepos() []*RepoInfo {
	var repos []*RepoInfo
	for _, repo := range m.TrackedRepos {
		if repo.Active {
			repos = append(repos, repo)
		}
	}
	return repos
}

// ExpandPath expands ~ to home directory
func ExpandPath(path string) string {
	if len(path) > 0 && path[0] == '~' {
		home, err := os.UserHomeDir()
		if err != nil {
			return path
		}
		return filepath.Join(home, path[1:])
	}
	return path
}
