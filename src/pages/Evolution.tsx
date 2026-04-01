import { useMemo } from "react";
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend
} from "recharts";
import { Link } from "react-router-dom";

// ── Mock Data (replace with API calls later) ────────────────────

const mockSummary = {
  totalEpochs: 50,
  latestEpoch: 50,
  population: 17,
  avgFitness: 0.42,
  moneySupply: 8200,
  gini: 0.34,
  archetypes: { specialist: 5, generalist: 8, trader: 2, predator: 2 },
  topAgents: [
    { agentId: "3f2a8b1c", archetype: "specialist", fitness: 0.89, genome: { bid_aggression: 0.35, risk_tolerance: 0.20, cooperation_bias: 0.70, specialization: 0.90, price_sensitivity: 0.60, breeding_investment: 0.45 } },
    { agentId: "9c1b4e2d", archetype: "predator", fitness: 0.76, genome: { bid_aggression: 0.80, risk_tolerance: 0.75, cooperation_bias: 0.30, specialization: 0.20, price_sensitivity: 0.40, breeding_investment: 0.55 } },
    { agentId: "d4e8f3a1", archetype: "trader", fitness: 0.71, genome: { bid_aggression: 0.50, risk_tolerance: 0.40, cooperation_bias: 0.85, specialization: 0.30, price_sensitivity: 0.70, breeding_investment: 0.80 } },
    { agentId: "a7c3e9f2", archetype: "generalist", fitness: 0.68, genome: { bid_aggression: 0.45, risk_tolerance: 0.50, cooperation_bias: 0.60, specialization: 0.40, price_sensitivity: 0.55, breeding_investment: 0.65 } },
    { agentId: "b1d4f6a8", archetype: "specialist", fitness: 0.65, genome: { bid_aggression: 0.30, risk_tolerance: 0.25, cooperation_bias: 0.75, specialization: 0.85, price_sensitivity: 0.50, breeding_investment: 0.40 } },
    { agentId: "e2f5c8b3", archetype: "generalist", fitness: 0.61, genome: { bid_aggression: 0.55, risk_tolerance: 0.45, cooperation_bias: 0.50, specialization: 0.35, price_sensitivity: 0.65, breeding_investment: 0.70 } },
  ],
};

// Seeded-ish deterministic mock epochs
const mockEpochs = Array.from({ length: 50 }, (_, i) => {
  const seed = Math.sin(i * 7.3) * 10000;
  const r = () => (seed - Math.floor(seed) + i * 0.001) % 1;
  return {
    epoch: i + 1,
    population: 10 + Math.floor((r() * 10 + i * 0.1) % 10),
    avg_fitness: +(0.2 + (i / 50) * 0.4 + (r() * 0.05)).toFixed(3),
    gini: +(0.25 + (r() * 0.15)).toFixed(3),
    archetype_counts: {
      specialist: 3 + Math.floor(i / 15),
      generalist: 8 - Math.floor(i / 20),
      trader: 1 + Math.floor(i / 25),
      predator: 1 + Math.floor(i / 30),
    },
  };
});

// ── Config ──────────────────────────────────────────────────────

const ARCHETYPE_COLORS: Record<string, string> = {
  specialist: "#2a9d8f",
  generalist: "#457b9d",
  trader: "#e9c46a",
  predator: "#e76f51",
};

const TRAIT_COLORS: Record<string, string> = {
  bid_aggression: "#e76f51",
  risk_tolerance: "#e9c46a",
  cooperation_bias: "#2a9d8f",
  specialization: "#457b9d",
  price_sensitivity: "#a855f7",
  breeding_investment: "#ec4899",
};

const TRAIT_LABELS: Record<string, string> = {
  bid_aggression: "Bid Agg",
  risk_tolerance: "Risk Tol",
  cooperation_bias: "Coop",
  specialization: "Spec",
  price_sensitivity: "Price Sens",
  breeding_investment: "Breed Inv",
};

// ── Sub-components ──────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl px-4 py-3 flex flex-col gap-0.5"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
      <span className="text-[10px] uppercase tracking-widest" style={{ color: "rgba(255,255,255,0.35)" }}>{label}</span>
      <span className="text-xl font-bold font-mono" style={{ color: "#e0e7ff" }}>{value}</span>
      {sub && <span className="text-[10px]" style={{ color: "rgba(255,255,255,0.25)" }}>{sub}</span>}
    </div>
  );
}

