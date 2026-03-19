// Package processor handles the main repository processing logic.
package processor

import (
	"os"
	"time"

	"github.com/NoamFav/iskra/internal/ai"
	"github.com/NoamFav/iskra/internal/config"
	"github.com/NoamFav/iskra/internal/git"
)

// Options holds processing options (from CLI args)
type Options struct {
	StatusOnly    bool   `json:"status_only"`
	PullOnly      bool   `json:"pull_only"`
	Pull          bool   `json:"pull"`
	NoPush        bool   `json:"no_push"`
	NoAICommit    bool   `json:"no_ai_commit"`
	CommitMessage string `json:"commit_message"`
	DryRun        bool   `json:"dry_run"`
	ShowDiff      bool   `json:"show_diff"`
	Compact       bool   `json:"compact"`
}

// RepoResult holds the result of processing a single repository
type RepoResult struct {
	Path        string       `json:"path"`
	Name        string       `json:"name"`
	Status      string       `json:"status"` // success, failed, skipped
	Branch      string       `json:"branch"`
	Changes     *Changes     `json:"changes"`
	Remote      *Remote      `json:"remote"`
	Commit      *CommitInfo  `json:"commit,omitempty"`
	Operations  []Operation  `json:"operations"`
	Error       string       `json:"error,omitempty"`
	ElapsedMs   int64        `json:"elapsed_ms"`
	IsProtected bool         `json:"is_protected"`
	Conflicts   []string     `json:"conflicts,omitempty"`
}

// Changes holds change counts
type Changes struct {
	Uncommitted int `json:"uncommitted"`
	Staged      int `json:"staged"`
	Untracked   int `json:"untracked"`
	Total       int `json:"total"`
}

// Remote holds remote status
type Remote struct {
	Ahead  int    `json:"ahead"`
	Behind int    `json:"behind"`
	URL    string `json:"url"`
}

// CommitInfo holds commit details
type CommitInfo struct {
	Hash    string `json:"hash"`
	Message string `json:"message"`
	IsAI    bool   `json:"is_ai"`
}

// Operation represents a single operation performed
type Operation struct {
	Type    string `json:"type"` // pull, add, commit, push, stash, etc.
	Success bool   `json:"success"`
	Message string `json:"message,omitempty"`
	Error   string `json:"error,omitempty"`
}

// BatchResult holds results of processing multiple repos
type BatchResult struct {
	Success     bool          `json:"success"`
	Operation   string        `json:"operation"` // commit, status, pull
	ReposTotal  int           `json:"repos_total"`
	ReposSuccess int          `json:"repos_success"`
	ReposFailed  int          `json:"repos_failed"`
	Results     []*RepoResult `json:"results"`
	Errors      []string      `json:"errors"`
	ElapsedMs   int64         `json:"elapsed_ms"`
}

// Processor handles repository processing
type Processor struct {
	ConfigManager *config.Manager
	AIConfig      ai.Config
}

// NewProcessor creates a new processor
func NewProcessor(cfgMgr *config.Manager) *Processor {
	aiCfg := ai.Config{
		Provider:    cfgMgr.GlobalConfig.AIProvider,
		OpenAIKey:   cfgMgr.GlobalConfig.OpenAIAPIKey,
		OpenAIModel: cfgMgr.GlobalConfig.OpenAIModel,
		ClaudeKey:   cfgMgr.GlobalConfig.ClaudeAPIKey,
		ClaudeModel: cfgMgr.GlobalConfig.ClaudeModel,
	}

	return &Processor{
		ConfigManager: cfgMgr,
		AIConfig:      aiCfg,
	}
}

