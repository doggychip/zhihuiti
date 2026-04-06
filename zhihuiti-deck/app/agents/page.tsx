"use client";

import { motion } from "framer-motion";
import StatusBar from "@/components/StatusBar";

const AGENTS = [
  {
    id: "oracle",
    name: "Oracle",
    role: "coordinator",
    realm: "中枢界",
    realmEn: "Central",
    status: "active",
    tokens: 847,
    score: 0.92,
    tasks: 156,
    gen: 3,
  },
  {
    id: "spark",
    name: "Spark",
    role: "researcher",
    realm: "研发界",
    realmEn: "Research",
    status: "active",
    tokens: 623,
    score: 0.87,
    tasks: 98,
    gen: 2,
  },
  {
    id: "sentinel",
    name: "Sentinel",
    role: "auditor",
    realm: "中枢界",
    realmEn: "Central",
    status: "active",
    tokens: 510,
    score: 0.85,
    tasks: 201,
    gen: 4,
  },
  {
    id: "architect",
    name: "Architect",
    role: "strategist",
    realm: "中枢界",
    realmEn: "Central",
    status: "idle",
    tokens: 392,
    score: 0.81,
    tasks: 67,
    gen: 2,
  },
  {
    id: "merchant",
    name: "Merchant",
    role: "trader",
    realm: "执行界",
    realmEn: "Execution",
    status: "active",
    tokens: 1204,
    score: 0.94,
    tasks: 312,
    gen: 5,
  },
  {
    id: "scholar",
    name: "Scholar",
    role: "analyst",
    realm: "研发界",
    realmEn: "Research",
    status: "idle",
    tokens: 275,
    score: 0.78,
    tasks: 44,
    gen: 1,
  },
];

function ScoreBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.85 ? "bg-gold" : value >= 0.7 ? "bg-ice/60" : "bg-ice/30";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1 bg-ice/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[9px] text-ice/40 w-8">{pct}%</span>
    </div>
  );
}

export default function AgentsPage() {
  return (
    <div className="bg-midnight min-h-screen px-6 py-16">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-12"
        >
          <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-2">Agent Registry</p>
          <h1 className="text-lg tracking-wide font-light text-ice">
            Active Agent Population
          </h1>
          <p className="text-[10px] text-ice/30 tracking-wide mt-2">
            {AGENTS.filter((a) => a.status === "active").length} active · {AGENTS.length} total · Generation {Math.max(...AGENTS.map((a) => a.gen))} max
          </p>
        </motion.div>

        {/* Agent Cards */}
        <div className="space-y-3">
          {AGENTS.map((agent, i) => (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08, duration: 0.5 }}
              className="border border-ice/8 rounded-lg p-5 bg-ice-dim hover:border-ice/20 transition-colors"
            >
              <div className="flex items-start justify-between flex-wrap gap-4">
                {/* Left: identity */}
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className={`w-2.5 h-2.5 rounded-full ${agent.status === "active" ? "bg-gold shadow-[0_0_8px_rgba(245,158,11,0.4)]" : "bg-ice/20"}`} />
                  </div>
                  <div>
                    <p className="text-[12px] text-ice tracking-widest uppercase">{agent.name}</p>
                    <p className="text-[9px] text-ice/30 tracking-wide mt-0.5">
                      {agent.role} · {agent.realm} <span className="text-ice/15">({agent.realmEn})</span>
                    </p>
                  </div>
                </div>

                {/* Right: stats */}
                <div className="flex items-center gap-8">
                  <div className="text-right">
                    <p className="text-[9px] text-ice/25 tracking-widest uppercase">Tokens</p>
                    <p className="text-[11px] text-ice/60 font-mono">{agent.tokens.toLocaleString()}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[9px] text-ice/25 tracking-widest uppercase">Tasks</p>
                    <p className="text-[11px] text-ice/60 font-mono">{agent.tasks}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[9px] text-ice/25 tracking-widest uppercase">Gen</p>
                    <p className="text-[11px] text-ice/60 font-mono">{agent.gen}</p>
                  </div>
                  <div>
                    <p className="text-[9px] text-ice/25 tracking-widest uppercase mb-1">Score</p>
                    <ScoreBar value={agent.score} />
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      <StatusBar />
    </div>
  );
}
