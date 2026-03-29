import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useState } from "react";
import {
  Activity, TrendingUp, TrendingDown, Minus, Zap, Brain,
  BarChart3, ArrowUpDown, RefreshCw, Search,
} from "lucide-react";

// ── Oracle API base URL ───────────────────────────────────────────────────
const ORACLE_API = "https://zhihuiti-oracle.zeabur.app";
function oracleUrl(path: string) { return `${ORACLE_API}${path}`; }

// ── Types ──────────────────────────────────────────────────────────────────

interface ScanResult {
  instrument: string;
  price: number;
  change_pct: number;
  regime: string;
  dominant_theory: string;
  pattern_count: number;
  top_pattern: string;
  top_pattern_strength: number;
  collision_count: number;
  signal_score: number;
}

interface Pattern {
  name: string;
  strength: number;
  description: string;
  metrics: Record<string, number>;
  theory_ids: string[];
}

interface CollisionInsight {
  pattern_a: string;
  pattern_b: string;
  bridge_theory: string;
  bridge_domain: string;
  collision_score: number;
  interpretation: string;
  trading_rule: string;
}

interface CryptoDiagnosis {
  instrument: string;
  price: number;
  change_pct: number;
  regime: string;
  dominant_theory: string;
  patterns: Pattern[];
  collision_insights: CollisionInsight[];
  theory_details: any[];
}

interface Transition {
  instrument: string;
  timestamp: number;
  from_regime: string;
  to_regime: string;
  price: number;
  signal_score: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────

const regimeColor: Record<string, string> = {
  trending_up: "text-emerald-400",
  trending_down: "text-red-400",
  mean_reverting: "text-blue-400",
  volatile: "text-amber-400",
  quiet: "text-zinc-400",
};

const regimeBg: Record<string, string> = {
  trending_up: "bg-emerald-500/10 border-emerald-500/20",
  trending_down: "bg-red-500/10 border-red-500/20",
  mean_reverting: "bg-blue-500/10 border-blue-500/20",
  volatile: "bg-amber-500/10 border-amber-500/20",
  quiet: "bg-zinc-500/10 border-zinc-500/20",
};

const regimeIcon: Record<string, typeof TrendingUp> = {
  trending_up: TrendingUp,
  trending_down: TrendingDown,
  mean_reverting: ArrowUpDown,
  volatile: Activity,
  quiet: Minus,
};

const regimeLabel: Record<string, string> = {
  trending_up: "Trending Up",
  trending_down: "Trending Down",
  mean_reverting: "Mean Reverting",
  volatile: "Volatile",
  quiet: "Quiet",
};

function formatPct(v: number) {
  return (v >= 0 ? "+" : "") + (v * 100).toFixed(2) + "%";
}

function formatPrice(v: number) {
  if (v >= 1000) return "$" + v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (v >= 1) return "$" + v.toFixed(2);
  return "$" + v.toFixed(6);
}

function strengthBar(v: number) {
  const pct = Math.round(v * 100);
  const color = v > 0.7 ? "bg-emerald-400" : v > 0.4 ? "bg-amber-400" : "bg-zinc-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground">{pct}%</span>
    </div>
  );
}

// ── Components ─────────────────────────────────────────────────────────────

