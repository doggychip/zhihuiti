import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useState, useCallback } from "react";
import {
  Activity, TrendingUp, TrendingDown, Minus, Zap, Brain,
  BarChart3, ArrowUpDown, RefreshCw, Search, Upload, Bell,
  Globe, DollarSign, Coins, LineChart, AlertTriangle, Link2,
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

interface AlertItem {
  id: string;
  timestamp: number;
  domain: string;
  label: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
}

interface CrossDomainCorrelation {
  domain_a: string;
  label_a: string;
  regime_a: string;
  pattern_a: string;
  domain_b: string;
  label_b: string;
  regime_b: string;
  pattern_b: string;
  bridge_theories: string[];
  correlation_type: string;
  interpretation: string;
  score: number;
}

// ── Domain tabs ───────────────────────────────────────────────────────────

type DomainTab = "crypto" | "equities" | "forex" | "indices" | "alerts" | "cross-domain" | "csv";

const DOMAIN_TABS: { key: DomainTab; label: string; icon: typeof Coins; endpoint: string }[] = [
  { key: "crypto", label: "Crypto", icon: Coins, endpoint: "/api/oracle/scan" },
  { key: "equities", label: "Equities", icon: BarChart3, endpoint: "/api/oracle/scan/equities" },
  { key: "forex", label: "Forex", icon: DollarSign, endpoint: "/api/oracle/scan/forex" },
  { key: "indices", label: "Indices", icon: LineChart, endpoint: "/api/oracle/scan/indices" },
  { key: "alerts", label: "Alerts", icon: Bell, endpoint: "/api/oracle/alerts" },
  { key: "cross-domain", label: "Cross-Domain", icon: Link2, endpoint: "/api/oracle/cross-domain" },
  { key: "csv", label: "Upload", icon: Upload, endpoint: "" },
];

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

const severityColor: Record<string, string> = {
  critical: "text-red-400 bg-red-500/10 border-red-500/20",
  warning: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  info: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

const correlationTypeColor: Record<string, string> = {
  convergent: "text-emerald-400",
  divergent: "text-amber-400",
  resonant: "text-red-400",
  neutral: "text-zinc-400",
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

function timeAgo(ts: number) {
  const diff = Math.floor(Date.now() / 1000 - ts);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Components ─────────────────────────────────────────────────────────────

function ScanTable({ results, onSelect }: { results: ScanResult[]; onSelect: (s: string) => void }) {
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
              <tr
                key={r.instrument}
                className="border-b border-border/50 hover:bg-muted/30 transition-colors cursor-pointer"
                onClick={() => onSelect(r.instrument)}
              >
                <td className="py-2.5 text-muted-foreground">{i + 1}</td>
                <td className="py-2.5 font-medium">{r.instrument.replace("_USDT", "").replace("=X", "")}</td>
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
                <td className="py-2.5 text-muted-foreground">{r.top_pattern?.replace(/_/g, " ") || "-"}</td>
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

function DetailPanel({ instrument, domain }: { instrument: string; domain: DomainTab }) {
  const endpoint = domain === "crypto"
    ? `/api/oracle/crypto/${instrument}`
    : `/api/oracle/instrument/${instrument}`;
  const { data, isLoading } = useQuery<CryptoDiagnosis>({
    queryKey: [oracleUrl(endpoint)],
    enabled: !!instrument,
  });

  if (isLoading) return <div className="space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-20 w-full" />)}</div>;
  if (!data) return <p className="text-muted-foreground text-sm">Select an instrument to view details</p>;

  const Icon = regimeIcon[data.regime] || Minus;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">{data.instrument.replace("_USDT", "")}</h3>
          <p className="text-2xl font-mono font-bold">{formatPrice(data.price)}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Alerts Panel ──────────────────────────────────────────────────────────

function AlertsPanel() {
  const { data, isLoading } = useQuery<{ alerts: AlertItem[] }>({
    queryKey: [oracleUrl("/api/oracle/alerts")],
    refetchInterval: 30000,
  });

  const alerts = data?.alerts ?? [];

  if (isLoading) return <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-16 w-full" />)}</div>;

  return (
    <div className="space-y-3">
      {alerts.length === 0 ? (
        <div className="flex flex-col items-center py-12 text-muted-foreground">
          <Bell className="w-8 h-8 mb-2 opacity-40" />
          <p className="text-sm">No alerts yet. Scan markets to generate alerts.</p>
        </div>
      ) : (
        alerts.map((a) => {
          const SevIcon = a.severity === "critical" ? AlertTriangle : a.severity === "warning" ? Bell : Activity;
          return (
            <div key={a.id} className={`p-3 rounded-lg border space-y-1 ${severityColor[a.severity] || ""}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <SevIcon className="w-4 h-4" />
                  <span className="font-medium text-sm">{a.title}</span>
                </div>
                <span className="text-xs text-muted-foreground">{timeAgo(a.timestamp)}</span>
              </div>
              <p className="text-xs opacity-80">{a.message}</p>
              <div className="flex gap-2">
                <Badge variant="outline" className="text-[10px]">{a.alert_type}</Badge>
                <Badge variant="outline" className="text-[10px]">{a.domain}</Badge>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

// ── Cross-Domain Panel ────────────────────────────────────────────────────

function CrossDomainPanel() {
  const { data, isLoading, refetch } = useQuery<{
    correlations: CrossDomainCorrelation[];
    alerts: AlertItem[];
    snapshot_count: number;
  }>({
    queryKey: [oracleUrl("/api/oracle/cross-domain")],
    enabled: false, // manual trigger
  });

  const correlations = data?.correlations ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Compare regimes across crypto, equities, forex, and indices to find structural bridges.
        </p>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 transition-colors text-sm"
        >
          <Link2 className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          Analyze
        </button>
      </div>

      {data && (
        <p className="text-xs text-muted-foreground">
          Analyzed {data.snapshot_count} instruments across domains
        </p>
      )}

      {correlations.length === 0 && !isLoading ? (
        <div className="flex flex-col items-center py-12 text-muted-foreground">
          <Globe className="w-8 h-8 mb-2 opacity-40" />
          <p className="text-sm">Scan multiple domains first, then click Analyze to find cross-domain correlations.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {correlations.map((c, i) => (
            <div key={i} className="p-3 rounded-lg bg-purple-500/5 border border-purple-500/20 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Link2 className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium">
                    {c.domain_a}:{c.label_a.replace("_USDT", "")}
                    <span className="text-muted-foreground mx-1.5">↔</span>
                    {c.domain_b}:{c.label_b.replace("_USDT", "")}
                  </span>
                </div>
                <span className={`text-xs font-medium ${correlationTypeColor[c.correlation_type]}`}>
                  {c.correlation_type} ({(c.score * 100).toFixed(0)}%)
                </span>
              </div>
              <div className="flex gap-2">
                <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${regimeBg[c.regime_a]}`}>
                  <span className={regimeColor[c.regime_a]}>{regimeLabel[c.regime_a]}</span>
                </div>
                <span className="text-muted-foreground text-xs self-center">↔</span>
                <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${regimeBg[c.regime_b]}`}>
                  <span className={regimeColor[c.regime_b]}>{regimeLabel[c.regime_b]}</span>
                </div>
              </div>
              <p className="text-xs text-foreground/80">{c.interpretation}</p>
              {c.bridge_theories.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  <span className="text-[10px] text-muted-foreground">Bridges:</span>
                  {c.bridge_theories.map(t => (
                    <Badge key={t} variant="outline" className="text-[10px] text-purple-300 border-purple-400/30">{t.replace(/_/g, " ")}</Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── CSV Upload Panel ──────────────────────────────────────────────────────

function CsvUploadPanel() {
  const [csvText, setCsvText] = useState("");
  const [domain, setDomain] = useState("scientific");
  const [label, setLabel] = useState("uploaded data");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleUpload = useCallback(async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      // Try to parse as JSON array or comma-separated values
      let values: number[] = [];
      const trimmed = csvText.trim();

      if (trimmed.startsWith("[")) {
        values = JSON.parse(trimmed);
      } else if (trimmed.includes(",") && !trimmed.includes("\n")) {
        values = trimmed.split(",").map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
      } else {
        // CSV with header
        const resp = await fetch(oracleUrl("/api/oracle/csv"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ csv: trimmed, domain, label }),
        });
        const data = await resp.json();
        if (data.error) { setError(data.error); } else { setResult(data); }
        setLoading(false);
        return;
      }

      const resp = await fetch(oracleUrl("/api/oracle/csv"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values, domain, label }),
      });
      const data = await resp.json();
      if (data.error) { setError(data.error); } else { setResult(data); }
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  }, [csvText, domain, label]);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Paste any time series data — CSV, JSON array, or comma-separated values. The oracle will detect patterns, classify regime, and map to theories.
      </p>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-muted-foreground block mb-1">Domain</label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm"
          >
            <option value="crypto">Crypto / Finance</option>
            <option value="system_perf">System Performance</option>
            <option value="social">Social Dynamics</option>
            <option value="business">Business Metrics</option>
            <option value="scientific">Scientific Data</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground block mb-1">Label</label>
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. API latency, revenue, temperature"
            className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm"
          />
        </div>
      </div>

      <textarea
        value={csvText}
        onChange={(e) => setCsvText(e.target.value)}
        placeholder={"Paste your data here:\n\n• JSON array: [1.2, 3.4, 5.6, ...]\n• Comma-separated: 1.2, 3.4, 5.6\n• CSV with header:\ntimestamp,value\n2024-01-01,100\n2024-01-02,102"}
        className="w-full h-40 bg-muted/30 border border-border rounded px-3 py-2 text-sm font-mono resize-y"
      />

      <button
        onClick={handleUpload}
        disabled={loading || !csvText.trim()}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors text-sm disabled:opacity-50"
      >
        <Upload className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        {loading ? "Analyzing..." : "Analyze Data"}
      </button>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
      )}

      {result && (
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{result.label || label}</h3>
              <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${regimeBg[result.regime] || ""}`}>
                <span className={`font-medium text-sm ${regimeColor[result.regime]}`}>{regimeLabel[result.regime] || result.regime}</span>
              </div>
            </div>
            {result.dominant_theory && (
              <p className="text-xs text-muted-foreground">Dominant theory: <span className="text-foreground">{result.dominant_theory.replace(/_/g, " ")}</span></p>
            )}
            {result.patterns?.map((p: any, i: number) => (
              <div key={i} className="p-2 rounded bg-muted/20 border border-border/30">
                <div className="flex items-center justify-between">
                  <span className="text-sm">{p.name.replace(/_/g, " ")}</span>
                  {strengthBar(p.strength)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">{p.description}</p>
              </div>
            ))}
            {result.collision_insights?.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">Collision Insights</h4>
                {result.collision_insights.map((ci: any, i: number) => (
                  <CollisionCard key={i} ci={ci} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function OraclePage() {
  const [activeTab, setActiveTab] = useState<DomainTab>("crypto");
  const [selected, setSelected] = useState<string>("");

  const scanEndpoint = DOMAIN_TABS.find(t => t.key === activeTab)?.endpoint || "";
  const isMarketTab = ["crypto", "equities", "forex", "indices"].includes(activeTab);

  const { data: scanData, isLoading: scanLoading, refetch: refetchScan } = useQuery<{
    results: ScanResult[];
    transitions: Transition[];
    count: number;
  }>({
    queryKey: [oracleUrl(scanEndpoint)],
    enabled: isMarketTab,
    refetchInterval: isMarketTab ? 60000 : false,
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
              Universal intelligence across {isMarketTab ? `${results.length} instruments` : "all domains"}
            </p>
          </div>
          {isMarketTab && (
            <button
              onClick={() => refetchScan()}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors text-sm"
            >
              <RefreshCw className={`w-4 h-4 ${scanLoading ? "animate-spin" : ""}`} />
              Scan
            </button>
          )}
        </div>

        {/* Domain Tabs */}
        <div className="flex gap-1 flex-wrap border-b border-border pb-3">
          {DOMAIN_TABS.map(({ key, label, icon: TabIcon }) => (
            <button
              key={key}
              onClick={() => { setActiveTab(key); setSelected(""); }}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-t-lg text-sm transition-colors ${
                activeTab === key
                  ? "bg-cyan-500/10 text-cyan-400 border-b-2 border-cyan-400"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
              }`}
            >
              <TabIcon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Stat cards — only for market tabs */}
        {isMarketTab && (
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
        )}

        {/* Regime distribution — market tabs */}
        {isMarketTab && Object.keys(regimeCounts).length > 0 && (
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

        {/* Main content — depends on active tab */}
        {isMarketTab && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <Card className="lg:col-span-3 bg-card/50 border-border/50">
              <CardContent className="p-4">
                <h2 className="text-sm font-medium text-muted-foreground mb-3">
                  {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Scan (ranked by signal)
                </h2>
                {scanLoading ? (
                  <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
                ) : results.length > 0 ? (
                  <ScanTable results={results} onSelect={setSelected} />
                ) : (
                  <p className="text-muted-foreground text-sm">No scan data. Click Scan to start.</p>
                )}
              </CardContent>
            </Card>

            <Card className="lg:col-span-2 bg-card/50 border-border/50">
              <CardContent className="p-4">
                <h2 className="text-sm font-medium text-muted-foreground mb-3">
                  {selected ? `${selected.replace("_USDT", "").replace("=X", "")} Analysis` : "Instrument Detail"}
                </h2>
                {selected ? (
                  <DetailPanel instrument={selected} domain={activeTab} />
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Search className="w-8 h-8 mb-2 opacity-40" />
                    <p className="text-sm">Click a row to see full diagnosis</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "alerts" && (
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <h2 className="text-sm font-medium text-muted-foreground mb-3">Regime Alerts</h2>
              <AlertsPanel />
            </CardContent>
          </Card>
        )}

        {activeTab === "cross-domain" && (
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <h2 className="text-sm font-medium text-muted-foreground mb-3">Cross-Domain Correlation</h2>
              <CrossDomainPanel />
            </CardContent>
          </Card>
        )}

        {activeTab === "csv" && (
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <h2 className="text-sm font-medium text-muted-foreground mb-3">Upload & Analyze</h2>
              <CsvUploadPanel />
            </CardContent>
          </Card>
        )}

        {/* Transitions — market tabs */}
        {isMarketTab && transitions.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <h2 className="text-sm font-medium text-muted-foreground mb-3">Regime Transitions</h2>
              <div className="space-y-2">
                {transitions.map((t, i) => {
                  const FromIcon = regimeIcon[t.from_regime] || Minus;
                  const ToIcon = regimeIcon[t.to_regime] || Minus;
                  return (
                    <div key={i} className="flex items-center gap-3 p-2 rounded bg-muted/20 border border-border/30">
                      <span className="font-medium text-sm w-16">{t.instrument.replace("_USDT", "").replace("=X", "")}</span>
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
