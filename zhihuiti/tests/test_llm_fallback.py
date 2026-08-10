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


def test_openai_is_used_as_provider_fallback_when_openrouter_is_absent(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "primary-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    llm = LLM()

    status = llm.provider_status()

    assert status["provider"] == "deepseek"
    assert status["provider_fallback_configured"] is True
    assert llm._fallback_backend == "openai"
    assert llm._effective_fallback_model == "gpt-4o-mini"
    llm.client.close()


def test_openai_is_selected_when_it_is_the_only_cloud_provider(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    llm = LLM()

    status = llm.provider_status()

    assert status["provider"] == "openai"
    assert status["model"] == "gpt-4o-mini"
    llm.client.close()


def test_provider_status_reports_observed_calls_without_secrets(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-value")
    llm = LLM()

    initial = llm.provider_status()
    assert initial["live_call_observed"] is False
    assert initial["ready"] is None

    monkeypatch.setattr(llm, "_chat_openai_compat", lambda *_args, **_kwargs: "OK")
    assert llm.chat("system", "user") == "OK"
    observed = llm.provider_status()

    assert observed["live_call_observed"] is True
    assert observed["ready"] is True
    assert observed["last_success_at"] is not None
    assert observed["last_latency_ms"] >= 0
    assert "secret-value" not in str(observed)
    llm.client.close()


def test_provider_status_records_secret_free_failure_type(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-value")
    llm = LLM()

    def fail(*_args, **_kwargs):
        raise LLMError("provider rejected secret-value")

    monkeypatch.setattr(llm, "_chat_openai_compat", fail)
    with pytest.raises(LLMError):
        llm.chat("system", "user")
    status = llm.provider_status()

    assert status["ready"] is False
    assert status["last_error_type"] == "LLMError"
    assert status["last_error_at"] is not None
    assert "secret-value" not in str(status)
    llm.client.close()


def test_provider_status_classifies_insufficient_balance_without_response_body(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-value")
    llm = LLM()

    def fail(*_args, **_kwargs):
        raise LLMError("DeepSeek error 402: Insufficient Balance")

    monkeypatch.setattr(llm, "_chat_openai_compat", fail)
    with pytest.raises(LLMError):
        llm.chat("system", "user")

    status = llm.provider_status()
    assert status["last_error_category"] == "insufficient_balance"
    assert status["action_required"] == "Add provider credit before agent work can resume."
    assert "Insufficient Balance" not in str(status)
    assert "secret-value" not in str(status)
    llm.client.close()


def test_failed_probe_returns_current_safe_error_category(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-value")
    llm = LLM()
    monkeypatch.setattr(
        llm,
        "_chat_openai_compat",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            LLMError("DeepSeek error 402: Insufficient Balance")
        ),
    )

    status = llm.probe_provider()

    assert status["ready"] is False
    assert status["last_error_category"] == "insufficient_balance"
    assert status["action_required"] == "Add provider credit before agent work can resume."
    llm.client.close()
