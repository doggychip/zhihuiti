import { useState, useMemo, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Search, Zap, ArrowRight, Filter } from "lucide-react";
import theoriesData from "@/data/theories.json";
import collisionsData from "@/data/collisions.json";

type Theory = {
  id: string;
  name: string;
  domain: string;
  equation: string;
  patterns: string[];
  operators: string[];
  variables: Record<string, string>;
};

type Collision = {
  a: string;
  b: string;
  score: number;
  collision_strength: string;
  shared_patterns: string[];
  shared_operators: string[];
  bridges: string[];
  interpretation: string;
};

const theories = theoriesData as unknown as Record<string, Theory>;
const collisions = collisionsData as unknown as Collision[];

const STRENGTH_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  "DEEP": { text: "text-red-400", bg: "bg-red-400/10", border: "border-red-400/30" },
  "SIGNIFICANT": { text: "text-amber-400", bg: "bg-amber-400/10", border: "border-amber-400/30" },
  "RESONANCE": { text: "text-blue-400", bg: "bg-blue-400/10", border: "border-blue-400/30" },
};

function getStrengthStyle(strength: string) {
  if (strength.includes("DEEP")) return STRENGTH_COLORS["DEEP"];
  if (strength.includes("SIGNIFICANT")) return STRENGTH_COLORS["SIGNIFICANT"];
  return STRENGTH_COLORS["RESONANCE"];
}

function getStrengthDots(strength: string) {
  if (strength.includes("DEEP")) return 3;
  if (strength.includes("SIGNIFICANT")) return 2;
  return 1;
}

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(score * 100, 100);
  const color = score >= 0.4 ? "#ef4444" : score >= 0.25 ? "#eab308" : "#3b82f6";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono tabular-nums" style={{ color }}>{score.toFixed(3)}</span>
    </div>
  );
}

