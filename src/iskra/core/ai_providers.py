"""
AI provider integrations. Let the robots write your commits.

Supports:
- Ollama (local, free, private, the way god intended)
- OpenAI (pay money, get GPT)
- Claude (pay money, get different GPT)

All of them take a diff and spit out a commit message.
Or fail. They fail sometimes. That's life.
"""

import os
import json
import subprocess
from typing import Optional
from dataclasses import dataclass


@dataclass
class AIConfig:
    """Config for AI stuff. Provider + API keys + model choices."""

    provider: str = "ollama"  # ollama, openai, claude
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-20250514"


def generate_commit_with_ollama(diff: str, branch: str) -> Optional[str]:
    """
    Use local Ollama via ai_commit binary.
    Returns None because ai_commit does the commit itself.
    It's weird but it works.
    """
    try:
        result = subprocess.run(
            ["ai_commit", "auto-commit"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return None  # ai_commit handles commit
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def generate_commit_with_openai(
    diff: str,
    branch: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> Optional[str]:
    """
    Hit the OpenAI API for a commit message.
    Truncates diff to 2000 chars because tokens cost money.
    No sdk import because i refuse to add dependencies.
    """
    try:
        import urllib.request  # yes we're doing raw urllib deal with it

        prompt = f"""Generate a conventional commit message for these changes.
Format: <type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
Use imperative mood. No period at the end. Only output the commit message line.

Branch: {branch}
Changes:
{diff[:2000]}"""

        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": 0.3,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            message = result["choices"][0]["message"]["content"].strip()
            return message.split("\n")[0].strip()

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None


def generate_commit_with_claude(
    diff: str,
    branch: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> Optional[str]:
    """
    Hit the Anthropic API for a commit message.
    Same deal as OpenAI but different endpoint and headers.
    Copy paste engineering at its finest.
    """
    try:
        import urllib.request

        prompt = f"""Generate a conventional commit message for these changes.
Format: <type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
Use imperative mood. No period at the end. Only output the commit message line.

Branch: {branch}
Changes:
{diff[:2000]}"""

        data = json.dumps({
            "model": model,
            "max_tokens": 100,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            message = result["content"][0]["text"].strip()
            return message.split("\n")[0].strip()

    except Exception as e:
        print(f"Claude API error: {e}")
        return None


def generate_commit_message_with_ai(
    diff: str,
    branch: str,
    config: AIConfig,
) -> Optional[str]:
    """
    Main entry point. Routes to the right provider.
    Falls back to env vars for API keys.
    If everything fails, returns None and we deal with it upstream.
    """
    provider = config.provider.lower()

    if provider == "openai":
        api_key = config.openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("OpenAI API key not configured")
            return None
        return generate_commit_with_openai(diff, branch, api_key, config.openai_model)

    elif provider == "claude":
        api_key = config.claude_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Claude API key not configured")
            return None
        return generate_commit_with_claude(diff, branch, api_key, config.claude_model)

    # default to ollama (handled by ai_commit binary)
    return None
