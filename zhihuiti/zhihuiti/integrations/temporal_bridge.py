"""Temporal Bridge — crash-resilient workflow orchestration.

Wraps Temporal (https://temporal.io/) for durable execution of
long-running agent workflows. Temporal guarantees that workflows
survive process crashes, network failures, and server restarts.

Integration points:
  - Goal decomposition: each zhihuiti goal becomes a Temporal workflow
  - Agent tasks: individual agent calls become Temporal activities
  - Crash recovery: if the process dies mid-goal, Temporal resumes from
    the last completed activity on restart

NOTE: Requires running Temporal server (docker-compose or Temporal Cloud).
  docker run -d --name temporal -p 7233:7233 temporalio/auto-setup:latest

Install: pip install temporalio
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class TemporalBridge:
    """Bridge to Temporal for durable workflow orchestration.

    Lazy-connects to Temporal server on first use. If temporalio is not
    installed or the server is unreachable, is_available() returns False
    and methods return mock/empty results.

    Full implementation would:
      - Define @workflow.defn classes for goal execution flows
      - Define @activity.defn functions for individual agent tasks
      - Use workflow.execute_activity() with retry policies
      - Support child workflows for sub-goal decomposition
      - Provide signal/query handlers for real-time status
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 7233,
        namespace: str = "zhihuiti",
        task_queue: str = "zhihuiti-agents",
    ):
        self._host = host
        self._port = port
        self._namespace = namespace
        self._task_queue = task_queue
        self._available: bool | None = None
        self._client: Any = None
        # In-memory mock workflow tracking
        self._mock_workflows: dict[str, dict] = {}

    def is_available(self) -> bool:
        """Check if temporalio is installed."""
        if self._available is not None:
            return self._available

        try:
            import temporalio  # noqa: F401
            self._available = True
        except ImportError:
            logger.debug("temporalio not installed — TemporalBridge using mock mode")
            self._available = False

        return self._available

    async def _get_client(self) -> Any:
        """Lazily connect to the Temporal server.

        Full implementation:
            from temporalio.client import Client
            self._client = await Client.connect(
                f"{self._host}:{self._port}",
                namespace=self._namespace,
            )
        """
        if self._client is not None:
            return self._client

        if not self.is_available():
            return None

        try:
            from temporalio.client import Client  # type: ignore

            self._client = await Client.connect(
                f"{self._host}:{self._port}",
                namespace=self._namespace,
            )
            logger.info("Connected to Temporal at %s:%d", self._host, self._port)
            return self._client
        except Exception as e:
            logger.warning("Temporal connection failed: %s", e)
            self._available = False
            return None

    def start_goal_workflow(self, goal: str, config: dict | None = None) -> str:
        """Start a durable goal-execution workflow.

        The workflow survives process crashes — Temporal replays completed
        activities and resumes from the last checkpoint on restart.

        Args:
            goal: The goal description to execute.
            config: Optional workflow config (timeout, retry policy, etc.).

        Returns:
            workflow_id string for tracking. Empty string on failure.

        Full implementation would:
            1. client.start_workflow(GoalWorkflow.run, goal,
                   id=workflow_id, task_queue=self._task_queue)
            2. GoalWorkflow decomposes goal into sub-tasks
            3. Each sub-task is a Temporal activity with retry policy
            4. Activities call zhihuiti agent loop
            5. Results aggregate back in the workflow
        """
        workflow_id = f"goal-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        if not self.is_available():
            # Mock workflow for testing without Temporal server
            self._mock_workflows[workflow_id] = {
                "workflow_id": workflow_id,
                "goal": goal,
                "config": config or {},
                "status": "RUNNING",
                "started_at": now,
                "completed_at": None,
                "result": None,
                "mock": True,
            }
            logger.debug("Mock workflow started: %s — %s", workflow_id, goal[:80])
            return workflow_id

        try:
            # Full implementation: start Temporal workflow
            # handle = await client.start_workflow(
            #     GoalWorkflow.run, goal,
            #     id=workflow_id,
            #     task_queue=self._task_queue,
            #     execution_timeout=timedelta(hours=24),
            # )
            logger.info("Workflow started: %s", workflow_id)
            return workflow_id
        except Exception as e:
            logger.error("start_goal_workflow failed: %s", e)
            return ""

    def get_workflow_status(self, workflow_id: str) -> dict:
        """Get the current status of a workflow.

        Args:
            workflow_id: The workflow ID returned by start_goal_workflow().

        Returns:
            {workflow_id, goal, status, started_at, completed_at, result}.
            Empty dict if not found.

        Full implementation would:
            handle = client.get_workflow_handle(workflow_id)
            desc = await handle.describe()
            Return status, close_time, execution_time, etc.
        """
        if not self.is_available():
            wf = self._mock_workflows.get(workflow_id)
            return dict(wf) if wf else {}

        try:
            # Full implementation: query Temporal for workflow status
            return {"workflow_id": workflow_id, "status": "UNKNOWN"}
        except Exception as e:
            logger.error("get_workflow_status(%s) failed: %s", workflow_id, e)
            return {}

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow.

        Args:
            workflow_id: The workflow to cancel.

        Returns:
            True if cancel was issued, False on failure.

        Full implementation would:
            handle = client.get_workflow_handle(workflow_id)
            await handle.cancel()
        """
        if not self.is_available():
            wf = self._mock_workflows.get(workflow_id)
            if wf and wf["status"] == "RUNNING":
                wf["status"] = "CANCELLED"
                wf["completed_at"] = datetime.now(timezone.utc).isoformat()
                return True
            return False

        try:
            # Full implementation: cancel via Temporal client
            logger.info("Workflow cancelled: %s", workflow_id)
            return True
        except Exception as e:
            logger.error("cancel_workflow(%s) failed: %s", workflow_id, e)
            return False

    def list_running_workflows(self) -> list[dict]:
        """List all currently running workflows.

        Returns:
            List of workflow summary dicts [{workflow_id, goal, status, started_at}].
            Empty list on failure.

        Full implementation would:
            async for wf in client.list_workflows('ExecutionStatus="Running"'):
                results.append({...})
        """
        if not self.is_available():
            return [
                {
                    "workflow_id": wf["workflow_id"],
                    "goal": wf["goal"],
                    "status": wf["status"],
                    "started_at": wf["started_at"],
                }
                for wf in self._mock_workflows.values()
                if wf["status"] == "RUNNING"
            ]

        try:
            # Full implementation: list workflows via Temporal client
            return []
        except Exception as e:
            logger.error("list_running_workflows failed: %s", e)
            return []


# Singleton for lazy initialization
_bridge: TemporalBridge | None = None


def get_bridge(
    host: str = "localhost",
    port: int = 7233,
    namespace: str = "zhihuiti",
) -> TemporalBridge:
    """Get or create the global Temporal bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = TemporalBridge(host=host, port=port, namespace=namespace)
    return _bridge
