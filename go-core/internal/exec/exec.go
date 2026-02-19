// Package exec runs commands across multiple repositories.
package exec

import (
	"bytes"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// Result holds the result of executing a command in a repo
type Result struct {
	Path     string `json:"path"`
	Name     string `json:"name"`
	Success  bool   `json:"success"`
	ExitCode int    `json:"exit_code"`
	Stdout   string `json:"stdout"`
	Stderr   string `json:"stderr"`
	Duration int64  `json:"duration_ms"`
	Error    string `json:"error,omitempty"`
}

// BatchResult holds results for all repos
type BatchResult struct {
	Command     string    `json:"command"`
	ReposTotal  int       `json:"repos_total"`
	ReposSuccess int      `json:"repos_success"`
	ReposFailed  int      `json:"repos_failed"`
	Results     []*Result `json:"results"`
	Duration    int64     `json:"duration_ms"`
}

// Options for execution
type Options struct {
	Parallel  int  // Number of parallel workers (0 = sequential)
	FailFast  bool // Stop on first error
	Quiet     bool // Suppress output
}

// Run executes a command in a single repository
func Run(repoPath, command string) *Result {
	start := time.Now()

	result := &Result{
		Path: repoPath,
		Name: repoBaseName(repoPath),
	}

	// Change to repo directory
	origDir, err := os.Getwd()
	if err != nil {
		result.Error = err.Error()
		return result
	}

	if err := os.Chdir(repoPath); err != nil {
		result.Error = err.Error()
		os.Chdir(origDir)
		return result
	}
	defer os.Chdir(origDir)

	// Execute command
	cmd := exec.Command("sh", "-c", command)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()

	result.Stdout = strings.TrimSpace(stdout.String())
	result.Stderr = strings.TrimSpace(stderr.String())
	result.Duration = time.Since(start).Milliseconds()

	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			result.ExitCode = exitErr.ExitCode()
		} else {
			result.ExitCode = 1
			result.Error = err.Error()
		}
		result.Success = false
	} else {
		result.Success = true
		result.ExitCode = 0
	}

	return result
}

// RunBatch executes a command across multiple repositories
func RunBatch(repos []string, command string, opts Options) *BatchResult {
	start := time.Now()

	result := &BatchResult{
		Command:    command,
		ReposTotal: len(repos),
		Results:    make([]*Result, 0, len(repos)),
	}

	if opts.Parallel > 1 {
		result.Results = runParallel(repos, command, opts)
	} else {
		result.Results = runSequential(repos, command, opts)
	}

	for _, r := range result.Results {
		if r.Success {
			result.ReposSuccess++
		} else {
			result.ReposFailed++
		}
	}

	result.Duration = time.Since(start).Milliseconds()
	return result
}

func runSequential(repos []string, command string, opts Options) []*Result {
	var results []*Result

	for _, repo := range repos {
		r := Run(repo, command)
		results = append(results, r)

		if opts.FailFast && !r.Success {
			break
		}
	}

	return results
}

func runParallel(repos []string, command string, opts Options) []*Result {
	results := make([]*Result, len(repos))
	var wg sync.WaitGroup
	var mu sync.Mutex
	var failed bool

	// Semaphore for limiting concurrency
	sem := make(chan struct{}, opts.Parallel)

	for i, repo := range repos {
		if opts.FailFast {
			mu.Lock()
			if failed {
				mu.Unlock()
				break
			}
			mu.Unlock()
		}

		wg.Add(1)
		go func(idx int, repoPath string) {
			defer wg.Done()

			sem <- struct{}{}        // Acquire
			defer func() { <-sem }() // Release

			r := Run(repoPath, command)

			mu.Lock()
			results[idx] = r
			if !r.Success {
				failed = true
			}
			mu.Unlock()
		}(i, repo)
	}

	wg.Wait()

	// Filter out nil results (from early exit)
	var filtered []*Result
	for _, r := range results {
		if r != nil {
			filtered = append(filtered, r)
		}
	}

	return filtered
}

func repoBaseName(path string) string {
	// Get last component of path
	parts := strings.Split(path, "/")
	if len(parts) > 0 {
		return parts[len(parts)-1]
	}
	return path
}
