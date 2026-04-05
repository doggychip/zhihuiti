import { useState, useRef, useCallback } from "react";

interface LeaderboardAgent {
  id: string;
  role: string;
  budget: number;
  avg_score: number;
  alive: boolean;
  realm: string;
  tasks: number;
  name?: string;
  group?: "zhihuiti" | "hedge_fund";
}

interface LeaderboardTableProps {
  agents: LeaderboardAgent[];
  handleSelect: (id: string) => void;
  REALM_COLORS: Record<string, string>;
}

const INITIAL_BUDGET = 100;

const ROLE_COLORS: Record<string, string> = {
  trader: "#f97316",
  strategist: "#a855f7",
  analyst: "#3b82f6",
  researcher: "#22c55e",
  coordinator: "#eab308",
  auditor: "#ef4444",
  coder: "#06b6d4",
  custom: "#ec4899",
};

const COLUMNS = [
  { key: "rank", label: "#", align: "left" as const, minWidth: 32, defaultWidth: 36 },
  { key: "agent", label: "Agent", align: "left" as const, minWidth: 80, defaultWidth: 160 },
  { key: "return", label: "Return %", align: "right" as const, minWidth: 60, defaultWidth: 80 },
  { key: "sharpe", label: "Sharpe", align: "right" as const, minWidth: 50, defaultWidth: 68 },
  { key: "winrate", label: "Win Rate", align: "right" as const, minWidth: 56, defaultWidth: 76 },
  { key: "score", label: "Score", align: "right" as const, minWidth: 50, defaultWidth: 64 },
];