function GenomeBar({ trait, value }: { trait: string; value: number }) {
  return (
    <div className="flex items-center gap-1.5" title={`${trait}: ${value.toFixed(2)}`}>
      <span className="text-[9px] font-mono w-16 text-right" style={{ color: "rgba(255,255,255,0.4)" }}>
        {TRAIT_LABELS[trait] || trait}
      </span>
      <div className="h-2 rounded-full flex-1" style={{ background: "rgba(255,255,255,0.06)", maxWidth: 80 }}>
        <div
          className="h-full rounded-full"
          style={{
            width: `${Math.max(value * 100, 2)}%`,
            background: TRAIT_COLORS[trait] || "#888",
            opacity: 0.85,
          }}
        />
      </div>
      <span className="text-[9px] font-mono w-7" style={{ color: "rgba(255,255,255,0.3)" }}>
        {value.toFixed(2)}
      </span>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────

export default function EvolutionDashboard() {
  const summary = mockSummary;
  const epochs = mockEpochs;

  const archetypeKeys = useMemo(
    () => Array.from(new Set(epochs.flatMap(e => Object.keys(e.archetype_counts)))),
    [epochs]
  );

  const stackedData = useMemo(
    () => epochs.map(e => ({
      epoch: e.epoch,
      ...Object.fromEntries(archetypeKeys.map(k => [k, e.archetype_counts[k as keyof typeof e.archetype_counts] ?? 0])),
    })),
    [epochs, archetypeKeys]
  );

  return (
    <div className="min-h-screen" style={{ background: "#0a0a1a", color: "#e0e7ff" }}>
      {/* Header */}
      <div className="px-6 pt-5 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🧬</span>
          <div>
            <h1 className="text-lg font-bold tracking-tight" style={{ color: "#e0e7ff" }}>
              Evolution Dashboard
            </h1>
            <div className="text-[10px] uppercase tracking-widest" style={{ color: "rgba(255,255,255,0.25)" }}>
              Darwinian Agent Simulation · Phase 2 Economy Layer
            </div>
          </div>
        </div>
        <Link to="/"
          className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
          style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.5)", border: "1px solid rgba(255,255,255,0.08)" }}>
          ← Back to HUD
        </Link>
      </div>

      {/* Stats Bar */}
      <div className="px-6 pb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Epochs" value={summary.totalEpochs} sub={`Latest: ${summary.latestEpoch}`} />
        <StatCard label="Population" value={summary.population} />
        <StatCard label="Avg Fitness" value={summary.avgFitness.toFixed(3)} />
        <StatCard label="Gini Coefficient" value={summary.gini.toFixed(4)} />
      </div>

      {/* Charts Row */}
      <div className="px-6 pb-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Fitness Chart */}
        <div className="rounded-xl p-4"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="text-[10px] uppercase tracking-widest mb-3" style={{ color: "rgba(255,255,255,0.3)" }}>
            📈 Avg Fitness Over Epochs
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={epochs}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="epoch" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
              <YAxis tick={{ fill: "#2a9d8f", fontSize: 10 }} domain={[0, 1]} />
              <Tooltip
                contentStyle={{
                  background: "rgba(10,10,26,0.95)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                  fontSize: 11,
                  color: "#e0e7ff",
                }}
              />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Line type="monotone" dataKey="avg_fitness" name="Avg Fitness"
                stroke="#2a9d8f" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Archetype Distribution */}
        <div className="rounded-xl p-4"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="text-[10px] uppercase tracking-widest mb-3" style={{ color: "rgba(255,255,255,0.3)" }}>
            🧩 Archetype Distribution
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={stackedData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="epoch" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
              <YAxis tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: "rgba(10,10,26,0.95)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                  fontSize: 11,
                  color: "#e0e7ff",
                }}
              />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {archetypeKeys.map(key => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stackId="1"
                  stroke={ARCHETYPE_COLORS[key] || "#888"}
                  fill={ARCHETYPE_COLORS[key] || "#888"}
                  fillOpacity={0.3}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Agent Leaderboard */}
      <div className="px-6 pb-8">
        <div className="rounded-xl p-4"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="text-[10px] uppercase tracking-widest mb-3" style={{ color: "rgba(255,255,255,0.3)" }}>
            🏆 Top Agents by Fitness
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  <th className="text-left py-2 px-2 font-medium" style={{ color: "rgba(255,255,255,0.4)" }}>#</th>
                  <th className="text-left py-2 px-2 font-medium" style={{ color: "rgba(255,255,255,0.4)" }}>Agent ID</th>
                  <th className="text-left py-2 px-2 font-medium" style={{ color: "rgba(255,255,255,0.4)" }}>Archetype</th>
                  <th className="text-right py-2 px-2 font-medium" style={{ color: "rgba(255,255,255,0.4)" }}>Fitness</th>
                  <th className="text-left py-2 px-2 font-medium" style={{ color: "rgba(255,255,255,0.4)" }}>Genome</th>
                </tr>
              </thead>
              <tbody>
                {summary.topAgents.map((agent, i) => (
                  <tr key={agent.agentId}
                    className="transition-colors"
                    style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.03)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                    <td className="py-2.5 px-2 font-mono" style={{ color: "rgba(255,255,255,0.25)" }}>{i + 1}</td>
                    <td className="py-2.5 px-2 font-mono" style={{ color: "#818cf8" }}>{agent.agentId}</td>
                    <td className="py-2.5 px-2">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                        style={{
                          background: `${ARCHETYPE_COLORS[agent.archetype] || "#888"}20`,
                          color: ARCHETYPE_COLORS[agent.archetype] || "#888",
                          border: `1px solid ${ARCHETYPE_COLORS[agent.archetype] || "#888"}40`,
                        }}>
                        {agent.archetype}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 text-right font-mono font-bold" style={{ color: "#e0e7ff" }}>
                      {agent.fitness.toFixed(3)}
                    </td>
                    <td className="py-2.5 px-2 min-w-[220px]">
                      <div className="flex flex-col gap-0.5">
                        {Object.entries(agent.genome).map(([trait, val]) => (
                          <GenomeBar key={trait} trait={trait} value={val} />
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
