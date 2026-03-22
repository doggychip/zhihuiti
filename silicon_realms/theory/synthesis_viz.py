"""
Synthesis Visualization
========================
Generate an interactive HTML page showing synthesized theories:
- Force-directed graph: parent theories → synthesized theory
- Click a synthesis node to see equations, variables, predictions
- Color by score, size by impact
"""
from __future__ import annotations

import json
from pathlib import Path

from .synthesis import SynthesizedTheory
from .collision_engine import THEORY_REGISTRY

# Domain colors (same as collision viz for consistency)
DOMAIN_COLORS = {
    "Evolutionary Game Theory": "#e74c3c",
    "Statistical Mechanics": "#e67e22",
    "Control Theory": "#2ecc71",
    "Information Theory": "#3498db",
    "Neuroscience": "#9b59b6",
    "Neuroscience / Cognitive Science": "#9b59b6",
    "Cognitive Science": "#8e44ad",
    "Dynamic Systems": "#1abc9c",
    "Quantum Physics": "#f39c12",
    "Meta-Frameworks": "#34495e",
    "Topology": "#e91e63",
}

SCORE_COLORS = {
    "high": "#f1c40f",
    "medium": "#e67e22",
    "low": "#95a5a6",
}


def _synthesis_graph_json(syntheses: list[SynthesizedTheory]) -> dict:
    """Build graph JSON: parent theory nodes + synthesis nodes + edges."""
    nodes = []
    links = []
    seen_parents = set()

    # Collect all parent theory nodes
    for s in syntheses:
        for parent_display in (s.parent_a, s.parent_b):
            if parent_display not in seen_parents:
                seen_parents.add(parent_display)
                # Look up domain
                domain = "Unknown"
                key = None
                for k, v in THEORY_REGISTRY.items():
                    if v["display_name"] == parent_display:
                        domain = v["domain"]
                        key = k
                        break
                nodes.append({
                    "id": f"theory:{parent_display}",
                    "name": parent_display,
                    "type": "theory",
                    "domain": domain,
                    "color": DOMAIN_COLORS.get(domain, "#95a5a6"),
                    "equation": THEORY_REGISTRY[key].get("equation", "") if key else "",
                    "score": 0,
                })

    # Add synthesis nodes
    for i, s in enumerate(syntheses):
        score_tier = "high" if s.overall_score >= 0.7 else "medium" if s.overall_score >= 0.4 else "low"
        syn_id = f"synthesis:{i}:{s.name}"
        nodes.append({
            "id": syn_id,
            "name": s.name,
            "type": "synthesis",
            "domain": "Synthesis",
            "color": SCORE_COLORS[score_tier],
            "score": round(s.overall_score, 3),
            "novelty": round(s.novelty_score, 3),
            "depth": round(s.depth_score, 3),
            "impact": round(s.impact_score, 3),
            "collision_score": round(s.collision_score, 3),
            "collision_strength": s.collision_strength,
            "core_equation": s.core_equation,
            "auxiliary_equations": s.auxiliary_equations,
            "update_mechanism": s.update_mechanism,
            "optimization_target": s.optimization_target,
            "backbone_patterns": s.backbone_patterns,
            "novel_patterns": s.novel_patterns,
            "variables": {k: v for k, v in s.combined_variables.items()},
            "conservation_laws": s.conservation_laws,
            "predicted_properties": s.predicted_properties,
            "research_directions": s.research_directions,
        })

        # Links from parents to synthesis
        links.append({
            "source": f"theory:{s.parent_a}",
            "target": syn_id,
            "type": "parent",
            "score": round(s.collision_score, 3),
        })
        links.append({
            "source": f"theory:{s.parent_b}",
            "target": syn_id,
            "type": "parent",
            "score": round(s.collision_score, 3),
        })

    return {
        "nodes": nodes,
        "links": links,
        "metadata": {
            "total_theories": len(seen_parents),
            "total_syntheses": len(syntheses),
            "total_links": len(links),
        },
    }


