"""LLM backend — supports Ollama (local, default) and OpenRouter (cloud).

Backend selection:
  - If OPENROUTER_API_KEY is set, uses OpenRouter (cloud).
  - Otherwise, uses Ollama at localhost:11434 (no key required).

Environment variables:
  OPENROUTER_API_KEY   — use OpenRouter; value is the API key
  OLLAMA_HOST          — Ollama base URL (default: http://localhost:11434)
  OLLAMA_MODEL         — Ollama model name (default: llama3)
  LLM_MODEL            — override model for whichever backend is active
"""

from __future__ import annotations

import json
import os
import time

import httpx


# ---------------------------------------------------------------------------
# Backend constants
# ---------------------------------------------------------------------------

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = "anthropic/claude-sonnet-4"

OLLAMA_DEFAULT_HOST = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3"

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMError(Exception):
    pass


class LLM:
    """LLM wrapper that auto-selects Ollama (local) or OpenRouter (cloud).

    Priority:
      1. OPENROUTER_API_KEY set → OpenRouter
      2. Otherwise             → Ollama (no key needed)

    Override the model with LLM_MODEL env var or the ``model`` constructor arg.
    """

    def __init__(self, model: str | None = None):
        self._api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self._use_ollama = not self._api_key

        if self._use_ollama:
            self._ollama_host = os.environ.get("OLLAMA_HOST", OLLAMA_DEFAULT_HOST).rstrip("/")
            default_model = os.environ.get("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
        else:
            default_model = OPENROUTER_DEFAULT_MODEL

        self.model = model or os.environ.get("LLM_MODEL", default_model)
        self.client = httpx.Client(timeout=300)  # Ollama can be slow on first load
        self.total_calls = 0
        self.total_retries = 0
        self.total_failures = 0

        backend = f"Ollama ({self._ollama_host}, {self.model})" if self._use_ollama \
            else f"OpenRouter ({self.model})"
        # Lazy import to avoid circular
        try:
            from rich.console import Console
            Console().print(f"  [dim]LLM backend: {backend}[/dim]")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request with automatic retry on failure."""
        if self._use_ollama:
            return self._chat_ollama(system, user, temperature, max_tokens)
        return self._chat_openrouter(system, user, temperature, max_tokens)

    def chat_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.5,
        max_tokens: int = 4096,
    ) -> dict | list:
        """Chat and parse the response as JSON."""
        system_with_json = (
            system + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "No markdown, no explanation, just the JSON object/array."
        )
        raw = self.chat(system_with_json, user, temperature, max_tokens)

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse JSON from LLM: {e}\nRaw: {raw[:500]}")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Budget units consumed (1 unit ≈ $0.001 for cloud; 0 for local)."""
        if self._use_ollama:
            return 0.0
        return (input_tokens + output_tokens) / 1000

    # ------------------------------------------------------------------
    # Ollama backend
    # ------------------------------------------------------------------

    def _chat_ollama(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self._ollama_host}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        last_error: str | None = None
        for attempt in range(MAX_RETRIES + 1):
            self.total_calls += 1
            try:
                resp = self.client.post(url, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        return data["message"]["content"]
                    except (KeyError, TypeError) as e:
                        raise LLMError(f"Unexpected Ollama response: {data}") from e

                if resp.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                    self.total_retries += 1
                    time.sleep(RETRY_BACKOFF_BASE ** (attempt + 1))
                    continue

                self.total_failures += 1
                raise LLMError(f"Ollama error {resp.status_code}: {resp.text[:500]}")

            except httpx.ConnectError:
                last_error = f"Cannot connect to Ollama at {self._ollama_host}. Is it running? (ollama serve)"
                if attempt < MAX_RETRIES:
                    self.total_retries += 1
                    time.sleep(RETRY_BACKOFF_BASE ** (attempt + 1))
                    continue
            except httpx.TimeoutException:
                last_error = "Ollama request timed out (model may still be loading)"
                if attempt < MAX_RETRIES:
                    self.total_retries += 1
                    time.sleep(RETRY_BACKOFF_BASE ** (attempt + 1))
                    continue

        self.total_failures += 1
        raise LLMError(f"Ollama failed after {MAX_RETRIES} retries: {last_error}")

    # ------------------------------------------------------------------
    # OpenRouter backend
    # ------------------------------------------------------------------

    def _chat_openrouter(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        last_error: str | None = None

        for attempt in range(MAX_RETRIES + 1):
            self.total_calls += 1
            try:
                resp = self.client.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/zhihuiti",
                        "X-Title": "zhihuiti",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )

                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        return data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError) as e:
                        raise LLMError(f"Unexpected OpenRouter response: {data}") from e

                if resp.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                    retry_after = resp.headers.get("retry-after")
                    if retry_after:
                        try:
                            wait = max(wait, float(retry_after))
                        except ValueError:
                            pass
                    self.total_retries += 1
                    time.sleep(wait)
                    continue

                self.total_failures += 1
                raise LLMError(f"OpenRouter error {resp.status_code}: {resp.text[:500]}")

            except httpx.TimeoutException:
                last_error = "Request timed out"
                if attempt < MAX_RETRIES:
                    self.total_retries += 1
                    time.sleep(RETRY_BACKOFF_BASE ** (attempt + 1))
                    continue
            except httpx.ConnectError:
                last_error = "Connection failed"
                if attempt < MAX_RETRIES:
                    self.total_retries += 1
                    time.sleep(RETRY_BACKOFF_BASE ** (attempt + 1))
                    continue

        self.total_failures += 1
        raise LLMError(f"OpenRouter failed after {MAX_RETRIES} retries: {last_error}")
