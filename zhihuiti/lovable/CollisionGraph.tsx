/**
 * Theory Collision Map — Force-Directed Graph
 *
 * Drop this into a Lovable project. Dependencies:
 *   npm install d3 @types/d3
 *
 * Usage:
 *   <CollisionGraph />
 *   <CollisionGraph minScore={0.1} width={1200} height={800} />
 */
import React, { useRef, useEffect, useState, useCallback } from "react";
import * as d3 from "d3";
import {
  COLLISION_GRAPH_DATA,
  STRENGTH_COLORS,
  type GraphNode,
  type GraphLink,
} from "./collision-graph-data";

interface SimNode extends GraphNode, d3.SimulationNodeDatum {}
interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  score: number;
  strength: string;
  shared_patterns: string[];
  bridges: string[];
}

interface CollisionGraphProps {
  width?: number;
  height?: number;
  minScore?: number;
}

const CollisionGraph: React.FC<CollisionGraphProps> = ({
  width = typeof window !== "undefined" ? window.innerWidth : 1200,
  height = typeof window !== "undefined" ? window.innerHeight : 800,
  minScore: initialMinScore = 0.05,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [minScore, setMinScore] = useState(initialMinScore);
  const [linkOpacity, setLinkOpacity] = useState(0.6);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [hoveredLink, setHoveredLink] = useState<SimLink | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);

  const getActiveLinks = useCallback((): SimLink[] => {
    return COLLISION_GRAPH_DATA.links
      .filter((l) => l.score >= minScore)
      .map((l) => ({ ...l })) as SimLink[];
  }, [minScore]);

  const countLinks = useCallback(
    (nodeId: string, links: SimLink[]) => {
      return links.filter((l) => {
        const sid = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
        const tid = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
        return sid === nodeId || tid === nodeId;
      }).length;
    },
    []
  );

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Defs for glow
    const defs = svg.append("defs");
    const filter = defs.append("filter").attr("id", "glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "coloredBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    const g = svg.append("g");

    // Zoom
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on("zoom", (event) => g.attr("transform", event.transform));
    svg.call(zoom);

    const nodes: SimNode[] = COLLISION_GRAPH_DATA.nodes.map((n) => ({ ...n }));
    const links = getActiveLinks();

    // Simulation
    const simulation = d3.forceSimulation<SimNode>(nodes)
      .force(
        "link",
        d3.forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .distance((d) => 200 * (1 - d.score))
          .strength((d) => d.score * 0.8)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30))
      .force("x", d3.forceX(width / 2).strength(0.03))
      .force("y", d3.forceY(height / 2).strength(0.03));

    simulationRef.current = simulation;

    // Links
    const linkSel = g
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d) => STRENGTH_COLORS[d.strength] || "#333")
      .attr("stroke-width", (d) => Math.max(0.5, d.score * 8))
      .attr("stroke-opacity", linkOpacity)
      .style("cursor", "pointer")
      .on("mouseover", function (event, d) {
        d3.select(this).attr("stroke-opacity", 1).attr("stroke-width", d.score * 12);
        setHoveredLink(d);
        setHoveredNode(null);
        setTooltipPos({ x: event.clientX + 15, y: event.clientY + 15 });
      })
      .on("mouseout", function (event, d) {
        d3.select(this)
          .attr("stroke-opacity", linkOpacity)
          .attr("stroke-width", Math.max(0.5, d.score * 8));
        setHoveredLink(null);
      });

    // Nodes
    const nodeSel = g
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => Math.max(6, 4 + countLinks(d.id, links) * 1.5))
      .attr("fill", (d) => d.color)
      .attr("stroke", "#fff")
      .attr("stroke-width", 0.5)
      .attr("stroke-opacity", 0.3)
      .style("filter", "url(#glow)")
      .style("cursor", "pointer")
      .on("mouseover", function (event, d) {
        d3.select(this).attr("stroke-width", 2).attr("stroke-opacity", 1);
        linkSel.attr("stroke-opacity", (l) => {
          const sid = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
          const tid = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
          return sid === d.id || tid === d.id ? 1 : 0.05;
        });
        setHoveredNode(d);
        setHoveredLink(null);
        setTooltipPos({ x: event.clientX + 15, y: event.clientY - 10 });
      })
      .on("mouseout", function () {
        d3.select(this).attr("stroke-width", 0.5).attr("stroke-opacity", 0.3);
        linkSel.attr("stroke-opacity", linkOpacity);
        setHoveredNode(null);
      })
      .call(
        d3.drag<SVGCircleElement, SimNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Labels
    const labelSel = g
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => (d.name.length > 25 ? d.name.slice(0, 23) + "…" : d.name))
      .attr("font-size", 9)
      .attr("fill", "#999")
      .attr("dx", 12)
      .attr("dy", 3)
      .style("pointer-events", "none")
      .style("font-family", "'Inter', -apple-system, sans-serif");

    simulation.on("tick", () => {
      linkSel
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);
      nodeSel.attr("cx", (d) => d.x!).attr("cy", (d) => d.y!);
      labelSel.attr("x", (d) => d.x!).attr("y", (d) => d.y!);
    });

    // Initial zoom
    svg
      .transition()
      .duration(1000)
      .call(
        zoom.transform,
        d3.zoomIdentity.translate(width * 0.05, height * 0.05).scale(0.9)
      );

    return () => {
      simulation.stop();
    };
  }, [width, height, minScore, linkOpacity, getActiveLinks, countLinks]);

  const activeLinks = getActiveLinks();
  const deepCount = activeLinks.filter((l) => l.strength === "deep").length;
  const sigCount = activeLinks.filter((l) => l.strength === "significant").length;
  const resCount = activeLinks.filter((l) => l.strength === "resonance").length;

  const domains = [...new Set(COLLISION_GRAPH_DATA.nodes.map((n) => n.domain))];

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", background: "#0a0a1a", overflow: "hidden" }}>
      {/* Header */}
      <div
        style={{
          position: "absolute", top: 0, left: 0, right: 0, zIndex: 10,
          padding: "16px 24px",
          background: "linear-gradient(180deg, rgba(10,10,26,0.95) 0%, rgba(10,10,26,0) 100%)",
          pointerEvents: "none",
        }}
      >
        <h1
          style={{
            fontSize: 20, fontWeight: 600, letterSpacing: 0.5, margin: 0,
            background: "linear-gradient(135deg, #3498db, #e74c3c)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}
        >
          Theory Collision Map
        </h1>
        <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
          Force-directed graph of cross-domain mathematical isomorphisms
        </div>
      </div>

      {/* Controls */}
      <div style={{ position: "absolute", top: 70, left: 24, zIndex: 10, display: "flex", flexDirection: "column", gap: 8 }}>
        <div>
          <label style={{ fontSize: 11, color: "#888" }}>
            Min collision score:{" "}
            <span style={{ color: "#3498db" }}>{minScore.toFixed(2)}</span>
          </label>
          <br />
          <input
            type="range" min={0} max={0.6} step={0.02} value={minScore}
            onChange={(e) => setMinScore(+e.target.value)}
            style={{ width: 180, accentColor: "#3498db" }}
          />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "#888" }}>
            Link opacity:{" "}
            <span style={{ color: "#3498db" }}>{linkOpacity.toFixed(2)}</span>
          </label>
          <br />
          <input
            type="range" min={0.05} max={1} step={0.05} value={linkOpacity}
            onChange={(e) => setLinkOpacity(+e.target.value)}
            style={{ width: 180, accentColor: "#3498db" }}
          />
        </div>
      </div>

      {/* Stats */}
      <div style={{ position: "absolute", top: 70, right: 24, zIndex: 10, fontSize: 11, color: "#555", textAlign: "right" }}>
        {COLLISION_GRAPH_DATA.nodes.length} theories · {activeLinks.length} collisions
        <br />
        <span style={{ color: "#e74c3c" }}>{deepCount} deep</span>
        {" · "}
        <span style={{ color: "#e67e22" }}>{sigCount} significant</span>
        {" · "}
        <span style={{ color: "#3498db" }}>{resCount} resonance</span>
      </div>

      {/* Legend */}
      <div
        style={{
          position: "absolute", bottom: 20, left: 24, zIndex: 10,
          display: "flex", flexWrap: "wrap", gap: 10, maxWidth: 500,
        }}
      >
        {domains.map((domain) => {
          const node = COLLISION_GRAPH_DATA.nodes.find((n) => n.domain === domain);
          return (
            <div key={domain} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "#aaa" }}>
              <div
                style={{
                  width: 10, height: 10, borderRadius: "50%",
                  background: node?.color || "#95a5a6",
                }}
              />
              {domain}
            </div>
          );
        })}
      </div>

      {/* Node tooltip */}
      {hoveredNode && (
        <div
          style={{
            position: "fixed", left: tooltipPos.x, top: tooltipPos.y,
            padding: "12px 16px",
            background: "rgba(20, 20, 40, 0.95)",
            border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: 8, fontSize: 12, lineHeight: 1.5,
            maxWidth: 360, pointerEvents: "none", zIndex: 20,
            backdropFilter: "blur(10px)", color: "#e0e0e0",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{hoveredNode.name}</div>
          <div style={{ fontSize: 11, color: "#888", marginBottom: 6 }}>{hoveredNode.domain}</div>
          {hoveredNode.equation && (
            <code
              style={{
                fontFamily: "'Courier New', monospace", fontSize: 11,
                color: "#f39c12", background: "rgba(0,0,0,0.3)",
                padding: "4px 8px", borderRadius: 4, marginBottom: 6,
                display: "block", wordBreak: "break-all",
              }}
            >
              {hoveredNode.equation}
            </code>
          )}
          <div style={{ fontSize: 11, color: "#aaa" }}>
            {countLinks(hoveredNode.id, activeLinks)} collision
            {countLinks(hoveredNode.id, activeLinks) !== 1 ? "s" : ""} above threshold
          </div>
        </div>
      )}

      {/* Edge tooltip */}
      {hoveredLink && (
        <div
          style={{
            position: "fixed", left: tooltipPos.x, top: tooltipPos.y,
            padding: "10px 14px",
            background: "rgba(20, 20, 40, 0.95)",
            border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: 8, fontSize: 11, lineHeight: 1.6,
            maxWidth: 340, pointerEvents: "none", zIndex: 20,
            backdropFilter: "blur(10px)", color: "#e0e0e0",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
            {typeof hoveredLink.source === "object" ? (hoveredLink.source as SimNode).name : hoveredLink.source}
            {" ↔ "}
            {typeof hoveredLink.target === "object" ? (hoveredLink.target as SimNode).name : hoveredLink.target}
          </div>
          <div style={{ color: "#3498db" }}>
            Score: {hoveredLink.score.toFixed(3)} ({hoveredLink.strength.toUpperCase()})
          </div>
          {hoveredLink.shared_patterns.length > 0 && (
            <div style={{ color: "#2ecc71", fontSize: 10 }}>
              Shared: {hoveredLink.shared_patterns.map((p) => p.replace(/_/g, " ")).join(", ")}
            </div>
          )}
          {hoveredLink.bridges.length > 0 && (
            <div style={{ color: "#e67e22", fontSize: 10, marginTop: 4 }}>
              {hoveredLink.bridges.map((b, i) => (
                <div key={i}>&rarr; {b}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SVG Canvas */}
      <svg ref={svgRef} width={width} height={height} />
    </div>
  );
};

export default CollisionGraph;
