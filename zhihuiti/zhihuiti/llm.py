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
  LLM_FALLBACK_MODEL   — model to use on OpenRouter fallback (default: anthropic/claude-sonnet-4)

Fallback behavior (DeepSeek → OpenRouter):
  When DEEPSEEK_API_KEY is the primary and OPENROUTER_API_KEY is also set,
  3 consecutive DeepSeek failures trigger automatic failover to OpenRouter.
  Every 10 minutes, a probe request checks if DeepSeek has recovered.
  All provider switches are logged to stderr.
"""

from __future__ import annotations

import json
import os
import sys
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
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Fallback configuration
FALLBACK_CONSECUTIVE_FAILURES = 2
FALLBACK_RECOVERY_CHECK_SECONDS = 600  # 10 minutes


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
        self._fallback_model = os.environ.get("LLM_FALLBACK_MODEL", OPENROUTER_DEFAULT_MODEL)

        # Backend selection: DeepSeek > OpenRouter > Ollama
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

        # Fallback state: only applies when primary is DeepSeek and OpenRouter key exists
        self._primary_backend = self._backend
        self._primary_api_key = self._api_key
        self._primary_api_url = self._api_url
        self._primary_model = self.model
        self._fallback_available = (self._backend == "deepseek" and bool(self._openrouter_key))
        self._consecutive_failures = 0
        self._using_fallback = False
        self._fallback_activated_at: float = 0.0

        if self._backend == "ollama":
            backend = f"Ollama ({self._ollama_host}, {self.model})"
        elif self._backend == "deepseek":
            backend = f"DeepSeek ({self.model})"
        else:
            backend = f"OpenRouter ({self.model})"
        # Lazy import to avoid circular
        try:
            from rich.console import Console
            Console().print(f"  [dim]LLM backend: {backend}[/dim]")
            if self._fallback_available:
                Console().print(f"  [dim]LLM fallback: OpenRouter ({self._fallback_model})[/dim]")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Fallback management
    # ------------------------------------------------------------------

    def _switch_to_fallback(self) -> None:
        """Switch from DeepSeek to OpenRouter fallback."""
        self._using_fallback = True
        self._fallback_activated_at = time.monotonic()
        self._backend = "openrouter"
        self._api_key = self._openrouter_key
        self._api_url = OPENROUTER_URL
        self.model = self._fallback_model
        print(
            f"[LLM FALLBACK] Switching to OpenRouter ({self._fallback_model}) "
            f"after {FALLBACK_CONSECUTIVE_FAILURES} consecutive DeepSeek failures",
            file=sys.stderr,
        )

    def _switch_to_primary(self) -> None:
        """Switch back from OpenRouter fallback to DeepSeek."""
        self._using_fallback = False
        self._consecutive_failures = 0
        self._fallback_activated_at = 0.0
        self._backend = self._primary_backend
        self._api_key = self._primary_api_key
        self._api_url = self._primary_api_url
        self.model = self._primary_model
        print(
            "[LLM FALLBACK] DeepSeek recovered, switching back to primary",
            file=sys.stderr,
        )

    def _maybe_check_primary_recovery(self) -> bool:
        """If using fallback and enough time passed, try one call to primary.

        Returns True if the caller should attempt the primary provider.
        """
        if not self._using_fallback:
            return False
        elapsed = time.monotonic() - self._fallback_activated_at
        return elapsed >= FALLBACK_RECOVERY_CHECK_SECONDS

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
        # Check if we should try switching back to primary
        if self._fallback_available and self._maybe_check_primary_recovery():
            try:
                result = self._do_openai_request(
                    system, user, temperature, max_tokens,
                    api_url=self._primary_api_url,
                    api_key=self._primary_api_key,
                    backend=self._primary_backend,
                    model=model or self._primary_model,
                )
                # Primary recovered
                self._switch_to_primary()
                return result
            except LLMError:
                # Primary still down, reset timer and continue with fallback
                self._fallback_activated_at = time.monotonic()
                print(
                    "[LLM FALLBACK] DeepSeek still unavailable, staying on OpenRouter",
                    file=sys.stderr,
                )

        try:
            result = self._do_openai_request(
                system, user, temperature, max_tokens,
                api_url=self._api_url,
                api_key=self._api_key,
                backend=self._backend,
                model=model or self.model,
            )
            # Success on current provider — reset consecutive failure count
            if not self._using_fallback:
                self._consecutive_failures = 0
            return result
        except LLMError:
            if self._fallback_available and not self._using_fallback:
                self._consecutive_failures += 1
                if self._consecutive_failures >= FALLBACK_CONSECUTIVE_FAILURES:
                    self._switch_to_fallback()
                    # Retry immediately on fallback
                    return self._do_openai_request(
                        system, user, temperature, max_tokens,
                        api_url=self._api_url,
                        api_key=self._api_key,
                        backend=self._backend,
                        model=model or self.model,
                    )
            raise

    def _do_openai_request(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        *,
        api_url: str,
        api_key: str,
        backend: str,
        model: str,
    ) -> str:
        """Single OpenAI-compatible request with retries."""
        last_error: str | None = None

        for attempt in range(MAX_RETRIES + 1):
            self.total_calls += 1
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                # OpenRouter-specific headers
                if backend == "openrouter":
                    headers["HTTP-Referer"] = "https://github.com/zhihuiti"
                    headers["X-Title"] = "zhihuiti"

                resp = self.client.post(
                    api_url,
                    headers=headers,
                    json={
                        "model": model,
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
                        content = data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError) as e:
                        raise LLMError(f"Unexpected {backend} response: {data}") from e
                    print(
                        f"[LLM] {backend} ({model}) — call #{self.total_calls} OK",
                        file=sys.stderr,
                    )
                    return content

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
                raise LLMError(f"{backend} error {resp.status_code}: {resp.text[:500]}")

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
        raise LLMError(f"{backend} failed after {MAX_RETRIES} retries: {last_error}")
