"""LLM backend using Claude API via OpenRouter with retry and rate limiting."""

from __future__ import annotations

import json
import os
import time

import httpx


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-sonnet-4"

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0   # Exponential backoff: 2s, 4s, 8s
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMError(Exception):
    pass


class LLM:
    """Thin wrapper around OpenRouter's chat completions API with retry."""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise LLMError(
                "Set OPENROUTER_API_KEY environment variable. "
                "Get one at https://openrouter.ai/keys"
            )
        self.model = model
        self.client = httpx.Client(timeout=120)
        self.total_calls = 0
        self.total_retries = 0
        self.total_failures = 0

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request with automatic retry on failure."""
        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            self.total_calls += 1
            try:
                resp = self.client.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
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
                        raise LLMError(f"Unexpected API response: {data}") from e

                if resp.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                    # Check for Retry-After header
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
                raise LLMError(f"OpenRouter API error {resp.status_code}: {resp.text[:500]}")

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
        raise LLMError(f"Failed after {MAX_RETRIES} retries: {last_error}")

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

        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (fences)
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse JSON from LLM: {e}\nRaw: {raw[:500]}")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Rough cost estimate in internal budget units (1 unit ≈ $0.001)."""
        # Approximate: 1 budget unit per 1000 tokens total
        return (input_tokens + output_tokens) / 1000
