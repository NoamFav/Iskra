// Package ai provides AI-powered commit message generation.
// Supports Ollama, OpenAI, and Claude providers.
package ai

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

// Config holds AI provider configuration
type Config struct {
	Provider    string `json:"provider"`
	OpenAIKey   string `json:"openai_api_key,omitempty"`
	OpenAIModel string `json:"openai_model"`
	ClaudeKey   string `json:"claude_api_key,omitempty"`
	ClaudeModel string `json:"claude_model"`
	OllamaURL   string `json:"ollama_url"`
	OllamaModel string `json:"ollama_model"`
}

// Result holds the result of AI generation
type Result struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Error   string `json:"error,omitempty"`
}

const commitPrompt = `You are a commit message generator. Generate a concise, conventional commit message for the following git diff.

Rules:
1. Use conventional commits format: type(scope): description
2. Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
3. Keep the first line under 72 characters
4. Be specific but concise
5. Focus on WHAT changed and WHY, not HOW
6. Output ONLY the commit message, nothing else

Branch: %s

Diff:
%s

Commit message:`

// GenerateCommitMessage generates a commit message using the configured AI provider
func GenerateCommitMessage(diff, branch string, cfg Config) Result {
	if diff == "" {
		return Result{Success: false, Error: "no diff provided"}
	}

	// Truncate diff if too long
	maxDiffLen := 8000
	if len(diff) > maxDiffLen {
		diff = diff[:maxDiffLen] + "\n... (truncated)"
	}

	prompt := fmt.Sprintf(commitPrompt, branch, diff)

	switch strings.ToLower(cfg.Provider) {
	case "ollama":
		return generateWithOllama(prompt, cfg)
	case "openai":
		return generateWithOpenAI(prompt, cfg)
	case "claude":
		return generateWithClaude(prompt, cfg)
	default:
		return generateWithOllama(prompt, cfg) // Default to Ollama
	}
}

// Ollama types
type ollamaRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

type ollamaResponse struct {
	Response string `json:"response"`
	Done     bool   `json:"done"`
}

func generateWithOllama(prompt string, cfg Config) Result {
	url := cfg.OllamaURL
	if url == "" {
		url = os.Getenv("OLLAMA_URL")
	}
	if url == "" {
		url = "http://127.0.0.1:11434"
	}

	model := cfg.OllamaModel
	if model == "" {
		model = os.Getenv("OLLAMA_MODEL")
	}
	if model == "" {
		model = "gemma"
	}

	reqBody := ollamaRequest{
		Model:  model,
		Prompt: prompt,
		Stream: false,
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return Result{Success: false, Error: err.Error()}
	}

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Post(url+"/api/generate", "application/json", bytes.NewReader(body))
	if err != nil {
		return Result{Success: false, Error: fmt.Sprintf("ollama request failed: %v", err)}
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return Result{Success: false, Error: fmt.Sprintf("ollama returned %d: %s", resp.StatusCode, string(respBody))}
	}

	var ollamaResp ollamaResponse
	if err := json.NewDecoder(resp.Body).Decode(&ollamaResp); err != nil {
		return Result{Success: false, Error: err.Error()}
	}

	message := cleanCommitMessage(ollamaResp.Response)
	if message == "" {
		return Result{Success: false, Error: "empty response from ollama"}
	}

	return Result{Success: true, Message: message}
}

// OpenAI types
type openAIRequest struct {
	Model    string          `json:"model"`
	Messages []openAIMessage `json:"messages"`
}

type openAIMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type openAIResponse struct {
	Choices []struct {
		Message openAIMessage `json:"message"`
	} `json:"choices"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

func generateWithOpenAI(prompt string, cfg Config) Result {
	apiKey := cfg.OpenAIKey
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
	}
	if apiKey == "" {
		return Result{Success: false, Error: "OpenAI API key not configured"}
	}

	model := cfg.OpenAIModel
	if model == "" {
		model = "gpt-4o-mini"
	}

	reqBody := openAIRequest{
		Model: model,
		Messages: []openAIMessage{
			{Role: "user", Content: prompt},
		},
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return Result{Success: false, Error: err.Error()}
	}

	req, err := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewReader(body))
	if err != nil {
		return Result{Success: false, Error: err.Error()}
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return Result{Success: false, Error: fmt.Sprintf("openai request failed: %v", err)}
	}
	defer resp.Body.Close()

	var openAIResp openAIResponse
	if err := json.NewDecoder(resp.Body).Decode(&openAIResp); err != nil {
		return Result{Success: false, Error: err.Error()}
	}

	if openAIResp.Error != nil {
		return Result{Success: false, Error: openAIResp.Error.Message}
	}

	if len(openAIResp.Choices) == 0 {
		return Result{Success: false, Error: "no response from openai"}
	}

	message := cleanCommitMessage(openAIResp.Choices[0].Message.Content)
	return Result{Success: true, Message: message}
}

// Claude types
type claudeRequest struct {
	Model     string          `json:"model"`
	MaxTokens int             `json:"max_tokens"`
	Messages  []claudeMessage `json:"messages"`
}

type claudeMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type claudeResponse struct {
	Content []struct {
		Text string `json:"text"`
	} `json:"content"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

func generateWithClaude(prompt string, cfg Config) Result {
	apiKey := cfg.ClaudeKey
	if apiKey == "" {
		apiKey = os.Getenv("ANTHROPIC_API_KEY")
	}
	if apiKey == "" {
		return Result{Success: false, Error: "Claude API key not configured"}
	}

	model := cfg.ClaudeModel
	if model == "" {
		model = "claude-sonnet-4-6"
	}

	reqBody := claudeRequest{
		Model:     model,
		MaxTokens: 256,
		Messages: []claudeMessage{
			{Role: "user", Content: prompt},
		},
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return Result{Success: false, Error: err.Error()}
	}

	req, err := http.NewRequest("POST", "https://api.anthropic.com/v1/messages", bytes.NewReader(body))
	if err != nil {
		return Result{Success: false, Error: err.Error()}
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", apiKey)
	req.Header.Set("anthropic-version", "2023-06-01")

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return Result{Success: false, Error: fmt.Sprintf("claude request failed: %v", err)}
	}
	defer resp.Body.Close()

	var claudeResp claudeResponse
	if err := json.NewDecoder(resp.Body).Decode(&claudeResp); err != nil {
		return Result{Success: false, Error: err.Error()}
	}

	if claudeResp.Error != nil {
		return Result{Success: false, Error: claudeResp.Error.Message}
	}

	if len(claudeResp.Content) == 0 {
		return Result{Success: false, Error: "no response from claude"}
	}

	message := cleanCommitMessage(claudeResp.Content[0].Text)
	return Result{Success: true, Message: message}
}

// cleanCommitMessage cleans up the AI response
func cleanCommitMessage(msg string) string {
	msg = strings.TrimSpace(msg)

	// Remove markdown code blocks
	msg = strings.TrimPrefix(msg, "```")
	msg = strings.TrimSuffix(msg, "```")
	msg = strings.TrimSpace(msg)

	// Remove quotes
	msg = strings.Trim(msg, "\"'`")

	// Take only the first line for the commit subject
	lines := strings.Split(msg, "\n")
	if len(lines) > 0 {
		msg = strings.TrimSpace(lines[0])
	}

	// Ensure it's not too long
	if len(msg) > 100 {
		msg = msg[:97] + "..."
	}

	return msg
}

// GenerateSmartCommitMessage generates a commit message based on file analysis
// Used as fallback when AI fails
func GenerateSmartCommitMessage(statusOutput string) string {
	if statusOutput == "" {
		return "chore: update files"
	}

	lines := strings.Split(strings.TrimSpace(statusOutput), "\n")

	var added, modified, deleted int
	var hasTests, hasDocs, hasConfig, hasDeps bool
	var mainFile string

	for _, line := range lines {
		if len(line) < 4 {
			continue
		}

		status := strings.TrimSpace(line[:2])
		file := strings.TrimSpace(line[3:])
		fileLower := strings.ToLower(file)

		// Count by status
		switch {
		case strings.Contains(status, "A") || status == "??":
			added++
		case strings.Contains(status, "M"):
			modified++
		case strings.Contains(status, "D"):
			deleted++
		}

		// Detect file types
		if strings.Contains(fileLower, "test") || strings.Contains(fileLower, "spec") {
			hasTests = true
		}
		if strings.HasSuffix(fileLower, ".md") || strings.Contains(fileLower, "doc") {
			hasDocs = true
		}
		if strings.Contains(fileLower, "config") || strings.HasSuffix(fileLower, ".yaml") ||
			strings.HasSuffix(fileLower, ".yml") || strings.HasSuffix(fileLower, ".json") ||
			strings.HasSuffix(fileLower, ".toml") {
			hasConfig = true
		}
		if strings.Contains(fileLower, "requirements") || strings.Contains(fileLower, "package.json") ||
			strings.Contains(fileLower, "go.mod") || strings.Contains(fileLower, "cargo.toml") {
			hasDeps = true
		}

		// Track main file for specific messages
		if mainFile == "" && !strings.HasPrefix(file, ".") {
			mainFile = file
		}
	}

	// Generate message based on analysis
	switch {
	case hasTests:
		return "test: update tests"
	case hasDocs:
		return "docs: update documentation"
	case hasDeps:
		return "chore: update dependencies"
	case hasConfig:
		return "chore: update configuration"
	case added > 0 && modified == 0 && deleted == 0:
		if mainFile != "" {
			return fmt.Sprintf("feat: add %s", mainFile)
		}
		return "feat: add new files"
	case deleted > 0 && added == 0 && modified == 0:
		return "chore: remove unused files"
	case modified > 0:
		if mainFile != "" {
			return fmt.Sprintf("refactor: update %s", mainFile)
		}
		return "refactor: update files"
	default:
		return "chore: update files"
	}
}
