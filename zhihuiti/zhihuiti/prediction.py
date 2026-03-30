"""预测误差引擎 — Prediction Error Engine.

Inspired by the brain's prediction error signal (dopamine system):
  - Before execution, agents predict their outcome score
  - After execution, measure the prediction error (actual - predicted)
  - Large errors are the richest learning signal
  - Prediction errors update causal graphs and agent calibration

The brain learns from SURPRISE, not just reward. When an agent's
causal model predicts X but Y happens, that gap is structural learning.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.causal import CausalGraph
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory
    from zhihuiti.models import AgentState, Task

console = Console()

# Prediction error thresholds
SURPRISE_THRESHOLD = 0.3   # Error above this = significant surprise
CALIBRATION_WINDOW = 10    # Rolling window for calibration score


PREDICTION_PROMPT = """You are predicting the outcome of a task before execution.

Given the task description, agent role, and any available context, predict:
1. The expected quality score (0.0 to 1.0)
2. A brief expected outcome description

Be calibrated — don't always predict high scores. Consider:
- Task difficulty and clarity
- Agent role suitability
- Available context and prior knowledge
- Potential failure modes

Respond with JSON:
{
  "predicted_score": 0.65,
  "predicted_outcome": "The agent should produce a reasonable analysis but may lack depth on market microstructure",
  "confidence": 0.6,
  "risk_factors": ["limited context", "complex domain"]
}"""


@dataclass
class Prediction:
    """A prediction about a task outcome."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    task_id: str = ""
    goal_id: str = ""
    predicted_score: float = 0.5
    predicted_outcome: str = ""
    actual_score: float | None = None
    actual_outcome: str = ""
    prediction_error: float | None = None

    @property
    def is_resolved(self) -> bool:
        return self.actual_score is not None

    @property
    def surprise(self) -> float:
        """Absolute prediction error — measure of surprise."""
        if self.prediction_error is None:
            return 0.0
        return abs(self.prediction_error)

    @property
    def is_surprising(self) -> bool:
        return self.surprise >= SURPRISE_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "predicted_score": self.predicted_score,
            "actual_score": self.actual_score,
            "prediction_error": self.prediction_error,
            "surprise": self.surprise,
            "is_surprising": self.is_surprising,
        }


