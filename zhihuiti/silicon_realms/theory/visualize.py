"""
Collision Map Visualization
============================
Export theory collision data as JSON for D3.js force-directed graph,
and generate a standalone interactive HTML visualization.

Usage:
    python -m silicon_realms.theory.visualize          # writes collision_map.html
    python -m silicon_realms.theory.visualize --json    # writes collision_map.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .collision_engine import THEORY_REGISTRY, collide, list_theories


# Domain → color mapping for visual clustering
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


def collision_graph_json(min_score: float = 0.08) -> dict:
    """
    Build a JSON-serializable graph of theory collisions.

    Returns:
        {
            "nodes": [{"id": str, "name": str, "domain": str, "color": str, "equation": str}, ...],
            "links": [{"source": str, "target": str, "score": float, "strength": str, "shared": [...], "bridges": [...]}, ...],
            "metadata": {"total_theories": int, "total_links": int, "min_score": float}
        }
    """
    keys = list_theories()

    nodes = []
    for key in keys:
        t = THEORY_REGISTRY[key]
        nodes.append({
            "id": key,
            "name": t["display_name"],
            "domain": t["domain"],
            "color": DOMAIN_COLORS.get(t["domain"], "#95a5a6"),
            "equation": t.get("equation", ""),
        })

    links = []
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            report = collide(ka, kb)
            if report.similarity_score >= min_score:
                links.append({
                    "source": ka,
                    "target": kb,
                    "score": round(report.similarity_score, 4),
                    "strength": report.collision_strength,
                    "shared_patterns": report.shared_patterns[:5],
                    "bridges": report.structural_bridges[:3],
                })

    return {
        "nodes": nodes,
        "links": links,
        "metadata": {
            "total_theories": len(nodes),
            "total_links": len(links),
            "min_score": min_score,
        },
    }


def generate_html(output_path: str | Path = "collision_map.html", min_score: float = 0.08) -> Path:
    """Generate a standalone HTML file with an interactive D3.js force-directed graph."""
    graph_data = collision_graph_json(min_score)
    json_str = json.dumps(graph_data, indent=2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Theory Collision Map — Silicon Realms</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0a0a1a;
    color: #e0e0e0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    overflow: hidden;
  }}
  #header {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 10;
    padding: 16px 24px;
    background: linear-gradient(180deg, rgba(10,10,26,0.95) 0%, rgba(10,10,26,0) 100%);
    pointer-events: none;
  }}
  #header h1 {{
    font-size: 20px; font-weight: 600; letter-spacing: 0.5px;
    background: linear-gradient(135deg, #3498db, #e74c3c);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    pointer-events: auto;
  }}
  #header .subtitle {{ font-size: 12px; color: #666; margin-top: 4px; }}
  #controls {{
    position: fixed; top: 70px; left: 24px; z-index: 10;
    display: flex; flex-direction: column; gap: 8px;
  }}
  #controls label {{
    font-size: 11px; color: #888;
  }}
  #controls input[type=range] {{
    width: 180px; accent-color: #3498db;
  }}
  #controls .value {{ font-size: 11px; color: #3498db; }}
  #legend {{
    position: fixed; bottom: 20px; left: 24px; z-index: 10;
    display: flex; flex-wrap: wrap; gap: 10px; max-width: 400px;
  }}
  .legend-item {{
    display: flex; align-items: center; gap: 5px; font-size: 11px; color: #aaa;
  }}
  .legend-dot {{
    width: 10px; height: 10px; border-radius: 50%;
  }}
  #tooltip {{
    position: fixed;
    padding: 12px 16px;
    background: rgba(20, 20, 40, 0.95);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    font-size: 12px;
    line-height: 1.5;
    max-width: 360px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 20;
    backdrop-filter: blur(10px);
  }}
  #tooltip .tt-name {{
    font-weight: 600; font-size: 14px; margin-bottom: 4px;
  }}
  #tooltip .tt-domain {{
    font-size: 11px; color: #888; margin-bottom: 6px;
  }}
  #tooltip .tt-eq {{
    font-family: 'Courier New', monospace; font-size: 11px;
    color: #f39c12; background: rgba(0,0,0,0.3);
    padding: 4px 8px; border-radius: 4px; margin-bottom: 6px;
    display: block; word-break: break-all;
  }}
  #tooltip .tt-links {{
    font-size: 11px; color: #aaa;
  }}
  #edge-tooltip {{
    position: fixed;
    padding: 10px 14px;
    background: rgba(20, 20, 40, 0.95);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    font-size: 11px;
    line-height: 1.6;
    max-width: 340px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 20;
    backdrop-filter: blur(10px);
  }}
  #edge-tooltip .et-title {{
    font-weight: 600; font-size: 13px; margin-bottom: 4px;
  }}
  #edge-tooltip .et-score {{
    color: #3498db;
  }}
  #edge-tooltip .et-patterns {{
    color: #2ecc71; font-size: 10px;
  }}
  #edge-tooltip .et-bridges {{
    color: #e67e22; font-size: 10px; margin-top: 4px;
  }}
  #stats {{
    position: fixed; top: 70px; right: 24px; z-index: 10;
    font-size: 11px; color: #555; text-align: right;
  }}
  svg {{ width: 100vw; height: 100vh; }}
</style>
</head>
<body>

<div id="header">
  <h1>Theory Collision Map</h1>
  <div class="subtitle">Force-directed graph of cross-domain mathematical isomorphisms</div>
</div>

<div id="controls">
  <div>
    <label>Min collision score: <span class="value" id="threshold-val">0.08</span></label>
    <input type="range" id="threshold" min="0" max="0.6" step="0.02" value="0.08">
  </div>
  <div>
    <label>Link opacity: <span class="value" id="opacity-val">0.6</span></label>
    <input type="range" id="link-opacity" min="0.05" max="1" step="0.05" value="0.6">
  </div>
</div>

<div id="stats"></div>
<div id="legend"></div>
<div id="tooltip"></div>
<div id="edge-tooltip"></div>

<svg></svg>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const graphData = {json_str};

const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("svg")
  .attr("width", width)
  .attr("height", height);

// Defs for glow effect
const defs = svg.append("defs");
const filter = defs.append("filter").attr("id", "glow");
filter.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "coloredBlur");
const feMerge = filter.append("feMerge");
feMerge.append("feMergeNode").attr("in", "coloredBlur");
feMerge.append("feMergeNode").attr("in", "SourceGraphic");

// Container for zoom
const g = svg.append("g");

// Zoom behavior
const zoom = d3.zoom()
  .scaleExtent([0.2, 5])
  .on("zoom", (event) => g.attr("transform", event.transform));
svg.call(zoom);

// Strength color scale
const strengthColor = {{
  "deep": "#e74c3c",
  "significant": "#e67e22",
  "resonance": "#3498db",
  "weak": "#2c3e50"
}};

// State
let currentThreshold = 0.08;
let currentOpacity = 0.6;
let nodes = graphData.nodes.map(d => ({{...d}}));
let allLinks = graphData.links.map(d => ({{...d}}));

function getActiveLinks() {{
  return allLinks.filter(l => l.score >= currentThreshold);
}}

// Count links per node
function countLinks(nodeId, links) {{
  return links.filter(l =>
    (typeof l.source === 'object' ? l.source.id : l.source) === nodeId ||
    (typeof l.target === 'object' ? l.target.id : l.target) === nodeId
  ).length;
}}

// Simulation
let simulation, linkSel, nodeSel, labelSel;

function buildGraph() {{
  const links = getActiveLinks();

  g.selectAll("*").remove();

  simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(d => 200 * (1 - d.score)).strength(d => d.score * 0.8))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(30))
    .force("x", d3.forceX(width / 2).strength(0.03))
    .force("y", d3.forceY(height / 2).strength(0.03));

  // Links
  linkSel = g.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", d => strengthColor[d.strength] || "#333")
    .attr("stroke-width", d => Math.max(0.5, d.score * 8))
    .attr("stroke-opacity", currentOpacity)
    .on("mouseover", function(event, d) {{
      d3.select(this).attr("stroke-opacity", 1).attr("stroke-width", d.score * 12);
      const tt = document.getElementById("edge-tooltip");
      const srcName = typeof d.source === 'object' ? d.source.name : d.source;
      const tgtName = typeof d.target === 'object' ? d.target.name : d.target;
      tt.innerHTML = `
        <div class="et-title">${{srcName}} ↔ ${{tgtName}}</div>
        <div class="et-score">Score: ${{d.score.toFixed(3)}} (${{d.strength.toUpperCase()}})</div>
        ${{d.shared_patterns.length ? '<div class="et-patterns">Shared: ' + d.shared_patterns.map(p => p.replace(/_/g, ' ')).join(', ') + '</div>' : ''}}
        ${{d.bridges.length ? '<div class="et-bridges">' + d.bridges.map(b => '→ ' + b).join('<br>') + '</div>' : ''}}
      `;
      tt.style.opacity = 1;
      tt.style.left = (event.clientX + 15) + "px";
      tt.style.top = (event.clientY + 15) + "px";
    }})
    .on("mouseout", function(event, d) {{
      d3.select(this).attr("stroke-opacity", currentOpacity).attr("stroke-width", Math.max(0.5, d.score * 8));
      document.getElementById("edge-tooltip").style.opacity = 0;
    }});

  // Nodes
  nodeSel = g.append("g")
    .selectAll("circle")
    .data(nodes)
    .join("circle")
    .attr("r", d => {{
      const lc = countLinks(d.id, links);
      return Math.max(6, 4 + lc * 1.5);
    }})
    .attr("fill", d => d.color)
    .attr("stroke", "#fff")
    .attr("stroke-width", 0.5)
    .attr("stroke-opacity", 0.3)
    .style("filter", "url(#glow)")
    .style("cursor", "pointer")
    .on("mouseover", function(event, d) {{
      d3.select(this).attr("stroke-width", 2).attr("stroke-opacity", 1).attr("r", function() {{
        return +d3.select(this).attr("r") + 3;
      }});
      // Highlight connected links
      linkSel.attr("stroke-opacity", l => {{
        const sid = typeof l.source === 'object' ? l.source.id : l.source;
        const tid = typeof l.target === 'object' ? l.target.id : l.target;
        return (sid === d.id || tid === d.id) ? 1 : 0.05;
      }});
      const lc = countLinks(d.id, links);
      const tt = document.getElementById("tooltip");
      tt.innerHTML = `
        <div class="tt-name">${{d.name}}</div>
        <div class="tt-domain">${{d.domain}}</div>
        ${{d.equation ? '<code class="tt-eq">' + d.equation + '</code>' : ''}}
        <div class="tt-links">${{lc}} collision${{lc !== 1 ? 's' : ''}} above threshold</div>
      `;
      tt.style.opacity = 1;
      tt.style.left = (event.clientX + 15) + "px";
      tt.style.top = (event.clientY - 10) + "px";
    }})
    .on("mouseout", function(event, d) {{
      d3.select(this).attr("stroke-width", 0.5).attr("stroke-opacity", 0.3).attr("r", function() {{
        return +d3.select(this).attr("r") - 3;
      }});
      linkSel.attr("stroke-opacity", currentOpacity);
      document.getElementById("tooltip").style.opacity = 0;
    }})
    .call(d3.drag()
      .on("start", (event, d) => {{
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      }})
      .on("drag", (event, d) => {{
        d.fx = event.x; d.fy = event.y;
      }})
      .on("end", (event, d) => {{
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      }})
    );

  // Labels
  labelSel = g.append("g")
    .selectAll("text")
    .data(nodes)
    .join("text")
    .text(d => d.name.length > 25 ? d.name.slice(0, 23) + '…' : d.name)
    .attr("font-size", 9)
    .attr("fill", "#999")
    .attr("dx", 12)
    .attr("dy", 3)
    .style("pointer-events", "none");

  simulation.on("tick", () => {{
    linkSel
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);
    nodeSel
      .attr("cx", d => d.x)
      .attr("cy", d => d.y);
    labelSel
      .attr("x", d => d.x)
      .attr("y", d => d.y);
  }});

  // Stats
  const deepCount = links.filter(l => l.strength === "deep").length;
  const sigCount = links.filter(l => l.strength === "significant").length;
  document.getElementById("stats").innerHTML =
    `${{nodes.length}} theories · ${{links.length}} collisions<br>` +
    `<span style="color:#e74c3c">${{deepCount}} deep</span> · ` +
    `<span style="color:#e67e22">${{sigCount}} significant</span>`;
}}

// Legend
const domains = [...new Set(graphData.nodes.map(n => n.domain))];
const legendEl = document.getElementById("legend");
domains.forEach(d => {{
  const color = graphData.nodes.find(n => n.domain === d)?.color || "#95a5a6";
  legendEl.innerHTML += `<div class="legend-item"><div class="legend-dot" style="background:${{color}}"></div>${{d}}</div>`;
}});

// Controls
document.getElementById("threshold").addEventListener("input", function() {{
  currentThreshold = +this.value;
  document.getElementById("threshold-val").textContent = this.value;
  buildGraph();
}});

document.getElementById("link-opacity").addEventListener("input", function() {{
  currentOpacity = +this.value;
  document.getElementById("opacity-val").textContent = this.value;
  linkSel.attr("stroke-opacity", currentOpacity);
}});

// Initial build
buildGraph();

// Gentle initial zoom
svg.transition().duration(1000).call(
  zoom.transform,
  d3.zoomIdentity.translate(width * 0.05, height * 0.05).scale(0.9)
);
</script>
</body>
</html>"""

    out = Path(output_path)
    out.write_text(html, encoding="utf-8")
    return out.resolve()


def export_json(output_path: str | Path = "collision_map.json", min_score: float = 0.08) -> Path:
    """Export collision graph data as JSON."""
    data = collision_graph_json(min_score)
    out = Path(output_path)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out.resolve()


if __name__ == "__main__":
    import sys
    if "--json" in sys.argv:
        p = export_json()
        print(f"Exported collision graph JSON → {p}")
    else:
        p = generate_html()
        print(f"Generated collision map → {p}")
        print(f"Open in browser: file://{p}")
