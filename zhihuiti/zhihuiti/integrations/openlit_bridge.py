"""OpenLIT Bridge — GPU monitoring, prompt management, and guardrails.

Wraps OpenLIT (https://github.com/openlit/openlit) for infrastructure
observability, prompt versioning, and content safety guardrails.

Integration points:
  - On startup: init_monitoring() auto-instruments LLM calls
  - Prompt management: version and retrieve prompt templates
  - Guardrails: check agent output before delivery
  - GPU stats: monitor hardware utilization
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OpenLITBridge:
    """Bridge to OpenLIT for GPU monitoring, prompt vault, and guardrails."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key
        self._available: bool | None = None
        self._monitoring_active = False

    def is_available(self) -> bool:
        """Check if OpenLIT is installed and accessible."""
        if self._available is not None:
            return self._available
        try:
            import openlit  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def init_monitoring(self) -> None:
        """Initialize OpenLIT auto-instrumentation for LLM calls.

        Automatically patches supported LLM client libraries (OpenAI,
        Anthropic, etc.) to emit traces and metrics. Safe to call
        multiple times; subsequent calls are no-ops.
        """
        if not self.is_available() or self._monitoring_active:
            return
        try:
            import openlit
            kwargs: dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            openlit.init(**kwargs)
            self._monitoring_active = True
            logger.info("OpenLIT monitoring initialized")
        except Exception as e:
            logger.warning("OpenLIT init_monitoring failed: %s", e)

    def log_prompt(
        self,
        name: str,
        template: str,
        variables: dict | None = None,
        version: str | None = None,
    ) -> None:
        """Log a prompt template to the OpenLIT prompt vault.

        Args:
            name: Prompt identifier (e.g., 'system_prompt', 'judge_accuracy').
            template: The prompt template string.
            variables: Optional dict of template variable defaults.
            version: Optional version tag (e.g., 'v1.2').
        """
        if not self.is_available():
            return
        try:
            import openlit
            kwargs: dict[str, Any] = {"name": name, "prompt": template}
            if variables:
                kwargs["variables"] = variables
            if version:
                kwargs["version"] = version
            if hasattr(openlit, "log_prompt"):
                openlit.log_prompt(**kwargs)
            else:
                logger.debug("OpenLIT log_prompt: API not available, skipping")
        except Exception as e:
            logger.warning("OpenLIT log_prompt failed: %s", e)

    def check_guardrails(self, text: str) -> dict:
        """Check text against OpenLIT content safety guardrails.

        Evaluates the text for PII, toxicity, prompt injection,
        and other safety concerns.

        Args:
            text: The text to evaluate.

        Returns:
            Dict with keys: 'safe' (bool), 'flags' (list of str).
            Returns safe=True with empty flags on failure.
        """
        default: dict[str, Any] = {"safe": True, "flags": []}
        if not self.is_available():
            return default
        try:
            import openlit
            if hasattr(openlit, "guard"):
                result = openlit.guard(text)
                if isinstance(result, dict):
                    return {
                        "safe": result.get("safe", True),
                        "flags": result.get("flags", []),
                    }
                return default
            if hasattr(openlit, "check_guardrails"):
                result = openlit.check_guardrails(text)
                if isinstance(result, dict):
                    return {
                        "safe": result.get("safe", True),
                        "flags": result.get("flags", []),
                    }
            return default
        except Exception as e:
            logger.warning("OpenLIT check_guardrails failed: %s", e)
            return default

    def get_gpu_stats(self) -> dict | None:
        """Retrieve current GPU utilization statistics.

        Returns:
            Dict with keys like 'gpu_utilization', 'memory_used',
            'memory_total', 'temperature'. Returns None if unavailable.
        """
        if not self.is_available():
            return None
        try:
            import openlit
            if hasattr(openlit, "get_gpu_stats"):
                stats = openlit.get_gpu_stats()
                return stats if isinstance(stats, dict) else None
            # Fallback: try nvidia-smi directly
            return self._gpu_stats_fallback()
        except Exception as e:
            logger.warning("OpenLIT get_gpu_stats failed: %s", e)
            return None

    @staticmethod
    def _gpu_stats_fallback() -> dict | None:
        """Attempt to read GPU stats via nvidia-smi subprocess."""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return None
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 4:
                return {
                    "gpu_utilization": float(parts[0]),
                    "memory_used_mb": float(parts[1]),
                    "memory_total_mb": float(parts[2]),
                    "temperature_c": float(parts[3]),
                }
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
        return None


# Singleton for lazy initialization
_bridge: OpenLITBridge | None = None


def get_bridge(api_key: str | None = None) -> OpenLITBridge:
    """Get or create the global OpenLIT bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = OpenLITBridge(api_key=api_key)
    return _bridge
