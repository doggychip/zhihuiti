"""Shared test fixtures and stubs."""

from __future__ import annotations

import json
from unittest.mock import MagicMock


def make_stub_llm(json_response: dict | list | None = None) -> MagicMock:
    """Create a stub LLM that bypasses the API key check.

    Args:
        json_response: Default JSON response returned by chat_json().
                       Defaults to {"score": 0.75, "reasoning": "ok", "pass": True}.
    """
    if json_response is None:
        json_response = {"score": 0.75, "reasoning": "acceptable output", "pass": True}

    llm = MagicMock()
    llm.chat.return_value = json.dumps(json_response)
    llm.chat_json.return_value = json_response
    return llm
