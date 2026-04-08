"use client";

import { motion } from "framer-motion";

const NODES = [
  { id: "oracle", label: "Oracle", angle: 0 },
  { id: "spark", label: "Spark", angle: 60 },
  { id: "sentinel", label: "Sentinel", angle: 120 },
  { id: "architect", label: "Architect", angle: 180 },
  { id: "merchant", label: "Merchant", angle: 240 },
  { id: "scholar", label: "Scholar", angle: 300 },
];

const RING_RADIUS = 120;

export { NODES };

export default function OntologyGraph() {
  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
      className="relative"
      style={{ width: RING_RADIUS * 2 + 60, height: RING_RADIUS * 2 + 60 }}
    >
      {/* 外環 */}
      <div className="absolute inset-0 rounded-full border border-ice/10 animate-breathe" />

      {/* 中環 */}
      <div
        className="absolute rounded-full border border-ice/5"
        style={{
          top: "15%",
          left: "15%",
          width: "70%",
          height: "70%",
        }}
      />

      {/* 核心光點 */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
        <div className="w-3 h-3 bg-gold rounded-full shadow-[0_0_12px_#F59E0B,0_0_24px_rgba(245,158,11,0.3)]" />
      </div>

      {/* Agent 節點 */}
      {NODES.map((node) => {
        const rad = (node.angle * Math.PI) / 180;
        const x = Math.cos(rad) * RING_RADIUS;
        const y = Math.sin(rad) * RING_RADIUS;
        return (
          <div
            key={node.id}
            className="absolute flex flex-col items-center gap-1"
            style={{
              top: `calc(50% + ${y}px - 8px)`,
              left: `calc(50% + ${x}px - 8px)`,
            }}
          >
            <div className="w-2 h-2 rounded-full bg-ice/60 shadow-[0_0_6px_rgba(96,165,250,0.4)]" />
            <span className="text-[8px] tracking-widest uppercase opacity-40 whitespace-nowrap">
              {node.label}
            </span>
          </div>
        );
      })}

      {/* 連接線 (SVG) */}
      <svg
        className="absolute inset-0 w-full h-full"
        viewBox={`0 0 ${RING_RADIUS * 2 + 60} ${RING_RADIUS * 2 + 60}`}
      >
        {NODES.map((node) => {
          const cx = RING_RADIUS + 30;
          const cy = RING_RADIUS + 30;
          const rad = (node.angle * Math.PI) / 180;
          const x = cx + Math.cos(rad) * RING_RADIUS;
          const y = cy + Math.sin(rad) * RING_RADIUS;
          return (
            <line
              key={node.id}
              x1={cx}
              y1={cy}
              x2={x}
              y2={y}
              stroke="rgba(96,165,250,0.08)"
              strokeWidth="0.5"
            />
          );
        })}
      </svg>
    </motion.div>
  );
}