export function LeaderboardTable({ agents, handleSelect, REALM_COLORS }: LeaderboardTableProps) {
  const [colWidths, setColWidths] = useState<number[]>(COLUMNS.map(c => c.defaultWidth));
  const [showZhihuiti, setShowZhihuiti] = useState(true);
  const [showHedgeFund, setShowHedgeFund] = useState(true);
  const [hiddenRoles, setHiddenRoles] = useState<Set<string>>(new Set());

  const allRoles = [...new Set(agents.filter(a => a.alive).map(a => a.role))].sort();

  const toggleRole = (role: string) => {
    setHiddenRoles(prev => {
      const next = new Set(prev);
      if (next.has(role)) next.delete(role); else next.add(role);
      return next;
    });
  };
  const dragRef = useRef<{ colIndex: number; startX: number; startWidth: number } | null>(null);

  const onMouseDown = useCallback((e: React.MouseEvent, colIndex: number) => {
    e.preventDefault();
    dragRef.current = { colIndex, startX: e.clientX, startWidth: colWidths[colIndex] };

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const delta = ev.clientX - dragRef.current.startX;
      const newWidth = Math.max(COLUMNS[dragRef.current.colIndex].minWidth, dragRef.current.startWidth + delta);
      setColWidths(prev => {
        if (!dragRef.current) return prev;
        const next = [...prev];
        next[dragRef.current.colIndex] = newWidth;
        return next;
      });
    };

    const onMouseUp = () => {
      dragRef.current = null;
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  }, [colWidths]);

  const leaderboardData = [...agents]
    .filter(a => a.alive)
    .filter(a => {
      if (a.group === "zhihuiti") return showZhihuiti;
      if (a.group === "hedge_fund") return showHedgeFund;
      return true;
    })
    .filter(a => !hiddenRoles.has(a.role))
    .map(a => {
      const returnPct = ((a.budget - INITIAL_BUDGET) / INITIAL_BUDGET) * 100;
      const sharpe = a.tasks > 0 ? (a.avg_score - 0.5) / Math.max(0.1, 1 - a.avg_score) : 0;
      const winRate = a.avg_score;
      const score = (a.avg_score * 0.4) + (Math.max(0, returnPct) / 100 * 0.3) + (winRate * 0.3);
      return { ...a, returnPct, sharpe, winRate, score };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 20);

  const zhihuiCount = agents.filter(a => a.alive && a.group === "zhihuiti").length;
  const hedgeCount = agents.filter(a => a.alive && a.group === "hedge_fund").length;

  return (
    <div>
      <div className="flex gap-1.5 pb-2">
        <button
          onClick={() => setShowZhihuiti(v => !v)}
          className="text-[10px] px-2 py-0.5 rounded-full transition-all"
          style={{
            background: showZhihuiti ? "rgba(234,179,8,0.15)" : "rgba(255,255,255,0.04)",
            color: showZhihuiti ? "#eab308" : "rgba(255,255,255,0.3)",
            border: `1px solid ${showZhihuiti ? "rgba(234,179,8,0.3)" : "rgba(255,255,255,0.08)"}`,
          }}
        >
          🟡 ZhihuiTi ({zhihuiCount})
        </button>
        <button
          onClick={() => setShowHedgeFund(v => !v)}
          className="text-[10px] px-2 py-0.5 rounded-full transition-all"
          style={{
            background: showHedgeFund ? "rgba(59,130,246,0.15)" : "rgba(255,255,255,0.04)",
            color: showHedgeFund ? "#3b82f6" : "rgba(255,255,255,0.3)",
            border: `1px solid ${showHedgeFund ? "rgba(59,130,246,0.3)" : "rgba(255,255,255,0.08)"}`,
          }}
        >
          🔵 Hedge Fund ({hedgeCount})
        </button>
      </div>
      <div className="flex gap-1 pb-2 flex-wrap">
        {allRoles.map(role => {
          const active = !hiddenRoles.has(role);
          const color = ROLE_COLORS[role] || "#888";
          const count = agents.filter(a => a.alive && a.role === role).length;
          return (
            <button
              key={role}
              onClick={() => toggleRole(role)}
              className="text-[9px] px-1.5 py-0.5 rounded-full transition-all capitalize"
              style={{
                background: active ? `${color}22` : "rgba(255,255,255,0.04)",
                color: active ? color : "rgba(255,255,255,0.25)",
                border: `1px solid ${active ? `${color}44` : "rgba(255,255,255,0.08)"}`,
              }}
            >
              {role} ({count})
            </button>
          );
        })}
      </div>
      <div className="overflow-x-auto max-h-52 overflow-y-auto">
      <table className="text-xs" style={{ borderCollapse: "separate", borderSpacing: 0, tableLayout: "fixed", width: colWidths.reduce((s, w) => s + w, 0) }}>
        <thead>
          <tr style={{ color: "rgba(255,255,255,0.35)" }}>
            {COLUMNS.map((col, i) => (
              <th
                key={col.key}
                className={`py-1.5 px-2 font-medium sticky top-0 select-none ${col.align === "right" ? "text-right" : "text-left"}`}
                style={{ background: "#0d0d1a", width: colWidths[i], position: "relative" }}
              >
                {col.label}
                <div
                  onMouseDown={e => onMouseDown(e, i)}
                  style={{
                    position: "absolute",
                    right: -4,
                    top: 0,
                    bottom: 0,
                    width: 9,
                    cursor: "col-resize",
                    background: "transparent",
                    zIndex: 2,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(167,139,250,0.4)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {leaderboardData.map((agent, i) => {
            const isPositive = agent.returnPct >= 0;
            return (
              <tr
                key={agent.id}
                className="transition-colors cursor-pointer"
                style={{ background: i % 2 === 0 ? "rgba(255,255,255,0.02)" : "transparent" }}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(167,139,250,0.08)")}
                onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? "rgba(255,255,255,0.02)" : "transparent")}
                onClick={() => handleSelect(agent.id)}
              >
                <td className="py-1.5 px-2 font-mono" style={{ color: i < 3 ? "#eab308" : "rgba(255,255,255,0.3)", width: colWidths[0] }}>
                  {i + 1}
                </td>
                <td className="py-1.5 px-2 text-white font-medium truncate" style={{ width: colWidths[1] }}>
                  <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: agent.group === "zhihuiti" ? "#eab308" : agent.group === "hedge_fund" ? "#3b82f6" : REALM_COLORS[agent.realm] }} />
                  {agent.name || agent.role} <span style={{ color: "rgba(255,255,255,0.2)" }}>#{agent.id.slice(0, 4)}</span>
                </td>
                <td className="py-1.5 px-2 text-right font-mono" style={{ color: isPositive ? "#22c55e" : "#ef4444", width: colWidths[2] }}>
                  {isPositive ? "+" : ""}{agent.returnPct.toFixed(1)}%
                </td>
                <td className="py-1.5 px-2 text-right font-mono text-white/70" style={{ width: colWidths[3] }}>
                  {agent.sharpe.toFixed(2)}
                </td>
                <td className="py-1.5 px-2 text-right font-mono text-white/70" style={{ width: colWidths[4] }}>
                  {(agent.winRate * 100).toFixed(1)}%
                </td>
                <td className="py-1.5 px-2 text-right font-mono" style={{ color: "#a78bfa", width: colWidths[5] }}>
                  {agent.score.toFixed(2)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}
