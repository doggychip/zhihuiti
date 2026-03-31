"""Knowledge base and research report routes for the dashboard."""

from __future__ import annotations

import glob
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from zhihuiti.routes.agent_routes import _send_json


def handle_reports(handler: BaseHTTPRequestHandler, orch) -> None:
    """GET /api/reports — list research reports and goal outputs."""
    if not orch:
        _send_json(handler, {"reports": [], "goals": []})
        return

    # Get recent goals with their outputs
    goals = orch.memory.get_recent_goals(limit=20) if hasattr(orch.memory, "get_recent_goals") else []

    # Get recent high-scoring task results
    rows = orch.memory._query(
        "SELECT description, result, score, agent_role, created_at "
        "FROM task_history WHERE score >= 0.7 ORDER BY rowid DESC LIMIT 30"
    )
    reports = []
    for r in rows:
        reports.append({
            "task": r["description"][:100],
            "result": r["result"][:500] if r["result"] else "",
            "score": round(r["score"], 3),
            "role": r["agent_role"],
            "created_at": r["created_at"] if "created_at" in r.keys() else "",
        })

    # Check for markdown reports in ./reports/
    report_files = []
    for f in sorted(glob.glob("reports/daemon_*.md"), reverse=True)[:10]:
        try:
            with open(f) as fh:
                content = fh.read()
            report_files.append({"filename": f, "content": content[:2000]})
        except Exception:
            pass

    _send_json(handler, {"reports": reports, "goals": goals, "files": report_files})


def handle_knowledge(handler: BaseHTTPRequestHandler, orch) -> None:
    """GET /api/knowledge — query the knowledge base."""
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    query = params.get("q", [""])[0]

    if not orch:
        _send_json(handler, {"chunks": [], "stats": {}})
        return

    try:
        from zhihuiti.knowledge import KnowledgeBase
        kb = KnowledgeBase(orch.memory)
        if query:
            chunks = kb.query(query, top_k=10)
            _send_json(handler, {
                "query": query,
                "chunks": [
                    {"id": c.id, "title": c.title, "content": c.content[:300],
                     "source": c.source, "confidence": c.confidence}
                    for c in chunks
                ],
            })
        else:
            stats = kb.get_stats()
            _send_json(handler, {"stats": stats})
    except Exception as e:
        _send_json(handler, {"error": str(e)})