def generate_synthesis_html(
    syntheses: list[SynthesizedTheory],
    output_path: str | Path = "synthesis_map.html",
) -> Path:
    """Generate a standalone interactive HTML visualization of synthesized theories."""
    graph_data = _synthesis_graph_json(syntheses)
    json_str = json.dumps(graph_data, indent=2)

    html = _SYNTHESIS_HTML_TEMPLATE.replace("__GRAPH_DATA__", json_str)

    out = Path(output_path)
    out.write_text(html, encoding="utf-8")
    return out.resolve()


_SYNTHESIS_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Theory Synthesis Map — Silicon Realms</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #080816;
    color: #e0e0e0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    overflow: hidden;
  }

  #header {
    position: fixed; top: 0; left: 0; right: 0; z-index: 10;
    padding: 16px 24px;
    background: linear-gradient(180deg, rgba(8,8,22,0.97) 0%, rgba(8,8,22,0) 100%);
    pointer-events: none;
  }
  #header h1 {
    font-size: 22px; font-weight: 700; letter-spacing: 0.5px;
    background: linear-gradient(135deg, #f1c40f, #e74c3c, #9b59b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    pointer-events: auto;
  }
  #header .subtitle { font-size: 12px; color: #555; margin-top: 4px; }

  #legend {
    position: fixed; bottom: 20px; left: 24px; z-index: 10;
    display: flex; flex-wrap: wrap; gap: 12px; max-width: 500px;
  }
  .legend-item {
    display: flex; align-items: center; gap: 6px; font-size: 11px; color: #888;
  }
  .legend-shape {
    width: 14px; height: 14px; border: 1px solid rgba(255,255,255,0.15);
  }
  .legend-circle { border-radius: 50%; }
  .legend-diamond {
    width: 12px; height: 12px;
    transform: rotate(45deg);
    border-radius: 2px;
  }

  #stats {
    position: fixed; top: 70px; right: 24px; z-index: 10;
    font-size: 11px; color: #555; text-align: right;
  }

  /* Detail panel */
  #detail-panel {
    position: fixed; top: 0; right: -480px; width: 460px;
    height: 100vh; z-index: 30;
    background: rgba(12, 12, 28, 0.97);
    border-left: 1px solid rgba(255,255,255,0.08);
    backdrop-filter: blur(20px);
    transition: right 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    overflow-y: auto;
    padding: 28px 24px;
  }
  #detail-panel.open { right: 0; }
  #detail-panel .close-btn {
    position: absolute; top: 16px; right: 16px;
    background: none; border: none; color: #666; font-size: 20px;
    cursor: pointer; padding: 4px 8px;
  }
  #detail-panel .close-btn:hover { color: #fff; }

  .dp-name {
    font-size: 20px; font-weight: 700; margin-bottom: 4px;
    color: #f1c40f;
  }
  .dp-parents {
    font-size: 12px; color: #888; margin-bottom: 16px;
  }
  .dp-scores {
    display: flex; gap: 16px; margin-bottom: 20px;
  }
  .dp-score-item {
    text-align: center;
  }
  .dp-score-val {
    font-size: 24px; font-weight: 700;
  }
  .dp-score-label {
    font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1px;
  }

  .dp-section {
    margin-bottom: 18px;
  }
  .dp-section-title {
    font-size: 11px; font-weight: 600; color: #888;
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding-bottom: 4px;
  }
  .dp-equation {
    font-family: 'Courier New', 'Fira Code', monospace;
    font-size: 13px; color: #f39c12;
    background: rgba(243, 156, 18, 0.08);
    border: 1px solid rgba(243, 156, 18, 0.15);
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 6px;
    word-break: break-all;
    line-height: 1.5;
  }
  .dp-equation.aux {
    font-size: 11px; color: #e67e22;
    background: rgba(230, 126, 34, 0.06);
    border-color: rgba(230, 126, 34, 0.1);
  }
  .dp-list {
    list-style: none; padding: 0;
  }
  .dp-list li {
    font-size: 12px; line-height: 1.6; color: #bbb;
    padding: 2px 0;
  }
  .dp-list li::before {
    content: ''; display: inline-block;
    width: 6px; height: 6px; border-radius: 50%;
    margin-right: 8px; vertical-align: middle;
  }
  .dp-list.patterns li::before { background: #3498db; }
  .dp-list.novel li::before { background: #e74c3c; }
  .dp-list.props li::before { background: #2ecc71; }
  .dp-list.dirs li::before { background: #9b59b6; }
  .dp-list.vars li::before { background: #e67e22; }
  .dp-list.cons li::before { background: #1abc9c; }

  .dp-mechanism {
    font-size: 12px; color: #3498db; font-weight: 500;
  }
  .dp-opt-target {
    font-size: 12px; color: #aaa; margin-top: 4px;
  }

  /* Node tooltip */
  #tooltip {
    position: fixed;
    padding: 10px 14px;
    background: rgba(16, 16, 32, 0.95);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    font-size: 12px; line-height: 1.5;
    max-width: 300px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 20;
    backdrop-filter: blur(10px);
  }
  .tt-name { font-weight: 600; font-size: 13px; margin-bottom: 2px; }
  .tt-domain { font-size: 10px; color: #888; }
  .tt-score { font-size: 11px; color: #f1c40f; margin-top: 4px; }
  .tt-eq {
    font-family: monospace; font-size: 10px; color: #f39c12;
    background: rgba(0,0,0,0.3); padding: 3px 6px;
    border-radius: 3px; margin-top: 4px; display: block;
    word-break: break-all;
  }

  svg { width: 100vw; height: 100vh; }
</style>
</head>
<body>

<div id="header">
  <h1>Theory Synthesis Map</h1>
  <div class="subtitle">Cross-domain breakthrough generator — click a synthesis node for details</div>
</div>

<div id="stats"></div>

<div id="legend">
  <div class="legend-item">
    <div class="legend-shape legend-circle" style="background:#3498db"></div>
    Parent Theory
  </div>
  <div class="legend-item">
    <div class="legend-shape legend-diamond" style="background:#f1c40f"></div>
    High-Score Synthesis
  </div>
  <div class="legend-item">
    <div class="legend-shape legend-diamond" style="background:#e67e22"></div>
    Medium-Score Synthesis
  </div>
  <div class="legend-item">
    <div class="legend-shape legend-diamond" style="background:#95a5a6"></div>
    Low-Score Synthesis
  </div>
</div>

<div id="tooltip"></div>

<div id="detail-panel">
  <button class="close-btn" onclick="closePanel()">&times;</button>
  <div id="detail-content"></div>
</div>

<svg></svg>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const graphData = __GRAPH_DATA__;

const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("svg").attr("width", width).attr("height", height);

// Defs
const defs = svg.append("defs");
const glowFilter = defs.append("filter").attr("id", "glow");
glowFilter.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "blur");
const merge = glowFilter.append("feMerge");
merge.append("feMergeNode").attr("in", "blur");
merge.append("feMergeNode").attr("in", "SourceGraphic");

// Arrow markers
defs.append("marker")
  .attr("id", "arrowhead")
  .attr("viewBox", "0 -5 10 10")
  .attr("refX", 20).attr("refY", 0)
  .attr("markerWidth", 6).attr("markerHeight", 6)
  .attr("orient", "auto")
  .append("path")
  .attr("d", "M0,-4L8,0L0,4")
  .attr("fill", "#444");

const g = svg.append("g");

// Zoom
const zoom = d3.zoom()
  .scaleExtent([0.15, 5])
  .on("zoom", (event) => g.attr("transform", event.transform));
svg.call(zoom);

// Data
const nodes = graphData.nodes.map(d => ({...d}));
const links = graphData.links.map(d => ({...d}));

// Simulation
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id)
    .distance(d => 140)
    .strength(0.5))
  .force("charge", d3.forceManyBody().strength(d => d.type === "synthesis" ? -500 : -350))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collision", d3.forceCollide().radius(d => d.type === "synthesis" ? 25 : 18))
  .force("x", d3.forceX(width / 2).strength(0.04))
  .force("y", d3.forceY(height / 2).strength(0.04));

// Links
const linkSel = g.append("g")
  .selectAll("line")
  .data(links)
  .join("line")
  .attr("stroke", "#333")
  .attr("stroke-width", 1.5)
  .attr("stroke-opacity", 0.4)
  .attr("stroke-dasharray", d => d.type === "parent" ? "6,3" : "none")
  .attr("marker-end", "url(#arrowhead)");

// Node groups
const nodeGroup = g.append("g")
  .selectAll("g")
  .data(nodes)
  .join("g")
  .style("cursor", "pointer")
  .call(d3.drag()
    .on("start", (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x; d.fy = d.y;
    })
    .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
    .on("end", (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null; d.fy = null;
    })
  );

// Draw theory nodes as circles
nodeGroup.filter(d => d.type === "theory")
  .append("circle")
  .attr("r", 10)
  .attr("fill", d => d.color)
  .attr("stroke", "rgba(255,255,255,0.2)")
  .attr("stroke-width", 1)
  .style("filter", "url(#glow)");

// Draw synthesis nodes as diamonds (rotated squares)
nodeGroup.filter(d => d.type === "synthesis")
  .append("rect")
  .attr("width", d => 14 + d.score * 16)
  .attr("height", d => 14 + d.score * 16)
  .attr("x", d => -(14 + d.score * 16) / 2)
  .attr("y", d => -(14 + d.score * 16) / 2)
  .attr("rx", 3)
  .attr("transform", "rotate(45)")
  .attr("fill", d => d.color)
  .attr("stroke", "rgba(255,255,255,0.25)")
  .attr("stroke-width", 1.5)
  .style("filter", "url(#glow)");

// Labels
const labelSel = g.append("g")
  .selectAll("text")
  .data(nodes)
  .join("text")
  .text(d => {
    const name = d.name;
    return name.length > 28 ? name.slice(0, 26) + '...' : name;
  })
  .attr("font-size", d => d.type === "synthesis" ? 10 : 9)
  .attr("fill", d => d.type === "synthesis" ? "#ddd" : "#777")
  .attr("font-weight", d => d.type === "synthesis" ? "600" : "400")
  .attr("dx", d => d.type === "synthesis" ? 20 : 14)
  .attr("dy", 3)
  .style("pointer-events", "none");

// Hover
nodeGroup
  .on("mouseover", function(event, d) {
    const tt = document.getElementById("tooltip");
    let html = `<div class="tt-name">${d.name}</div>`;
    if (d.type === "theory") {
      html += `<div class="tt-domain">${d.domain}</div>`;
      if (d.equation) html += `<code class="tt-eq">${d.equation}</code>`;
    } else {
      html += `<div class="tt-score">Score: ${d.score} (${d.collision_strength})</div>`;
      html += `<code class="tt-eq">${d.core_equation}</code>`;
    }
    tt.innerHTML = html;
    tt.style.opacity = 1;
    tt.style.left = (event.clientX + 15) + "px";
    tt.style.top = (event.clientY - 10) + "px";

    // Highlight connected links
    linkSel.attr("stroke-opacity", l => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source;
      const tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === d.id || tid === d.id) ? 0.9 : 0.07;
    }).attr("stroke", l => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source;
      const tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === d.id || tid === d.id) ? "#f1c40f" : "#333";
    });
  })
  .on("mouseout", function() {
    document.getElementById("tooltip").style.opacity = 0;
    linkSel.attr("stroke-opacity", 0.4).attr("stroke", "#333");
  })
  .on("click", function(event, d) {
    if (d.type === "synthesis") openPanel(d);
  });

