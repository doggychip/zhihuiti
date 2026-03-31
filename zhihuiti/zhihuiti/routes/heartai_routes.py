"""HeartAI and AlphaArena external integration routes for the dashboard."""

from __future__ import annotations

import os


def gather_external_data() -> dict:
    """Gather data from external integrations: AlphaArena and HeartAI.

    Returns a dict with 'alphaarena' and 'heartai' keys to merge into
    the main dashboard data.
    """
    data: dict = {}

    # AlphaArena external agents
    aa_url = os.environ.get("ALPHAARENA_URL", "")
    if aa_url:
        try:
            import httpx
            resp = httpx.get(f"{aa_url}/api/leaderboard", timeout=5)
            lb = resp.json()
            entries = lb if isinstance(lb, list) else lb.get("leaderboard", lb.get("entries", []))
            aa_agents = []
            for e in entries[:20]:
                agent_info = e.get("agent", {}) or {}
                aa_agents.append({
                    "id": e.get("agentId", "?"),
                    "name": agent_info.get("name", e.get("agentId", "?")),
                    "rank": e.get("rank", 0),
                    "totalReturn": e.get("totalReturn", 0),
                    "sharpeRatio": e.get("sharpeRatio", 0),
                    "winRate": e.get("winRate", 0),
                    "maxDrawdown": e.get("maxDrawdown", 0),
                    "compositeScore": e.get("compositeScore", 0),
                    "type": agent_info.get("type", "algo_bot"),
                })
            data["alphaarena"] = {
                "agents": aa_agents,
                "total": len(aa_agents),
                "url": aa_url,
            }
        except Exception:
            data["alphaarena"] = {"agents": [], "total": 0, "url": aa_url}
    else:
        data["alphaarena"] = {"agents": [], "total": 0, "url": ""}

    # HeartAI cross-project integration
    heartai_url = os.environ.get("HEARTAI_URL", "")
    if heartai_url:
        try:
            import httpx as _hx_heartai
            resp = _hx_heartai.get(f"{heartai_url}/api/agents", timeout=5)
            if resp.status_code == 200:
                heartai_data = resp.json()
                agents_list = heartai_data if isinstance(heartai_data, list) else heartai_data.get("agents", [])
                heartai_agents = []
                for a in agents_list[:20]:
                    heartai_agents.append({
                        "id": a.get("id", "?"),
                        "name": a.get("nickname", a.get("name", "?")),
                        "posts": a.get("postCount", 0),
                        "comments": a.get("commentCount", 0),
                        "type": a.get("agentDescription", "agent")[:50],
                    })
                data["heartai"] = {
                    "online": True,
                    "agents": heartai_agents,
                    "total": len(heartai_agents),
                    "url": heartai_url,
                }
            else:
                data["heartai"] = {"online": False, "agents": [], "total": 0, "url": heartai_url}
        except Exception:
            data["heartai"] = {"online": False, "agents": [], "total": 0, "url": heartai_url}
    else:
        data["heartai"] = {"online": False, "agents": [], "total": 0, "url": ""}

    return data
