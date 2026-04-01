"""Evolution dashboard — generates static HTML report from simulation data.

Reads epoch_stats, agent_decisions, and genome_snapshots from SQLite.
Produces a self-contained HTML file with Plotly charts.

MVP charts:
1. Fitness over time (avg/min/max)
2. Strategy archetypes (stacked area)
3. Market prices by role
4. Agent leaderboard
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zhihuiti.memory import Memory


def generate_report(memory: Memory, output_path: str = "zhihuiti_evolution_report.html") -> None:
    """Generate a static HTML dashboard from simulation data."""
    stats = memory.get_epoch_stats(limit=10000)
    if not stats:
        return

    # Sort by epoch ascending
    stats.sort(key=lambda s: s["epoch"])

    epochs = [s["epoch"] for s in stats]
    avg_fitness = [s["avg_fitness"] for s in stats]
    populations = [s["population"] for s in stats]
    money_supply = [s["money_supply"] for s in stats]
    gini = [s["gini"] for s in stats]

    # Archetype data
    archetype_names = set()
    for s in stats:
        counts = json.loads(s["archetype_counts"]) if isinstance(s["archetype_counts"], str) else s["archetype_counts"]
        archetype_names.update(counts.keys())
    archetype_names = sorted(archetype_names)

    archetype_series = {name: [] for name in archetype_names}
    for s in stats:
        counts = json.loads(s["archetype_counts"]) if isinstance(s["archetype_counts"], str) else s["archetype_counts"]
        for name in archetype_names:
            archetype_series[name].append(counts.get(name, 0))

    # Get latest genome snapshots for leaderboard
    latest_epoch = epochs[-1] if epochs else 0
    snapshots = memory.get_genome_snapshots_for_epoch(latest_epoch)

    # Get latest decisions for reasoning display
    decisions = memory.get_agent_decisions_for_epoch(latest_epoch)

    # Build HTML
    html = _build_html(
        epochs, avg_fitness, populations, money_supply, gini,
        archetype_names, archetype_series, snapshots, decisions, latest_epoch,
    )

    with open(output_path, "w") as f:
        f.write(html)


def _build_html(
    epochs: list[int],
    avg_fitness: list[float],
    populations: list[int],
    money_supply: list[float],
    gini: list[float],
    archetype_names: list[str],
    archetype_series: dict[str, list[int]],
    snapshots: list[dict],
    decisions: list[dict],
    latest_epoch: int,
) -> str:
    """Build the complete HTML report."""

    # Archetype colors
    colors = {
        "specialist": "#2a9d8f",
        "generalist": "#457b9d",
        "trader": "#e9c46a",
        "predator": "#e76f51",
    }

    # Build archetype traces
    archetype_traces = ""
    for name in archetype_names:
        color = colors.get(name, "#999")
        y_data = archetype_series[name]
        archetype_traces += f"""{{
            x: {epochs},
            y: {y_data},
            name: '{name}',
            type: 'scatter',
            mode: 'lines',
            stackgroup: 'one',
            line: {{color: '{color}'}},
        }},\n"""

    # Build leaderboard rows
    leaderboard_rows = ""
    sorted_snaps = sorted(snapshots, key=lambda s: s.get("fitness", 0), reverse=True)
    for i, snap in enumerate(sorted_snaps[:15]):
        genome = json.loads(snap["genome"]) if isinstance(snap["genome"], str) else snap["genome"]
        agent_id = snap.get("agent_id", "?")[:8]
        archetype = snap.get("archetype", "?")
        fitness = snap.get("fitness", 0)

        # Find matching decision
        reasoning = ""
        for d in decisions:
            if d.get("agent_id", "")[:8] == snap.get("agent_id", "")[:8]:
                reasoning = d.get("reasoning", "")[:100]
                break

        genome_bars = ""
        for trait_name, trait_val in genome.items():
            width = int(trait_val * 60)
            genome_bars += f'<span style="display:inline-block;width:{width}px;height:8px;background:#457b9d;border-radius:2px;margin-right:2px" title="{trait_name}: {trait_val:.2f}"></span>'

        leaderboard_rows += f"""<tr>
            <td>{i+1}</td>
            <td style="font-family:monospace">{agent_id}</td>
            <td>{archetype}</td>
            <td style="font-weight:bold">{fitness:.3f}</td>
            <td>{genome_bars}</td>
            <td style="font-size:11px;color:#666;max-width:300px;overflow:hidden;text-overflow:ellipsis">{reasoning}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>zhihuiti Evolution Report — Epoch {latest_epoch}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body {{ font-family: 'SF Mono', monospace; background: #fafaf8; color: #333; padding: 24px; max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 20px; margin-bottom: 4px; }}
  .subtitle {{ font-size: 12px; color: #888; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
  .chart {{ border: 1px solid #ddd; border-radius: 4px; padding: 8px; background: #fff; }}
  .full-width {{ grid-column: 1 / -1; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{ text-align: left; padding: 6px 8px; border-bottom: 2px solid #ddd; font-size: 10px; text-transform: uppercase; color: #666; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #eee; }}
</style>
</head>
<body>

<h1>zhihuiti · Evolution Report</h1>
<p class="subtitle">Darwinian arms race — {latest_epoch} epochs completed</p>

<div class="grid">
  <div class="chart" id="fitness-chart"></div>
  <div class="chart" id="archetype-chart"></div>
</div>

<div class="full-width">
  <h2 style="font-size:14px;margin:16px 0 8px">Agent Leaderboard — Epoch {latest_epoch}</h2>
  <table>
    <tr><th>#</th><th>Agent</th><th>Archetype</th><th>Fitness</th><th>Genome</th><th>Last Reasoning</th></tr>
    {leaderboard_rows}
  </table>
</div>

<script>
// Fitness over time
Plotly.newPlot('fitness-chart', [{{
    x: {epochs},
    y: {avg_fitness},
    name: 'Avg Fitness',
    type: 'scatter',
    mode: 'lines',
    line: {{color: '#2a9d8f', width: 2}},
}}, {{
    x: {epochs},
    y: {populations},
    name: 'Population',
    type: 'scatter',
    mode: 'lines',
    line: {{color: '#e76f51', width: 1, dash: 'dot'}},
    yaxis: 'y2',
}}], {{
    title: 'Fitness & Population Over Time',
    xaxis: {{title: 'Epoch'}},
    yaxis: {{title: 'Avg Fitness', side: 'left'}},
    yaxis2: {{title: 'Population', side: 'right', overlaying: 'y'}},
    margin: {{t: 40, b: 40, l: 50, r: 50}},
    height: 300,
}});

// Archetype distribution
Plotly.newPlot('archetype-chart', [{archetype_traces}], {{
    title: 'Strategy Archetypes Over Time',
    xaxis: {{title: 'Epoch'}},
    yaxis: {{title: 'Count'}},
    margin: {{t: 40, b: 40, l: 50, r: 50}},
    height: 300,
}});
</script>

<p style="font-size:10px;color:#aaa;text-align:center;margin-top:24px">
  zhihuiti · Tierra with Reasoning · epoch {latest_epoch}
</p>
</body>
</html>"""
