"""CriticAI Bridge — cross-system monitoring and collaboration.

Connects zhihuiti agents to the CriticAI entertainment review platform.
Agents can monitor critic health, analyze debates, and generate meta-commentary.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from rich.console import Console
from rich.table import Table

console = Console()

DEFAULT_BASE_URL = "https://criticai.zeabur.app"


class CriticAIBridge:
    """Bridge to CriticAI's API for monitoring and collaboration."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=15)

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
