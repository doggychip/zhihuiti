from __future__ import annotations

import pytest

from zhihuiti.llm import LLM, LLMError


def _clear_provider_env(monkeypatch):
    for name in (
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_FALLBACK_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "LLM_API_KEY",
        "LLM_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_secondary_deepseek_key_is_reported_as_credential_fallback(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "primary-key")
    monkeypatch.setenv("DEEPSEEK_FALLBACK_API_KEY", "secondary-key")
    llm = LLM()

    status = llm.provider_status()

    assert status["fallback_configured"] is True
    assert status["provider_fallback_configured"] is False
    assert status["credential_fallback_configured"] is True
    assert status["fallback_type"] == "credential"
    llm.client.close()


def test_secondary_deepseek_key_activates_after_two_failures(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "primary-key")
    monkeypatch.setenv("DEEPSEEK_FALLBACK_API_KEY", "secondary-key")
    llm = LLM()
    calls = []

    def request(*_args, api_key, **_kwargs):
        calls.append(api_key)
        if api_key == "primary-key":
            raise LLMError("primary failed")
        return "OK"

    monkeypatch.setattr(llm, "_do_openai_request", request)

    with pytest.raises(LLMError):
        llm.chat("system", "user")
    assert llm.chat("system", "user") == "OK"
    assert calls == ["primary-key", "primary-key", "secondary-key"]
    assert llm.provider_status()["fallback_active"] is True
    llm.client.close()


def test_openrouter_is_preferred_when_both_fallback_types_exist(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "primary-key")
    monkeypatch.setenv("DEEPSEEK_FALLBACK_API_KEY", "secondary-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "provider-key")
    llm = LLM()

    status = llm.provider_status()

    assert status["provider_fallback_configured"] is True
    assert status["credential_fallback_configured"] is True
    assert status["fallback_type"] == "provider"
    llm.client.close()