class PredictionEngine:
    """Generates and tracks predictions for agent task outcomes.

    The dopamine system of zhihuiti: learns from surprise, not just reward.
    """

    def __init__(self, memory: "Memory", llm: "LLM | None" = None,
                 causal_graph: "CausalGraph | None" = None):
        self.memory = memory
        self.llm = llm
        self.causal_graph = causal_graph
        self.predictions: list[Prediction] = []

    # ------------------------------------------------------------------
    # Generate predictions
    # ------------------------------------------------------------------

    def predict(self, agent: "AgentState", task: "Task",
                goal_id: str = "") -> Prediction:
        """Generate a prediction for a task before execution.

        Uses LLM if available, otherwise uses agent history heuristic.
        """
        if self.llm:
            pred = self._llm_predict(agent, task, goal_id)
        else:
            pred = self._heuristic_predict(agent, task, goal_id)

        # Persist
        self.memory.save_prediction(
            pred_id=pred.id,
            agent_id=pred.agent_id,
            task_id=pred.task_id,
            predicted_score=pred.predicted_score,
            predicted_outcome=pred.predicted_outcome,
            goal_id=goal_id,
        )
        self.predictions.append(pred)
        return pred

    def _llm_predict(self, agent: "AgentState", task: "Task",
                     goal_id: str) -> Prediction:
        """Use LLM to generate a calibrated prediction."""
        # Build context
        context_parts = [
            f"Task: {task.description[:300]}",
            f"Agent role: {agent.config.role.value}",
            f"Agent avg score: {agent.avg_score:.2f}",
            f"Agent budget: {agent.budget:.1f}",
        ]

        # Add prior predictions for calibration
        prior = self.memory.get_agent_predictions(agent.id, resolved=True, limit=5)
        if prior:
            errors = [p.get("prediction_error", 0) for p in prior
                      if p.get("prediction_error") is not None]
            if errors:
                avg_err = sum(errors) / len(errors)
                context_parts.append(
                    f"Prior prediction bias: {avg_err:+.2f} "
                    f"(positive=overconfident, negative=underconfident)"
                )

        try:
            result = self.llm.chat_json(
                system=PREDICTION_PROMPT,
                user="\n".join(context_parts),
                temperature=0.3,
            )
            predicted_score = max(0.0, min(1.0, float(
                result.get("predicted_score", 0.5)
            )))
            predicted_outcome = result.get("predicted_outcome", "")
        except Exception:
            return self._heuristic_predict(agent, task, goal_id)

        return Prediction(
            agent_id=agent.id,
            task_id=task.id,
            goal_id=goal_id,
            predicted_score=predicted_score,
            predicted_outcome=predicted_outcome,
        )

    def _heuristic_predict(self, agent: "AgentState", task: "Task",
                           goal_id: str) -> Prediction:
        """Heuristic prediction based on agent history."""
        # Use agent's average score as the prediction, adjusted slightly
        base = agent.avg_score if agent.scores else 0.5

        # Adjust for known biases from prior predictions
        prior = self.memory.get_agent_predictions(agent.id, resolved=True, limit=10)
        if prior:
            errors = [p.get("prediction_error", 0) for p in prior
                      if p.get("prediction_error") is not None]
            if errors:
                bias = sum(errors) / len(errors)
                base -= bias * 0.5  # Partial correction

        predicted_score = max(0.1, min(0.95, base))

        return Prediction(
            agent_id=agent.id,
            task_id=task.id,
            goal_id=goal_id,
            predicted_score=round(predicted_score, 3),
            predicted_outcome=f"Expected {agent.config.role.value} performance based on history",
        )

    # ------------------------------------------------------------------
    # Resolve predictions
    # ------------------------------------------------------------------

    def resolve(self, prediction: Prediction, actual_score: float,
                actual_outcome: str = "") -> Prediction:
        """Resolve a prediction with actual results.

        Calculates prediction error and triggers learning if surprising.
        """
        prediction.actual_score = actual_score
        prediction.actual_outcome = actual_outcome
        prediction.prediction_error = actual_score - prediction.predicted_score

        # Persist resolution
        causal_update = {}
        if prediction.is_surprising:
            causal_update = self._learn_from_surprise(prediction)

        self.memory.resolve_prediction(
            pred_id=prediction.id,
            actual_score=actual_score,
            actual_outcome=actual_outcome,
            prediction_error=prediction.prediction_error,
            causal_update=causal_update,
        )

        # Log surprising predictions
        if prediction.is_surprising:
            direction = "better" if prediction.prediction_error > 0 else "worse"
            console.print(
                f"  [yellow]预测误差:[/yellow] Surprise! "
                f"Predicted {prediction.predicted_score:.2f}, "
                f"got {actual_score:.2f} ({direction} than expected, "
                f"error={prediction.prediction_error:+.2f})"
            )

        return prediction

    def _learn_from_surprise(self, prediction: Prediction) -> dict:
        """When a prediction is surprising, extract causal learning.

        Returns a dict describing what causal update was made.
        """
        if not self.causal_graph:
            return {"learned": False, "reason": "no causal graph"}

        error = prediction.prediction_error
        agent_id = prediction.agent_id
        task_id = prediction.task_id

        # If actual >> predicted: something unexpected helped
        # If actual << predicted: something unexpected hurt
        update = {
            "learned": True,
            "error": error,
            "direction": "positive_surprise" if error > 0 else "negative_surprise",
            "agent_id": agent_id,
            "task_id": task_id,
        }

        # Add a causal edge: "prediction_error → agent_calibration"
        # This represents the system learning that its model was wrong
        from zhihuiti.causal import EdgeType, EvidenceStrength
        self.causal_graph.add_edge(
            source=f"surprise_{task_id[:6]}",
            target="model_accuracy",
            edge_type=EdgeType.CAUSES,
            strength=EvidenceStrength.WEAK,
            confidence=min(abs(error), 0.9),
            evidence={"prediction_error": error, "agent": agent_id},
            domain="metacognition",
        )

        return update

    # ------------------------------------------------------------------
    # Agent calibration score
    # ------------------------------------------------------------------

    def get_calibration_score(self, agent_id: str) -> float:
        """Calculate how well-calibrated an agent's predictions are.

        Returns 0.0-1.0 where 1.0 = perfectly calibrated.
        """
        history = self.memory.get_agent_predictions(
            agent_id, resolved=True, limit=CALIBRATION_WINDOW,
        )
        if not history:
            return 0.5  # No data = neutral

        errors = [abs(p.get("prediction_error", 0)) for p in history
                  if p.get("prediction_error") is not None]
        if not errors:
            return 0.5

        avg_abs_error = sum(errors) / len(errors)
        # Convert error to calibration score: 0 error = 1.0, 1.0 error = 0.0
        return max(0.0, 1.0 - avg_abs_error)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_report(self) -> None:
        """Print prediction accuracy report."""
        stats = self.memory.get_prediction_stats()
        if stats["total_predictions"] == 0:
            return

        resolved = [p for p in self.predictions if p.is_resolved]
        if not resolved:
            # Try loading from DB
            return

        table = Table(title="预测误差 Prediction Error Report", show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total predictions", str(stats["total_predictions"]))
        table.add_row("Resolved", str(stats["resolved"]))
        table.add_row("Avg absolute error", f"{stats['avg_absolute_error']:.4f}")

        surprises = [p for p in resolved if p.is_surprising]
        table.add_row("Surprising outcomes", str(len(surprises)))

        if resolved:
            errors = [p.prediction_error for p in resolved if p.prediction_error is not None]
            if errors:
                bias = sum(errors) / len(errors)
                bias_label = "overconfident" if bias < 0 else "underconfident"
                table.add_row("Prediction bias", f"{bias:+.3f} ({bias_label})")

        console.print(Panel(table))

        # Show recent surprises
        recent_surprises = [p for p in resolved if p.is_surprising][-5:]
        if recent_surprises:
            s_table = Table(title="Recent Surprises")
            s_table.add_column("Task", max_width=20, style="dim")
            s_table.add_column("Predicted", justify="center")
            s_table.add_column("Actual", justify="center")
            s_table.add_column("Error", justify="center")

            for p in recent_surprises:
                err = p.prediction_error or 0
                style = "green" if err > 0 else "red"
                s_table.add_row(
                    p.task_id[:20],
                    f"{p.predicted_score:.2f}",
                    f"{p.actual_score:.2f}",
                    f"[{style}]{err:+.2f}[/{style}]",
                )
            console.print(s_table)