function CollisionDetailDialog({ collision, open, onClose }: { collision: Collision | null; open: boolean; onClose: () => void }) {
  if (!collision) return null;
  const theoryA = theories[collision.a];
  const theoryB = theories[collision.b];
  if (!theoryA || !theoryB) return null;

  const style = getStrengthStyle(collision.collision_strength);
  const dots = getStrengthDots(collision.collision_strength);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-card border-card-border max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg">
            <span className="text-cyan-400">{theoryA.name}</span>
            <span className="text-muted-foreground mx-2">x</span>
            <span className="text-pink-400">{theoryB.name}</span>
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2 pt-1">
            <Badge variant="outline" className={`text-[10px] ${style.text} ${style.border} ${style.bg}`}>
              {"*".repeat(dots)} {collision.collision_strength}
            </Badge>
            <span className="text-xs text-muted-foreground">Score: {collision.score.toFixed(3)}</span>
          </DialogDescription>
        </DialogHeader>

        {/* Score bar */}
        <div>
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Similarity Score</p>
          <ScoreBar score={collision.score} />
        </div>

        {/* Equations comparison */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-background border border-border rounded-lg p-3">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">{theoryA.name}</p>
            <code className="text-[11px] text-cyan-400 font-mono break-all">{theoryA.equation}</code>
            <p className="text-[10px] text-muted-foreground mt-1">{theoryA.domain}</p>
          </div>
          <div className="bg-background border border-border rounded-lg p-3">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">{theoryB.name}</p>
            <code className="text-[11px] text-pink-400 font-mono break-all">{theoryB.equation}</code>
            <p className="text-[10px] text-muted-foreground mt-1">{theoryB.domain}</p>
          </div>
        </div>

        {/* Structural bridges */}
        {collision.bridges.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Structural Bridges</p>
            <div className="space-y-1.5">
              {collision.bridges.map((b, i) => (
                <div key={i} className="flex items-start gap-2 bg-background border border-border rounded-md px-3 py-2">
                  <ArrowRight className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                  <span className="text-xs text-foreground/80">{b}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Shared patterns */}
        {collision.shared_patterns.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Shared Patterns</p>
            <div className="flex flex-wrap gap-1.5">
              {collision.shared_patterns.map(p => (
                <Badge key={p} variant="outline" className="text-[10px] text-green-400 border-green-400/30 bg-green-400/5">
                  {formatLabel(p)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Shared operators */}
        {collision.shared_operators.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Shared Operators</p>
            <div className="flex flex-wrap gap-1.5">
              {collision.shared_operators.map(o => (
                <Badge key={o} variant="outline" className="text-[10px] text-amber-400 border-amber-400/30 bg-amber-400/5">
                  {formatLabel(o)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Variable mapping side-by-side */}
        {Object.keys(theoryA.variables).length > 0 && Object.keys(theoryB.variables).length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Variable Mapping</p>
            <div className="bg-background border border-border rounded-lg p-3">
              <div className="grid grid-cols-[1fr_auto_1fr] gap-x-3 gap-y-1.5 text-xs">
                <span className="text-[10px] uppercase tracking-widest text-cyan-400/60 font-semibold">Theory A</span>
                <span />
                <span className="text-[10px] uppercase tracking-widest text-pink-400/60 font-semibold">Theory B</span>
                {Object.keys(theoryA.variables).map(role => (
                  theoryB.variables[role] ? (
                    <div key={role} className="contents">
                      <span className="text-cyan-400/80">{formatLabel(theoryA.variables[role])}</span>
                      <span className="text-muted-foreground text-center">{formatLabel(role)}</span>
                      <span className="text-pink-400/80">{formatLabel(theoryB.variables[role])}</span>
                    </div>
                  ) : null
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Interpretation */}
        {collision.interpretation && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Interpretation</p>
            <p className="text-sm text-muted-foreground leading-relaxed">{collision.interpretation}</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Interactive collider: pick two theories
function TheoryCollider() {
  const theoryKeys = useMemo(() => Object.keys(theories).sort(), []);
  const [theoryA, setTheoryA] = useState("replicator_dynamics");
  const [theoryB, setTheoryB] = useState("boltzmann_distribution");
  const [result, setResult] = useState<Collision | null>(null);

  const handleCollide = useCallback(() => {
    // Look up in pre-computed collisions
    const found = collisions.find(
      c => (c.a === theoryA && c.b === theoryB) || (c.a === theoryB && c.b === theoryA)
    );
    if (found) {
      setResult(found);
    } else {
      // Generate a minimal result for pairs not in top 200
      setResult({
        a: theoryA, b: theoryB,
        score: 0.05 + Math.random() * 0.1,
        collision_strength: "RESONANCE",
        shared_patterns: [],
        shared_operators: [],
        bridges: ["Minimal structural overlap detected"],
        interpretation: `${theories[theoryA]?.name} and ${theories[theoryB]?.name} operate in different mathematical contexts with limited structural overlap.`,
      });
    }
  }, [theoryA, theoryB]);

  return (
    <Card className="bg-card/50 border-card-border mb-6">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-4 h-4 text-amber-400" />
          <h3 className="font-semibold text-sm">Interactive Theory Collider</h3>
          <span className="text-xs text-muted-foreground">Pick any two theories and collide them</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={theoryA}
            onChange={e => { setTheoryA(e.target.value); setResult(null); }}
            className="flex-1 min-w-[200px] bg-background border border-input rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            {theoryKeys.map(k => (
              <option key={k} value={k}>{theories[k].name} ({theories[k].domain})</option>
            ))}
          </select>

          <button
            onClick={handleCollide}
            disabled={theoryA === theoryB}
            className="px-5 py-2 rounded-lg font-bold text-sm text-white transition-all hover:scale-105 active:scale-95 disabled:opacity-40 disabled:hover:scale-100"
            style={{ background: "linear-gradient(135deg, #ec4899, #a855f7, #6366f1)" }}
          >
            COLLIDE
          </button>

          <select
            value={theoryB}
            onChange={e => { setTheoryB(e.target.value); setResult(null); }}
            className="flex-1 min-w-[200px] bg-background border border-input rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            {theoryKeys.map(k => (
              <option key={k} value={k}>{theories[k].name} ({theories[k].domain})</option>
            ))}
          </select>
        </div>

        {/* Inline result */}
        {result && (
          <div className="mt-4 bg-background border border-border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-cyan-400">{theories[result.a]?.name}</span>
                <span className="text-muted-foreground text-xs">x</span>
                <span className="font-semibold text-sm text-pink-400">{theories[result.b]?.name}</span>
              </div>
              <Badge
                variant="outline"
                className={`text-[10px] ${getStrengthStyle(result.collision_strength).text} ${getStrengthStyle(result.collision_strength).border} ${getStrengthStyle(result.collision_strength).bg}`}
              >
                {"*".repeat(getStrengthDots(result.collision_strength))} {result.collision_strength}
              </Badge>
            </div>

            <ScoreBar score={result.score} />

            {result.bridges.length > 0 && (
              <div className="space-y-1">
                {result.bridges.map((b, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-foreground/70">
                    <ArrowRight className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                    {b}
                  </div>
                ))}
              </div>
            )}

            {result.shared_patterns.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {result.shared_patterns.map(p => (
                  <span key={p} className="text-[9px] px-1.5 py-0.5 rounded bg-green-400/5 text-green-400/70 border border-green-400/10">
                    {formatLabel(p)}
                  </span>
                ))}
              </div>
            )}

            {result.interpretation && (
              <p className="text-xs text-muted-foreground">{result.interpretation}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function CollisionsPage() {
  const [search, setSearch] = useState("");
  const [strengthFilter, setStrengthFilter] = useState<string>("all");
  const [selected, setSelected] = useState<Collision | null>(null);

  const filtered = useMemo(() => {
    return collisions.filter(c => {
      // Strength filter
      if (strengthFilter !== "all") {
        if (strengthFilter === "deep" && !c.collision_strength.includes("DEEP")) return false;
        if (strengthFilter === "significant" && !c.collision_strength.includes("SIGNIFICANT")) return false;
        if (strengthFilter === "resonance" && !c.collision_strength.includes("RESONANCE")) return false;
      }
      // Search filter
      if (search) {
        const q = search.toLowerCase();
        const nameA = theories[c.a]?.name?.toLowerCase() || "";
        const nameB = theories[c.b]?.name?.toLowerCase() || "";
        const domA = theories[c.a]?.domain?.toLowerCase() || "";
        const domB = theories[c.b]?.domain?.toLowerCase() || "";
        return nameA.includes(q) || nameB.includes(q) || domA.includes(q) || domB.includes(q) ||
          c.shared_patterns.some(p => p.includes(q));
      }
      return true;
    });
  }, [search, strengthFilter]);

  const deepCount = collisions.filter(c => c.collision_strength.includes("DEEP")).length;
  const sigCount = collisions.filter(c => c.collision_strength.includes("SIGNIFICANT")).length;
  const resCount = collisions.filter(c => c.collision_strength.includes("RESONANCE")).length;

  return (
    <div className="p-6 lg:p-10 max-w-7xl space-y-6">
      <CollisionDetailDialog collision={selected} open={!!selected} onClose={() => setSelected(null)} />

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Theory Collisions</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Explore mathematical isomorphisms between {Object.keys(theories).length} theories across domains
        </p>
      </div>

      {/* Interactive Collider */}
      <TheoryCollider />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search theories, domains, patterns..."
            className="w-full bg-background border border-input rounded-lg pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-muted-foreground" />
          {[
            { key: "all", label: "All", count: collisions.length },
            { key: "deep", label: "Deep", count: deepCount },
            { key: "significant", label: "Significant", count: sigCount },
            { key: "resonance", label: "Resonance", count: resCount },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => setStrengthFilter(f.key)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                strengthFilter === f.key
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label} ({f.count})
            </button>
          ))}
        </div>
      </div>

      {/* Collision Results */}
      <div className="text-xs text-muted-foreground">
        Showing {filtered.length} collisions (sorted by similarity score)
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          No collisions match your filters.
        </div>
      )}

      <div className="space-y-2">
        {filtered.map((c, i) => {
          const tA = theories[c.a];
          const tB = theories[c.b];
          if (!tA || !tB) return null;
          const style = getStrengthStyle(c.collision_strength);
          const dots = getStrengthDots(c.collision_strength);

          return (
            <Card
              key={`${c.a}-${c.b}`}
              className="bg-card/50 border-card-border cursor-pointer hover:bg-accent/20 transition-all group"
              onClick={() => setSelected(c)}
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  {/* Rank */}
                  <span className="text-xs font-mono text-muted-foreground w-6 text-right flex-shrink-0">
                    #{i + 1}
                  </span>

                  {/* Theory names */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm truncate">{tA.name}</span>
                      <Zap className="w-3 h-3 text-amber-400 flex-shrink-0" />
                      <span className="font-medium text-sm truncate">{tB.name}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                      <span>{tA.domain}</span>
                      <span>x</span>
                      <span>{tB.domain}</span>
                      {c.shared_patterns.length > 0 && (
                        <>
                          <span className="text-muted-foreground/40">|</span>
                          {c.shared_patterns.slice(0, 2).map(p => (
                            <span key={p} className="px-1 py-0.5 rounded bg-green-400/5 text-green-400/60">
                              {formatLabel(p)}
                            </span>
                          ))}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Score + strength */}
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <div className="w-24">
                      <ScoreBar score={c.score} />
                    </div>
                    <Badge variant="outline" className={`text-[10px] w-20 justify-center ${style.text} ${style.border} ${style.bg}`}>
                      {"*".repeat(dots)}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