// ProcessRepo processes a single repository
func (p *Processor) ProcessRepo(repoPath string, opts Options) *RepoResult {
	start := time.Now()

	result := &RepoResult{
		Path:       repoPath,
		Name:       "", // Will be set from state
		Status:     "success",
		Operations: []Operation{},
	}

	// Get current directory to restore later
	origDir, err := os.Getwd()
	if err != nil {
		result.Status = "failed"
		result.Error = err.Error()
		return result
	}
	defer os.Chdir(origDir)

	// Change to repo directory
	if err := os.Chdir(repoPath); err != nil {
		result.Status = "failed"
		result.Error = err.Error()
		return result
	}

	// Get repo state
	state, err := git.GetRepoState(repoPath)
	if err != nil {
		result.Status = "failed"
		result.Error = err.Error()
		return result
	}

	result.Name = state.Name
	result.Branch = state.Branch
	result.Remote = &Remote{
		Ahead:  state.Ahead,
		Behind: state.Behind,
		URL:    state.RemoteURL,
	}
	result.Conflicts = state.Conflicts

	// Get merged config for this repo
	cfg := p.ConfigManager.MergeConfig(repoPath)

	// Check protected branch
	result.IsProtected = git.IsProtectedBranch(state.Branch, cfg.ProtectedBranches)

	// Check for conflicts
	if len(state.Conflicts) > 0 && cfg.WarnConflicts {
		result.Operations = append(result.Operations, Operation{
			Type:    "conflict_check",
			Success: false,
			Error:   "merge conflicts detected",
		})
	}

	// Parse changes
	statuses := git.ParseStatus(state.StatusOutput)
	changes := &Changes{Total: len(statuses)}
	for _, s := range statuses {
		switch {
		case s.Code == "??":
			changes.Untracked++
		case s.Code[0] != ' ':
			changes.Staged++
		default:
			changes.Uncommitted++
		}
	}
	result.Changes = changes

	// Status only mode - just return state
	if opts.StatusOnly {
		result.ElapsedMs = time.Since(start).Milliseconds()
		return result
	}

	// Handle pull
	if opts.Pull || opts.PullOnly || cfg.AutoPull {
		// Auto-stash if configured
		var stashed bool
		if cfg.AutoStash && state.ChangesCount > 0 {
			stashResult := git.Stash(repoPath)
			stashed = stashResult.Success
			result.Operations = append(result.Operations, Operation{
				Type:    "stash",
				Success: stashResult.Success,
				Error:   stashResult.Error,
			})
		}

		// Pull
		pullResult := git.Pull(repoPath)
		result.Operations = append(result.Operations, Operation{
			Type:    "pull",
			Success: pullResult.Success,
			Message: pullResult.Output,
			Error:   pullResult.Error,
		})

		// Pop stash if we stashed
		if stashed {
			popResult := git.StashPop(repoPath)
			result.Operations = append(result.Operations, Operation{
				Type:    "stash_pop",
				Success: popResult.Success,
				Error:   popResult.Error,
			})
		}

		// Refresh state after pull
		state, _ = git.GetRepoState(repoPath)
	}

	// Pull only mode - stop here
	if opts.PullOnly {
		result.ElapsedMs = time.Since(start).Milliseconds()
		return result
	}

	// Dry run - don't make changes
	if opts.DryRun {
		result.Operations = append(result.Operations, Operation{
			Type:    "dry_run",
			Success: true,
			Message: "would commit and push",
		})
		result.ElapsedMs = time.Since(start).Milliseconds()
		return result
	}

	// No changes to commit
	if !git.HasChanges(repoPath) {
		result.ElapsedMs = time.Since(start).Milliseconds()
		return result
	}

	// Stage all changes
	addResult := git.AddAll(repoPath)
	result.Operations = append(result.Operations, Operation{
		Type:    "add",
		Success: addResult.Success,
		Error:   addResult.Error,
	})

	if !addResult.Success {
		result.Status = "failed"
		result.Error = addResult.Error
		result.ElapsedMs = time.Since(start).Milliseconds()
		return result
	}

	// Generate commit message
	var commitMsg string
	var isAI bool

	if opts.CommitMessage != "" {
		commitMsg = opts.CommitMessage
	} else if !opts.NoAICommit && cfg.UseAICommit {
		// Get diff for AI
		diff, _ := git.GetDiff(repoPath, true)
		aiResult := ai.GenerateCommitMessage(diff, state.Branch, p.AIConfig)
		if aiResult.Success {
			commitMsg = aiResult.Message
			isAI = true
		} else {
			// Fallback to smart message
			commitMsg = ai.GenerateSmartCommitMessage(state.StatusOutput)
		}
	} else {
		commitMsg = ai.GenerateSmartCommitMessage(state.StatusOutput)
	}

	// Commit
	commitResult := git.Commit(repoPath, commitMsg)
	result.Operations = append(result.Operations, Operation{
		Type:    "commit",
		Success: commitResult.Success,
		Message: commitMsg,
		Error:   commitResult.Error,
	})

	if commitResult.Success {
		result.Commit = &CommitInfo{
			Message: commitMsg,
			IsAI:    isAI,
		}
		// Get commit hash
		if lastCommit, err := git.GetLastCommit(repoPath); err == nil {
			parts := splitN(lastCommit, "|", 4)
			if len(parts) > 0 {
				result.Commit.Hash = parts[0]
			}
		}
	} else {
		result.Status = "failed"
		result.Error = commitResult.Error
		result.ElapsedMs = time.Since(start).Milliseconds()
		return result
	}

	// Push
	if !opts.NoPush && cfg.AutoPush {
		pushResult := git.Push(repoPath)
		result.Operations = append(result.Operations, Operation{
			Type:    "push",
			Success: pushResult.Success,
			Message: pushResult.Output,
			Error:   pushResult.Error,
		})

		if !pushResult.Success {
			result.Status = "failed"
			result.Error = pushResult.Error
		}
	}

	result.ElapsedMs = time.Since(start).Milliseconds()
	return result
}

// ProcessBatch processes multiple repositories
func (p *Processor) ProcessBatch(repos []string, opts Options) *BatchResult {
	start := time.Now()

	result := &BatchResult{
		Operation: "commit",
		Results:   make([]*RepoResult, 0, len(repos)),
	}

	if opts.StatusOnly {
		result.Operation = "status"
	} else if opts.PullOnly {
		result.Operation = "pull"
	}

	for _, repoPath := range repos {
		repoResult := p.ProcessRepo(repoPath, opts)
		result.Results = append(result.Results, repoResult)

		if repoResult.Status == "success" {
			result.ReposSuccess++
		} else {
			result.ReposFailed++
			if repoResult.Error != "" {
				result.Errors = append(result.Errors, repoResult.Error)
			}
		}
	}

	result.ReposTotal = len(repos)
	result.Success = result.ReposFailed == 0
	result.ElapsedMs = time.Since(start).Milliseconds()

	return result
}

// Helper function since strings.SplitN might not be available
func splitN(s, sep string, n int) []string {
	var result []string
	for i := 0; i < n-1; i++ {
		idx := -1
		for j := 0; j < len(s); j++ {
			if j+len(sep) <= len(s) && s[j:j+len(sep)] == sep {
				idx = j
				break
			}
		}
		if idx == -1 {
			break
		}
		result = append(result, s[:idx])
		s = s[idx+len(sep):]
	}
	result = append(result, s)
	return result
}
