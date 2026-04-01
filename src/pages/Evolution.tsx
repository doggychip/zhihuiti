import { useState, useEffect, useCallback } from "react";
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend
} from "recharts";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";
import { ChevronDown } from "lucide-react";

const API = "https://zhihuiti.zeabur.app/api/evolution";

interface GenomeTraits {
  bid_aggression: number;
  risk_tolerance: number;
  cooperation_bias: number;
  specialization: number;
  price_sensitivity: number;
  breeding_investment: number;
}

interface TopAgent {
  agentId: string;
  archetype: string;
  fitness: number;
  genome: GenomeTraits;
}

interface Summary {
  totalEpochs: number;
  latestEpoch: number;
  population: number;
  avgFitness: number;
  moneySupply: number;
  gini: number;
  archetypes: Record<string, number>;
  topAgents: TopAgent[];
}

interface EpochData {
  epoch: number;
  population: number;
  avg_fitness: number;
  money_supply: number;
  gini: number;
  archetype_counts: Record<string, number>;
}

interface Decision {
  agent_id: string;
  action: string;
  params: any;
  reasoning: string;
}

const ARCHETYPE_COLORS: Record<string, string> = {
  specialist: "#3b82f6",
  generalist: "#22c55e",
  trader: "#eab308",
  predator: "#ef4444",
};

const TRAIT_COLORS: Record<string, string> = {
  bid_aggression: "#f97316",
  risk_tolerance: "#ef4444",
  cooperation_bias: "#22c55e",
  specialization: "#3b82f6",
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
          className="h-full rounded-full transition-all"
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

export default function EvolutionDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [epochs, setEpochs] = useState<EpochData[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [sumRes, epochRes] = await Promise.all([
        fetch(`${API}/summary`),
        fetch(`${API}/epochs`),
      ]);
      const sumData = await sumRes.json();
      if (sumData.error) {
        setError(sumData.error);
        setLoading(false);
        return;
      }
      setSummary(sumData);
      setError(null);

      const epochData = await epochRes.json();
      setEpochs(Array.isArray(epochData) ? epochData : []);

      // Fetch decisions for latest epoch
      if (sumData.latestEpoch != null) {
        try {
          const decRes = await fetch(`${API}/decisions/${sumData.latestEpoch}`);
          const decData = await decRes.json();
          setDecisions(Array.isArray(decData) ? decData : []);
        } catch {
          setDecisions([]);
        }
      }
    } catch {
      setError("Failed to connect to evolution API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Prepare archetype stacked area data
  const archetypeKeys = Array.from(
    new Set(epochs.flatMap(e => Object.keys(e.archetype_counts || {})))
  );
  const stackedData = epochs.map(e => ({
    epoch: e.epoch,
    ...Object.fromEntries(archetypeKeys.map(k => [k, e.archetype_counts?.[k] ?? 0])),
  }));

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0a0a1a" }}>
        <div className="text-sm font-mono animate-pulse" style={{ color: "rgba(255,255,255,0.3)" }}>
          Loading evolution data...
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0a0a1a" }}>
        <div className="rounded-xl p-8 text-center max-w-md"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="text-3xl mb-3">🧬</div>
          <div className="text-sm mb-2" style={{ color: "rgba(255,255,255,0.7)" }}>
            {error || "No simulation data yet."}
          </div>
          <code className="text-xs font-mono px-3 py-1.5 rounded-lg inline-block mt-2"
            style={{ background: "rgba(255,255,255,0.05)", color: "#818cf8" }}>
            python -m zhihuiti.simulation
          </code>
          <div className="text-[10px] mt-2" style={{ color: "rgba(255,255,255,0.25)" }}>
            Run the above to start evolving agents.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "#0a0a1a", color: "#e0e7ff" }}>
      {/* Header */}
      <div className="px-6 pt-5 pb-3 flex items-center gap-3">
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

      {/* Stats Bar */}
      <div className="px-6 pb-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <StatCard label="Epochs" value={summary.totalEpochs} sub={`Latest: ${summary.latestEpoch}`} />
        <StatCard label="Population" value={summary.population} />
        <StatCard label="Avg Fitness" value={summary.avgFitness.toFixed(3)} />
        <StatCard label="Gini Coefficient" value={summary.gini.toFixed(4)} />
        <StatCard label="Money Supply" value={summary.moneySupply.toLocaleString()} />
      </div>

      {/* Charts Row */}
      <div className="px-6 pb-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Fitness + Population Chart */}
        <div className="rounded-xl p-4"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="text-[10px] uppercase tracking-widest mb-3" style={{ color: "rgba(255,255,255,0.3)" }}>
            📈 Fitness & Population Over Epochs
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={epochs}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="epoch" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
              <YAxis yAxisId="left" tick={{ fill: "#818cf8", fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#22c55e", fontSize: 10 }} />
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
              <Line yAxisId="left" type="monotone" dataKey="avg_fitness" name="Avg Fitness"
                stroke="#818cf8" strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="population" name="Population"
                stroke="#22c55e" strokeWidth={2} dot={false} strokeDasharray="5 5" />
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
      <div className="px-6 pb-4">
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
                {(summary.topAgents || []).slice(0, 10).map((agent, i) => (
                  <tr key={agent.agentId}
                    className="transition-colors"
                    style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.03)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                    <td className="py-2 px-2 font-mono" style={{ color: "rgba(255,255,255,0.25)" }}>{i + 1}</td>
                    <td className="py-2 px-2 font-mono" style={{ color: "#818cf8" }}>{agent.agentId}</td>
                    <td className="py-2 px-2">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                        style={{
                          background: `${ARCHETYPE_COLORS[agent.archetype] || "#888"}20`,
                          color: ARCHETYPE_COLORS[agent.archetype] || "#888",
                          border: `1px solid ${ARCHETYPE_COLORS[agent.archetype] || "#888"}30`,
                        }}>
                        {agent.archetype}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right font-mono font-bold" style={{ color: "#e0e7ff" }}>
                      {agent.fitness.toFixed(3)}
                    </td>
                    <td className="py-2 px-2 min-w-[200px]">
                      <div className="flex flex-col gap-0.5">
                        {agent.genome && Object.entries(agent.genome).map(([trait, val]) => (
                          <GenomeBar key={trait} trait={trait} value={val as number} />
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

      {/* Decision Log */}
      <div className="px-6 pb-8">
        <Collapsible>
          <div className="rounded-xl overflow-hidden"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <CollapsibleTrigger className="w-full px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-white/[0.02] transition-colors">
              <div className="text-[10px] uppercase tracking-widest" style={{ color: "rgba(255,255,255,0.3)" }}>
                📋 Decision Log — Epoch {summary.latestEpoch}
              </div>
              <ChevronDown className="h-3.5 w-3.5 transition-transform duration-200" style={{ color: "rgba(255,255,255,0.3)" }} />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="px-4 pb-4 space-y-2 max-h-96 overflow-y-auto">
                {decisions.length === 0 ? (
                  <div className="text-xs py-4 text-center" style={{ color: "rgba(255,255,255,0.2)" }}>
                    No decisions recorded for this epoch.
                  </div>
                ) : (
                  decisions.map((d, i) => (
                    <div key={i} className="rounded-lg px-3 py-2"
                      style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-[11px]" style={{ color: "#818cf8" }}>{d.agent_id}</span>
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-medium uppercase"
                          style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.5)" }}>
                          {d.action}
                        </span>
                      </div>
                      <div className="text-[11px] leading-relaxed" style={{ color: "rgba(255,255,255,0.5)" }}>
                        {d.reasoning}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>
      </div>
    </div>
  );
}
