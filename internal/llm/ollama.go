package llm

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
)

type generateReq struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

func AskOllama(prompt string) string {
	model := os.Getenv("OLLAMA_MODEL")
	if model == "" {
		model = "mistral"
	}
	base := os.Getenv("OLLAMA_URL")
	if base == "" {
		base = "http://127.0.0.1:11434"
	}

	body, _ := json.Marshal(generateReq{Model: model, Prompt: prompt, Stream: true})
	resp, err := http.Post(base+"/api/generate", "application/json", bytes.NewBuffer(body))
	if err != nil {
		log.Fatal("Failed to connect to Ollama:", err)
	}
	defer resp.Body.Close()

	sc := bufio.NewScanner(resp.Body)
	var b strings.Builder
	for sc.Scan() {
		line := sc.Text()
		var chunk struct {
			Response string `json:"response"`
		}
		if err := json.Unmarshal([]byte(line), &chunk); err == nil {
			fmt.Print(chunk.Response) // stream to console
			b.WriteString(chunk.Response)
		}
	}
	fmt.Println()
	return b.String()
}