// Tick
simulation.on("tick", () => {
  linkSel
    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  nodeGroup.attr("transform", d => `translate(${d.x},${d.y})`);
  labelSel.attr("x", d => d.x).attr("y", d => d.y);
});

// Stats
const meta = graphData.metadata;
document.getElementById("stats").innerHTML =
  `${meta.total_theories} theories &middot; ${meta.total_syntheses} syntheses &middot; ${meta.total_links} links`;

// ─── Detail Panel ───────────────────────────────────────────────────────

function scoreColor(v) {
  if (v >= 0.7) return "#2ecc71";
  if (v >= 0.4) return "#f1c40f";
  return "#e74c3c";
}

function openPanel(d) {
  const panel = document.getElementById("detail-panel");
  const content = document.getElementById("detail-content");

  const stars = "★".repeat(Math.max(1, Math.round(d.score * 5))) +
                "☆".repeat(5 - Math.max(1, Math.round(d.score * 5)));

  let html = `
    <div class="dp-name">${d.name}</div>
    <div class="dp-parents">
      ${stars} &nbsp; Score: ${d.score}
    </div>

    <div class="dp-scores">
      <div class="dp-score-item">
        <div class="dp-score-val" style="color:${scoreColor(d.novelty)}">${d.novelty}</div>
        <div class="dp-score-label">Novelty</div>
      </div>
      <div class="dp-score-item">
        <div class="dp-score-val" style="color:${scoreColor(d.depth)}">${d.depth}</div>
        <div class="dp-score-label">Depth</div>
      </div>
      <div class="dp-score-item">
        <div class="dp-score-val" style="color:${scoreColor(d.impact)}">${d.impact}</div>
        <div class="dp-score-label">Impact</div>
      </div>
      <div class="dp-score-item">
        <div class="dp-score-val" style="color:#3498db">${d.collision_score}</div>
        <div class="dp-score-label">Collision</div>
      </div>
    </div>

    <div class="dp-section">
      <div class="dp-section-title">Core Equation</div>
      <div class="dp-equation">${d.core_equation}</div>
    </div>
  `;

  if (d.auxiliary_equations && d.auxiliary_equations.length) {
    html += `<div class="dp-section"><div class="dp-section-title">Auxiliary Equations</div>`;
    d.auxiliary_equations.forEach(eq => {
      html += `<div class="dp-equation aux">${eq}</div>`;
    });
    html += `</div>`;
  }

  html += `
    <div class="dp-section">
      <div class="dp-section-title">Update Mechanism</div>
      <div class="dp-mechanism">${d.update_mechanism}</div>
      <div class="dp-opt-target">Optimizes: ${d.optimization_target}</div>
    </div>
  `;

  if (d.backbone_patterns && d.backbone_patterns.length) {
    html += `<div class="dp-section"><div class="dp-section-title">Shared Backbone (${d.backbone_patterns.length})</div><ul class="dp-list patterns">`;
    d.backbone_patterns.forEach(p => { html += `<li>${p.replace(/_/g, ' ')}</li>`; });
    html += `</ul></div>`;
  }

  if (d.novel_patterns && d.novel_patterns.length) {
    html += `<div class="dp-section"><div class="dp-section-title">Novel Patterns (${d.novel_patterns.length})</div><ul class="dp-list novel">`;
    d.novel_patterns.forEach(p => { html += `<li>${p.replace(/_/g, ' ')}</li>`; });
    html += `</ul></div>`;
  }

  if (d.variables && Object.keys(d.variables).length) {
    html += `<div class="dp-section"><div class="dp-section-title">Variable Mapping</div><ul class="dp-list vars">`;
    Object.entries(d.variables).forEach(([role, meaning]) => {
      html += `<li><strong>${role}:</strong> ${meaning.replace(/_/g, ' ')}</li>`;
    });
    html += `</ul></div>`;
  }

  if (d.conservation_laws && d.conservation_laws.length) {
    html += `<div class="dp-section"><div class="dp-section-title">Conservation Laws</div><ul class="dp-list cons">`;
    d.conservation_laws.forEach(c => { html += `<li>d/dt [${c.replace(/_/g, ' ')}] = 0</li>`; });
    html += `</ul></div>`;
  }

  if (d.predicted_properties && d.predicted_properties.length) {
    html += `<div class="dp-section"><div class="dp-section-title">Predicted Properties</div><ul class="dp-list props">`;
    d.predicted_properties.forEach(p => { html += `<li>${p}</li>`; });
    html += `</ul></div>`;
  }

  if (d.research_directions && d.research_directions.length) {
    html += `<div class="dp-section"><div class="dp-section-title">Research Directions</div><ul class="dp-list dirs">`;
    d.research_directions.forEach(r => { html += `<li>${r}</li>`; });
    html += `</ul></div>`;
  }

  content.innerHTML = html;
  panel.classList.add("open");
}

function closePanel() {
  document.getElementById("detail-panel").classList.remove("open");
}

// Close panel on Escape
document.addEventListener("keydown", e => { if (e.key === "Escape") closePanel(); });

// Initial zoom
svg.transition().duration(800).call(
  zoom.transform,
  d3.zoomIdentity.translate(width * 0.05, height * 0.05).scale(0.9)
);
</script>
</body>
</html>"""
