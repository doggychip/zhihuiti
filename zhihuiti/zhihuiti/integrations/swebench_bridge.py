"""SWE-bench Bridge — standardized coding agent evaluation.

Wraps SWE-bench (https://swe-bench.github.io/) for measuring agent
performance on real GitHub issues. SWE-bench provides 2,294 real-world
software engineering tasks collected from popular Python repositories.

Use this to benchmark zhihuiti coding agents against the standard
SWE-bench Lite (300 tasks) or full dataset.

NOTE: Requires Docker for sandboxed execution of test suites.
      Requires datasets and swebench packages.

Install: pip install swebench datasets
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# SWE-bench dataset identifiers
DATASETS = {
    "lite": "princeton-nlp/SWE-bench_Lite",
    "full": "princeton-nlp/SWE-bench",
    "verified": "princeton-nlp/SWE-bench_Verified",
}


class SWEBenchBridge:
    """Bridge to SWE-bench for standardized agent evaluation.

    Lazy-loads the dataset on first use. If swebench or datasets are
    not installed, is_available() returns False and methods return
    empty/mock results.

    Full implementation would:
      - Load task instances from HuggingFace datasets
      - Set up Docker containers per task for sandboxed evaluation
      - Apply agent-generated patches and run test suites
      - Report pass/fail per task with detailed logs
    """

    def __init__(self, dataset: str = "lite"):
        self._dataset_key = dataset
        self._dataset_name = DATASETS.get(dataset, DATASETS["lite"])
        self._available: bool | None = None
        self._tasks: list[dict] | None = None

    def is_available(self) -> bool:
        """Check if swebench and datasets packages are installed."""
        if self._available is not None:
            return self._available

        try:
            import datasets  # noqa: F401
            self._available = True
        except ImportError:
            logger.debug("datasets not installed — SWEBenchBridge disabled")
            self._available = False

        return self._available

    def _load_tasks(self) -> list[dict]:
        """Lazily load the SWE-bench task dataset.

        Full implementation loads from HuggingFace:
            from datasets import load_dataset
            ds = load_dataset(self._dataset_name, split="test")
        """
        if self._tasks is not None:
            return self._tasks

        if not self.is_available():
            self._tasks = []
            return self._tasks

        try:
            from datasets import load_dataset  # type: ignore

            ds = load_dataset(self._dataset_name, split="test")
            self._tasks = [
                {
                    "instance_id": row["instance_id"],
                    "repo": row.get("repo", ""),
                    "issue_text": row.get("problem_statement", ""),
                    "test_patch": row.get("test_patch", ""),
                    "base_commit": row.get("base_commit", ""),
                    "hints_text": row.get("hints_text", ""),
                    "version": row.get("version", ""),
                }
                for row in ds
            ]
            logger.info(
                "Loaded %d tasks from %s", len(self._tasks), self._dataset_name
            )
            return self._tasks
        except Exception as e:
            logger.error("Failed to load SWE-bench dataset: %s", e)
            self._tasks = []
            return self._tasks

    def get_tasks(self, limit: int = 10) -> list[dict]:
        """Get SWE-bench task instances.

        Args:
            limit: Maximum number of tasks to return.

        Returns:
            List of task dicts [{instance_id, repo, issue_text, test_patch,
            base_commit, hints_text, version}]. Empty list on failure.
        """
        tasks = self._load_tasks()
        return tasks[:limit]

    def evaluate_patch(self, instance_id: str, patch_text: str) -> dict:
        """Evaluate a generated patch against SWE-bench test suite.

        Args:
            instance_id: The SWE-bench instance ID (e.g. "astropy__astropy-12907").
            patch_text: The unified diff patch to evaluate.

        Returns:
            {instance_id, resolved: bool, tests_passed: int, tests_failed: int,
             error: str|None}. Returns resolved=False with error on failure.

        Full implementation would:
            1. Clone the repo at base_commit inside a Docker container
            2. Apply the patch_text via `git apply`
            3. Run the test suite (test_patch defines which tests)
            4. Parse test output for pass/fail counts
            5. resolved = True if all relevant tests pass
        """
        if not self.is_available():
            logger.debug("Mock evaluate_patch for %s", instance_id)
            return {
                "instance_id": instance_id,
                "resolved": False,
                "tests_passed": 0,
                "tests_failed": 0,
                "error": "SWE-bench not available (datasets package not installed)",
                "mock": True,
            }

        try:
            # Full implementation: Docker-based sandboxed evaluation
            # 1. Find the task by instance_id
            tasks = self._load_tasks()
            task = next((t for t in tasks if t["instance_id"] == instance_id), None)
            if task is None:
                return {
                    "instance_id": instance_id,
                    "resolved": False,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "error": f"Instance {instance_id} not found in dataset",
                }

            # 2. Placeholder for Docker evaluation
            # In full implementation:
            #   - swebench.harness.run_evaluation(instance_id, patch_text)
            #   - Parse grading output
            logger.info("evaluate_patch(%s): patch length=%d", instance_id, len(patch_text))
            return {
                "instance_id": instance_id,
                "resolved": False,
                "tests_passed": 0,
                "tests_failed": 0,
                "error": "Docker evaluation not yet wired (stub implementation)",
            }
        except Exception as e:
            logger.error("evaluate_patch(%s) failed: %s", instance_id, e)
            return {
                "instance_id": instance_id,
                "resolved": False,
                "tests_passed": 0,
                "tests_failed": 0,
                "error": str(e),
            }

    def run_benchmark(
        self,
        agent_fn: Callable[[dict], str],
        tasks: list[dict] | None = None,
        limit: int = 10,
    ) -> dict:
        """Run a full benchmark: agent generates patches, SWE-bench evaluates.

        Args:
            agent_fn: Callable that takes a task dict and returns a patch string.
                      Signature: (task: dict) -> str (unified diff).
            tasks: Optional pre-selected tasks. If None, loads from dataset.
            limit: Maximum tasks to evaluate (ignored if tasks provided).

        Returns:
            {resolved_count, total, resolve_rate, per_task_results: [{
                instance_id, resolved, tests_passed, tests_failed, error
            }]}

        Full implementation would:
            1. For each task: call agent_fn to generate a patch
            2. Evaluate each patch via evaluate_patch()
            3. Aggregate pass/fail statistics
            4. Return resolve rate and per-task breakdown
        """
        if tasks is None:
            tasks = self.get_tasks(limit=limit)

        if not tasks:
            return {
                "resolved_count": 0,
                "total": 0,
                "resolve_rate": 0.0,
                "per_task_results": [],
            }

        results: list[dict] = []
        resolved = 0

        for task in tasks:
            instance_id = task["instance_id"]
            try:
                patch = agent_fn(task)
                result = self.evaluate_patch(instance_id, patch)
            except Exception as e:
                logger.error("Agent failed on %s: %s", instance_id, e)
                result = {
                    "instance_id": instance_id,
                    "resolved": False,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "error": f"Agent error: {e}",
                }

            results.append(result)
            if result.get("resolved"):
                resolved += 1

        total = len(results)
        return {
            "resolved_count": resolved,
            "total": total,
            "resolve_rate": resolved / total if total > 0 else 0.0,
            "per_task_results": results,
        }


# Singleton for lazy initialization
_bridge: SWEBenchBridge | None = None


def get_bridge(dataset: str = "lite") -> SWEBenchBridge:
    """Get or create the global SWE-bench bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = SWEBenchBridge(dataset=dataset)
    return _bridge