function ScanTable({ results }: { results: ScanResult[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted-foreground border-b border-border">
            <th className="pb-2 font-medium">#</th>
            <th className="pb-2 font-medium">Instrument</th>
            <th className="pb-2 font-medium text-right">Price</th>
            <th className="pb-2 font-medium text-right">Change</th>
            <th className="pb-2 font-medium">Regime</th>
            <th className="pb-2 font-medium">Top Pattern</th>
            <th className="pb-2 font-medium">Signal</th>
            <th className="pb-2 font-medium text-right">Collisions</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r, i) => {
            const Icon = regimeIcon[r.regime] || Minus;
            return (
              <tr key={r.instrument} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                <td className="py-2.5 text-muted-foreground">{i + 1}</td>
                <td className="py-2.5 font-medium">{r.instrument.replace("_USDT", "")}</td>
                <td className="py-2.5 text-right font-mono">{formatPrice(r.price)}</td>
                <td className={`py-2.5 text-right font-mono ${r.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {formatPct(r.change_pct)}
                </td>
                <td className="py-2.5">
                  <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${regimeBg[r.regime] || ""}`}>
                    <Icon className="w-3 h-3" />
                    <span className={regimeColor[r.regime]}>{regimeLabel[r.regime] || r.regime}</span>
                  </div>
                </td>
                <td className="py-2.5 text-muted-foreground">{r.top_pattern || "-"}</td>
                <td className="py-2.5">{strengthBar(r.signal_score)}</td>
                <td className="py-2.5 text-right">
                  {r.collision_count > 0 ? (
                    <Badge variant="outline" className="text-cyan-400 border-cyan-400/30">{r.collision_count}</Badge>
                  ) : "-"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function PatternCard({ pattern }: { pattern: Pattern }) {
  return (
    <div className="p-3 rounded-lg bg-muted/30 border border-border/50 space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm">{pattern.name.replace(/_/g, " ")}</span>
        {strengthBar(pattern.strength)}
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{pattern.description}</p>
      <div className="flex gap-1 flex-wrap">
        {pattern.theory_ids.map(t => (
          <Badge key={t} variant="outline" className="text-[10px] px-1.5 py-0">{t.replace(/_/g, " ")}</Badge>
        ))}
      </div>
    </div>
  );
}

function CollisionCard({ ci }: { ci: CollisionInsight }) {
  return (
    <div className="p-3 rounded-lg bg-cyan-500/5 border border-cyan-500/20 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-sm font-medium">
            {ci.pattern_a} <span className="text-muted-foreground">x</span> {ci.pattern_b}
          </span>
        </div>
        <span className="text-xs text-cyan-400">{(ci.collision_score * 100).toFixed(0)}%</span>
      </div>
      {ci.bridge_theory !== "(rule-template)" && (
        <p className="text-xs text-muted-foreground">
          Bridge: <span className="text-cyan-300">{ci.bridge_theory.replace(/_/g, " ")}</span> ({ci.bridge_domain})
        </p>
      )}
      <p className="text-xs text-foreground/80 leading-relaxed">{ci.trading_rule}</p>
    </div>
  );
}

function DetailPanel({ instrument }: { instrument: string }) {
  const { data, isLoading } = useQuery<CryptoDiagnosis>({
    queryKey: [oracleUrl(`/api/oracle/crypto/${instrument}`)],
    enabled: !!instrument,
  });

  if (isLoading) return <div className="space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-20 w-full" />)}</div>;
  if (!data) return <p className="text-muted-foreground text-sm">Select an instrument to view details</p>;

  const Icon = regimeIcon[data.regime] || Minus;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">{data.instrument.replace("_USDT", "")}/USDT</h3>
          <p className="text-2xl font-mono font-bold">{formatPrice(data.price)}</p>
        </div>
        <div className={`flex flex-col items-end gap-1`}>
          <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${regimeBg[data.regime]}`}>
            <Icon className="w-4 h-4" />
            <span className={`font-medium ${regimeColor[data.regime]}`}>{regimeLabel[data.regime]}</span>
          </div>
          <span className={`text-sm font-mono ${data.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {formatPct(data.change_pct)}
          </span>
        </div>
      </div>

      {data.patterns.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Detected Patterns</h4>
          {data.patterns.map((p, i) => <PatternCard key={i} pattern={p} />)}
        </div>
      )}

      {data.collision_insights.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Collision Insights</h4>
          {data.collision_insights.map((ci, i) => <CollisionCard key={i} ci={ci} />)}
        </div>
      )}

      {data.theory_details.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Theory Details</h4>
          {data.theory_details.slice(0, 3).map((t, i) => (
            <div key={i} className="p-2 rounded bg-muted/20 border border-border/30">
              <div className="flex items-center gap-2">
                <Brain className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-sm font-medium">{t.name}</span>
                <Badge variant="outline" className="text-[10px]">{t.domain}</Badge>
              </div>
              {t.equation && <p className="text-xs text-muted-foreground font-mono mt-1">{t.equation.slice(0, 80)}</p>}
              {t.cross_domain_analogies?.slice(0, 1).map((a: any, j: number) => (
                <p key={j} className="text-[11px] text-muted-foreground mt-1">
                  Analogy: {a.theory} ({a.domain}) - {a.interpretation?.slice(0, 100)}
                </p>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function OraclePage() {
  const [selected, setSelected] = useState<string>("");

  const { data: scanData, isLoading: scanLoading, refetch: refetchScan } = useQuery<{
    results: ScanResult[];
    transitions: Transition[];
    count: number;
  }>({
    queryKey: [oracleUrl("/api/oracle/scan")],
    refetchInterval: 60000, // auto-refresh every 60s
  });

  const { data: statsData } = useQuery<any>({
    queryKey: [oracleUrl("/api/oracle/theories/stats")],
  });

  const results = scanData?.results ?? [];
  const transitions = scanData?.transitions ?? [];

  // Regime distribution
  const regimeCounts: Record<string, number> = {};
  for (const r of results) {
    regimeCounts[r.regime] = (regimeCounts[r.regime] || 0) + 1;
  }

  return (
    <div className="grid-pattern min-h-screen">
      <div className="p-6 lg:p-10 max-w-7xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Oracle</h1>
            <p className="text-muted-foreground text-sm">
              Theory-grounded market intelligence across {results.length} instruments
            </p>
          </div>
          <button
            onClick={() => refetchScan()}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${scanLoading ? "animate-spin" : ""}`} />
            Scan
          </button>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground mb-1">Instruments</p>
              <p className="text-xl font-bold">{results.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground mb-1">Theories</p>
              <p className="text-xl font-bold">{statsData?.theories ?? "-"}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground mb-1">Collisions</p>
              <p className="text-xl font-bold">{statsData?.collisions ?? "-"}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground mb-1">Transitions</p>
              <p className="text-xl font-bold text-amber-400">{transitions.length}</p>
            </CardContent>
          </Card>
        </div>

        {/* Regime distribution */}
        {Object.keys(regimeCounts).length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {Object.entries(regimeCounts).map(([regime, count]) => {
              const Icon = regimeIcon[regime] || Minus;
              return (
                <div key={regime} className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border ${regimeBg[regime]}`}>
                  <Icon className="w-3.5 h-3.5" />
                  <span className={`text-sm ${regimeColor[regime]}`}>{regimeLabel[regime]}</span>
                  <span className="text-xs text-muted-foreground ml-1">({count})</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Main content: scan table + detail panel */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Scan table */}
          <Card className="lg:col-span-3 bg-card/50 border-border/50">
            <CardContent className="p-4">
              <h2 className="text-sm font-medium text-muted-foreground mb-3">Market Scan (ranked by signal)</h2>
              {scanLoading ? (
                <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
              ) : results.length > 0 ? (
                <div>
                  <ScanTable results={results} />
                  <div className="mt-3 flex gap-2 flex-wrap">
                    {results.map(r => (
                      <button
                        key={r.instrument}
                        onClick={() => setSelected(r.instrument)}
                        className={`px-2.5 py-1 rounded text-xs transition-colors ${
                          selected === r.instrument
                            ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                            : "bg-muted/30 text-muted-foreground hover:text-foreground border border-transparent"
                        }`}
                      >
                        {r.instrument.replace("_USDT", "")}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No scan data. Click Scan to start.</p>
              )}
            </CardContent>
          </Card>

          {/* Detail panel */}
          <Card className="lg:col-span-2 bg-card/50 border-border/50">
            <CardContent className="p-4">
              <h2 className="text-sm font-medium text-muted-foreground mb-3">
                {selected ? `${selected.replace("_USDT", "")}/USDT Analysis` : "Instrument Detail"}
              </h2>
              {selected ? (
                <DetailPanel instrument={selected} />
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <Search className="w-8 h-8 mb-2 opacity-40" />
                  <p className="text-sm">Select an instrument to see full diagnosis</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Transitions */}
        {transitions.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <h2 className="text-sm font-medium text-muted-foreground mb-3">Regime Transitions</h2>
              <div className="space-y-2">
                {transitions.map((t, i) => {
                  const FromIcon = regimeIcon[t.from_regime] || Minus;
                  const ToIcon = regimeIcon[t.to_regime] || Minus;
                  return (
                    <div key={i} className="flex items-center gap-3 p-2 rounded bg-muted/20 border border-border/30">
                      <span className="font-medium text-sm w-16">{t.instrument.replace("_USDT", "")}</span>
                      <div className={`flex items-center gap-1 ${regimeColor[t.from_regime]}`}>
                        <FromIcon className="w-3.5 h-3.5" />
                        <span className="text-xs">{regimeLabel[t.from_regime]}</span>
                      </div>
                      <span className="text-muted-foreground text-xs">-&gt;</span>
                      <div className={`flex items-center gap-1 ${regimeColor[t.to_regime]}`}>
                        <ToIcon className="w-3.5 h-3.5" />
                        <span className="text-xs">{regimeLabel[t.to_regime]}</span>
                      </div>
                      <span className="text-xs text-muted-foreground ml-auto">{formatPrice(t.price)}</span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
