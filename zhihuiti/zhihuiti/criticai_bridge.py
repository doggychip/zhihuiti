"""CriticAI Bridge — cross-system monitoring, collaboration, and analysis.

Connects zhihuiti agents to the CriticAI entertainment review platform.
Agents can monitor critic health, analyze debates, generate meta-commentary,
persist metrics over time, and expose CriticAI data via MCP tools.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
from rich.console import Console
from rich.table import Table

console = Console()

DEFAULT_BASE_URL = "https://criticai.zeabur.app"

# MCP tool definitions for exposing CriticAI via the MCP server
CRITICAI_MCP_TOOLS = [
    {
        "name": "criticai_status",
        "description": (
            "Check the health and status of the CriticAI entertainment review platform. "
            "Returns agent count, top critics, recent activity count, and online status."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "criticai_analyze_ecosystem",
        "description": (
            "Use zhihuiti's multi-agent system to perform a deep analysis of the CriticAI "
            "critic ecosystem — diversity, content coverage, activity health, rivalry dynamics, "
            "and evolutionary patterns. Returns a scored analysis report."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "description": "Optional analysis focus: 'diversity', 'activity', 'rivalries', 'trends', or 'all'",
                    "default": "all",
                },
            },
        },
    },
    {
        "name": "criticai_trigger_activity",
        "description": "Trigger a random CriticAI agent to generate new content (hot take, recommendation, etc.).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "criticai_get_metrics_history",
        "description": "Retrieve stored CriticAI metrics history for trend analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent snapshots to return",
                    "default": 20,
                },
            },
        },
    },
]


class CriticAIBridge:
    """Bridge to CriticAI's API for monitoring, analysis, and collaboration."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, memory=None):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=15)
        self.memory = memory  # Optional: zhihuiti Memory instance for persistence

    def _get(self, path: str) -> Any:
        try:
            res = self.client.get(f"{self.base_url}{path}")
            res.raise_for_status()
            return res.json()
        except Exception as e:
            console.print(f"  [red]CriticAI API error ({path}):[/red] {e}")
            return None

    def _post(self, path: str, data: dict | None = None) -> Any:
        try:
            res = self.client.post(f"{self.base_url}{path}", json=data or {})
            res.raise_for_status()
            return res.json()
        except Exception as e:
            console.print(f"  [red]CriticAI API error ({path}):[/red] {e}")
            return None

    # === Health & Status ===

    def health_check(self) -> dict:
        """Check if CriticAI is responsive and return basic stats."""
        agents = self._get("/api/agents")
        leaderboard = self._get("/api/leaderboard")
        activity = self._get("/api/activity-feed?limit=3")

        return {
            "online": agents is not None,
            "agent_count": len(agents) if agents else 0,
            "top_agents": leaderboard.get("topAgents", [])[:3] if leaderboard else [],
            "recent_activity": len(activity) if activity else 0,
        }

    def get_agents(self) -> list[dict]:
        """Get all critic agents."""
        return self._get("/api/agents") or []

    def get_agent_profile(self, agent_id: int) -> dict | None:
        """Get detailed agent profile with stats and memories."""
        return self._get(f"/api/agents/{agent_id}")

    def get_leaderboard(self) -> dict | None:
        """Get full leaderboard data."""
        return self._get("/api/leaderboard")

    def get_activity_feed(self, limit: int = 10) -> list[dict]:
        """Get recent agent activities."""
        return self._get(f"/api/activity-feed?limit={limit}") or []

    def get_rivalries(self) -> list[dict]:
        """Get agent rivalry network."""
        return self._get("/api/agents/network") or []

    def get_trending_content(self) -> list[dict]:
        """Get top-rated content."""
        return self._get("/api/content/trending") or []

    # === Active Collaboration ===

    def trigger_activity(self) -> dict | None:
        """Trigger a random agent to generate a new activity (hot take, recommendation, etc.)."""
        return self._post("/api/generate-activity")

    # === Monitoring Reports ===

    def generate_status_report(self) -> str:
        """Generate a comprehensive status report for zhihuiti agents to analyze."""
        health = self.health_check()
        if not health["online"]:
            return "CriticAI is OFFLINE — cannot reach the API."

        agents = self.get_agents()
        leaderboard = self.get_leaderboard()
        activities = self.get_activity_feed(limit=5)
        rivalries = self.get_rivalries()

        lines = [
            f"=== CriticAI Status Report ===",
            f"Status: ONLINE",
            f"Total agents: {len(agents)} ({sum(1 for a in agents if not a.get('isCustom')) } built-in, {sum(1 for a in agents if a.get('isCustom'))} custom)",
            "",
        ]

        # Agent rankings
        if leaderboard and leaderboard.get("topAgents"):
            lines.append("Top Critics:")
            for i, entry in enumerate(leaderboard["topAgents"][:5]):
                agent = entry["agent"]
                lines.append(
                    f"  #{i+1} {agent['name']} — avg {entry['avgScore']}/10, "
                    f"{entry['totalReviews']} reviews, contrarian: {entry['contrarian']}"
                )
            lines.append("")

        # Recent activity
        if activities:
            lines.append("Recent Activity:")
            for act in activities[:5]:
                agent_name = act.get("agent", {}).get("name", "Unknown")
                lines.append(f"  [{act.get('activityType', '?')}] {agent_name}: {act.get('content', '')[:80]}")
            lines.append("")

        # Rivalries
        if rivalries:
            lines.append(f"Agent Rivalries: {len(rivalries)} active relationships")
            for r in rivalries[:3]:
                lines.append(
                    f"  {r.get('agent', {}).get('name', '?')} vs {r.get('rival', {}).get('name', '?')} "
                    f"— agreement: {round(r.get('agreementRate', 0) * 100)}%"
                )

        return "\n".join(lines)

    def print_status(self) -> None:
        """Print a formatted status table to the console."""
        health = self.health_check()

        table = Table(title="CriticAI Status")
        table.add_column("Metric", style="bold")
        table.add_column("Value")

        table.add_row("Status", "[green]ONLINE[/green]" if health["online"] else "[red]OFFLINE[/red]")
        table.add_row("Agents", str(health["agent_count"]))
        table.add_row("Recent Activities", str(health["recent_activity"]))

        if health["top_agents"]:
            top = health["top_agents"][0]
            table.add_row("Top Critic", f"{top['agent']['name']} (avg {top['avgScore']})")

        console.print(table)

    # === Persistence ===

    def _ensure_metrics_table(self) -> None:
        """Create the criticai_metrics table if it doesn't exist."""
        if self.memory is None:
            return
        with self.memory._lock:
            self.memory.conn.execute("""
                CREATE TABLE IF NOT EXISTS criticai_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    online INTEGER NOT NULL,
                    agent_count INTEGER NOT NULL,
                    top_critic_name TEXT,
                    top_critic_score REAL,
                    recent_activity_count INTEGER,
                    data_json TEXT
                )
            """)
            self.memory.conn.commit()

    def snapshot_metrics(self) -> dict | None:
        """Take a health snapshot and persist it to the database."""
        health = self.health_check()

        if self.memory is not None:
            self._ensure_metrics_table()
            top_name = None
            top_score = None
            if health["top_agents"]:
                top = health["top_agents"][0]
                top_name = top.get("agent", {}).get("name")
                top_score = top.get("avgScore")

            with self.memory._lock:
                self.memory.conn.execute(
                    """INSERT INTO criticai_metrics
                       (timestamp, online, agent_count, top_critic_name, top_critic_score,
                        recent_activity_count, data_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        int(health["online"]),
                        health["agent_count"],
                        top_name,
                        top_score,
                        health["recent_activity"],
                        json.dumps(health, default=str),
                    ),
                )
                self.memory.conn.commit()

        return health

    def get_metrics_history(self, limit: int = 20) -> list[dict]:
        """Retrieve stored metric snapshots for trend analysis."""
        if self.memory is None:
            return []
        self._ensure_metrics_table()
        rows = self.memory._query(
            "SELECT * FROM criticai_metrics ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in rows]

    def detect_anomalies(self) -> list[str]:
        """Check recent metrics for anomalies (stale activity, score drops, offline)."""
        history = self.get_metrics_history(limit=5)
        if not history:
            return []

        alerts: list[str] = []
        latest = history[0]

        if not latest.get("online"):
            alerts.append("ALERT: CriticAI is OFFLINE")

        if latest.get("recent_activity_count", 0) == 0:
            alerts.append("ALERT: No recent activity detected — system may be stale")

        if len(history) >= 2:
            prev_score = history[1].get("top_critic_score")
            curr_score = latest.get("top_critic_score")
            if prev_score and curr_score and curr_score < prev_score * 0.8:
                alerts.append(
                    f"ALERT: Top critic score dropped {prev_score:.1f} → {curr_score:.1f}"
                )

        return alerts

    # === Deep Analysis (Orchestrator Integration) ===

    def analyze_ecosystem(self, focus: str = "all") -> str:
        """Use zhihuiti's orchestrator to perform deep analysis of CriticAI ecosystem."""
        report = self.generate_status_report()
        if "OFFLINE" in report:
            return report

        focus_prompts = {
            "diversity": "Analyze agent diversity — roles, specializations, content coverage gaps.",
            "activity": "Analyze activity health — frequency, quality trends, engagement patterns.",
            "rivalries": "Analyze rivalry dynamics — agreement rates, debate quality, polarization.",
            "trends": "Identify emerging content trends and underserved review categories.",
            "all": (
                "Perform a comprehensive analysis covering: agent diversity, activity health, "
                "rivalry dynamics, content trends, and evolutionary patterns."
            ),
        }

        prompt = focus_prompts.get(focus, focus_prompts["all"])
        goal = (
            f"Analyze the CriticAI entertainment review platform ecosystem.\n\n"
            f"Current Status Data:\n{report}\n\n"
            f"Analysis Focus: {prompt}\n\n"
            f"Provide actionable insights and recommendations."
        )

        try:
            from zhihuiti.orchestrator import Orchestrator
            import os

            orch = Orchestrator(
                db_path=os.environ.get("ZHIHUITI_DB", ":memory:"),
                model=os.environ.get("ZHIHUITI_MODEL"),
            )
            result = orch.execute_goal(goal)
            return result.get("summary", str(result)) if isinstance(result, dict) else str(result)
        except Exception as e:
            return f"Analysis failed: {e}"

    # === MCP Tool Handler ===

    def handle_mcp_tool(self, name: str, arguments: dict) -> dict:
        """Handle MCP tool calls for CriticAI-related tools."""
        try:
            if name == "criticai_status":
                health = self.health_check()
                report = self.generate_status_report()
                return {"content": [{"type": "text", "text": report}]}

            elif name == "criticai_analyze_ecosystem":
                focus = arguments.get("focus", "all")
                result = self.analyze_ecosystem(focus)
                return {"content": [{"type": "text", "text": result}]}

            elif name == "criticai_trigger_activity":
                result = self.trigger_activity()
                text = json.dumps(result, indent=2) if result else "Failed to trigger activity"
                return {"content": [{"type": "text", "text": text}]}

            elif name == "criticai_get_metrics_history":
                limit = arguments.get("limit", 20)
                history = self.get_metrics_history(limit=limit)
                text = json.dumps(history, indent=2, default=str) if history else "No metrics stored yet"
                return {"content": [{"type": "text", "text": text}]}

            else:
                return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
