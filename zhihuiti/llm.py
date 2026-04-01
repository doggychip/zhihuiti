"""LLM backend — supports Ollama (local), DeepSeek, OpenRouter, and any OpenAI-compatible API.

Backend selection (first match wins):
  1. DEEPSEEK_API_KEY   → DeepSeek (https://api.deepseek.com)
  2. OPENROUTER_API_KEY → OpenRouter (https://openrouter.ai)
  3. OPENAI_API_KEY     → OpenAI (https://api.openai.com)
  4. LLM_API_KEY + LLM_API_URL → Any OpenAI-compatible API
  5. Otherwise          → Ollama at localhost:11434 (no key required)

Environment variables:
  DEEPSEEK_API_KEY     — use DeepSeek API
  OPENROUTER_API_KEY   — use OpenRouter
  OPENAI_API_KEY       — use OpenAI
  LLM_API_KEY          — generic API key (requires LLM_API_URL)
  LLM_API_URL          — custom API endpoint (OpenAI-compatible)
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

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_PREMIUM_MODEL = "deepseek-reasoner"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = "anthropic/claude-sonnet-4"
OPENROUTER_PREMIUM_MODEL = "anthropic/claude-opus-4"

OLLAMA_DEFAULT_HOST = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3"
OLLAMA_PREMIUM_MODEL = "llama3.1"

# Retry configuration
MAX_RETRIES = 5
RETRY_BACKOFF_BASE = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMError(Exception):
    pass


class LLM:
    """LLM wrapper that auto-selects DeepSeek, OpenRouter, or Ollama.

    Priority:
      1. DEEPSEEK_API_KEY set   → DeepSeek API
      2. OPENROUTER_API_KEY set → OpenRouter
      3. Otherwise              → Ollama (no key needed)

    Override the model with LLM_MODEL env var or the ``model`` constructor arg.
    """

    def __init__(self, model: str | None = None):
        self._deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self._openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        self._generic_key = os.environ.get("LLM_API_KEY", "")
        self._generic_url = os.environ.get("LLM_BASE_URL", "")

        # Backend selection: DeepSeek > OpenRouter > Generic OpenAI-compat > Ollama
        if self._deepseek_key:
            self._backend = "deepseek"
            self._api_key = self._deepseek_key
            self._api_url = DEEPSEEK_URL
            default_model = DEEPSEEK_DEFAULT_MODEL
            default_premium = DEEPSEEK_PREMIUM_MODEL
        elif self._openrouter_key:
            self._backend = "openrouter"
            self._api_key = self._openrouter_key
            self._api_url = OPENROUTER_URL
            default_model = OPENROUTER_DEFAULT_MODEL
            default_premium = OPENROUTER_PREMIUM_MODEL
        elif self._generic_key and self._generic_url:
            self._backend = "generic"
            self._api_key = self._generic_key
            # Normalize: append /chat/completions if base URL doesn't already have a path
            base = self._generic_url.rstrip("/")
            if not base.endswith("/chat/completions"):
                base = base + "/chat/completions"
            self._api_url = base
            default_model = "deepseek-chat"
            default_premium = "deepseek-chat"
        else:
            self._backend = "ollama"
            self._api_key = ""
            self._api_url = ""
            self._ollama_host = os.environ.get("OLLAMA_HOST", OLLAMA_DEFAULT_HOST).rstrip("/")
            default_model = os.environ.get("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
            default_premium = OLLAMA_PREMIUM_MODEL

        self.model = model or os.environ.get("LLM_MODEL", default_model)
        self.premium_model = os.environ.get("LLM_PREMIUM_MODEL", default_premium)
        self.client = httpx.Client(timeout=300)
        self.total_calls = 0
        self.total_retries = 0
        self.total_failures = 0

        if self._backend == "ollama":
            backend = f"Ollama ({self._ollama_host}, {self.model})"
        elif self._backend == "deepseek":
            backend = f"DeepSeek ({self.model})"
        elif self._backend == "generic":
            backend = f"Generic ({self._generic_url}, {self.model})"
        else:
            backend = f"OpenRouter ({self.model})"
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
        model: str | None = None,
    ) -> str:
        """Send a chat completion request with automatic retry on failure.

        model: optional per-call override; falls back to self.model.
        """
        if self._backend == "ollama":
            return self._chat_ollama(system, user, temperature, max_tokens, model=model)
        # DeepSeek and OpenRouter both use OpenAI-compatible format
        return self._chat_openai_compat(system, user, temperature, max_tokens, model=model)

    def chat_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.5,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> dict | list:
        """Chat and parse the response as JSON."""
        system_with_json = (
            system + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "No markdown, no explanation, just the JSON object/array."
        )
        raw = self.chat(system_with_json, user, temperature, max_tokens, model=model)

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
        if self._backend == "ollama":
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
        model: str | None = None,
    ) -> str:
        url = f"{self._ollama_host}/api/chat"
        payload = {
            "model": model or self.model,
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

    def _chat_openai_compat(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> str:
        """OpenAI-compatible chat endpoint — works with DeepSeek, OpenRouter, OpenAI."""
        last_error: str | None = None

        for attempt in range(MAX_RETRIES + 1):
            self.total_calls += 1
            try:
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                # OpenRouter-specific headers
                if self._backend == "openrouter":
                    headers["HTTP-Referer"] = "https://github.com/zhihuiti"
                    headers["X-Title"] = "zhihuiti"

                resp = self.client.post(
                    self._api_url,
                    headers=headers,
                    json={
                        "model": model or self.model,
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
                raise LLMError(f"{self._backend} error {resp.status_code}: {resp.text[:500]}")

            except (httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
                last_error = str(exc)
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
        raise LLMError(f"{self._backend} failed after {MAX_RETRIES} retries: {last_error}")
