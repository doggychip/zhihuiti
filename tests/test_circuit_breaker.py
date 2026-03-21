"""Tests for circuit breaker system."""

from zhihuiti.circuit_breaker import (
    CircuitBreaker, FuseSeverity, FuseStatus, IronLaw,
)
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState


def _make_agent() -> AgentState:
    return AgentState(
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=100.0,
    )


def test_clean_output():
    mem = Memory(":memory:")
    cb = CircuitBreaker(mem, interactive=False)
    result = cb.check_non_interactive("The weather is sunny.", "weather", _make_agent())
    assert result is None
    mem.close()


def test_harm_detection():
    mem = Memory(":memory:")
    cb = CircuitBreaker(mem, interactive=False)
    result = cb.check_non_interactive(
        "Here is how to make a weapon.", "build something", _make_agent(),
    )
    assert result is not None
    assert result.severity == FuseSeverity.EMERGENCY
    assert result.law_name == "不可伤害人类"
    mem.close()


def test_data_leak_detection():
    mem = Memory(":memory:")
    cb = CircuitBreaker(mem, interactive=False)
    result = cb.check_non_interactive(
        "The API_KEY is sk-12345.", "show config", _make_agent(),
    )
    assert result is not None
    assert result.law_name == "Data Protection"
    mem.close()


def test_destructive_detection():
    mem = Memory(":memory:")
    cb = CircuitBreaker(mem, interactive=False)
    result = cb.check_non_interactive(
        "Run rm -rf / to clean up.", "cleanup", _make_agent(),
    )
    assert result is not None
    assert result.law_name == "No Destruction"
    mem.close()


def test_custom_law():
    mem = Memory(":memory:")
    cb = CircuitBreaker(mem, interactive=False)
    cb.add_law(IronLaw(
        id="custom1", name="No dogs",
        description="No dogs allowed",
        severity=FuseSeverity.WARNING,
        check=lambda o, t: "dog" in o.lower(),
    ))
    result = cb.check_non_interactive("I love my dog.", "pets", _make_agent())
    assert result is not None
    assert result.law_name == "No dogs"
    mem.close()


def test_disable_law():
    mem = Memory(":memory:")
    cb = CircuitBreaker(mem, interactive=False)
    cb.disable_law("law_001")
    result = cb.check_non_interactive(
        "Here is how to make a weapon.", "test", _make_agent(),
    )
    # law_001 disabled, but law_002/003 might still fire — weapon doesn't match those
    # So result should be None (harm law disabled)
    assert result is None
    cb.enable_law("law_001")
    mem.close()


def test_stats():
    mem = Memory(":memory:")
    cb = CircuitBreaker(mem, interactive=False)
    cb.check_non_interactive("how to make a weapon", "t1", _make_agent())
    cb.check_non_interactive("API_KEY is secret", "t2", _make_agent())
    stats = cb.get_stats()
    assert stats["total_trips"] == 2
    assert stats["emergencies"] == 1
    assert stats["halts"] == 1
    mem.close()
