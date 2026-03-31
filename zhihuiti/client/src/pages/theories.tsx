import { useState, useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Atom, ChevronRight, Zap, BookOpen } from "lucide-react";
import theoriesData from "@/data/theories.json";
import skeletonsData from "@/data/skeletons.json";
import historicalData from "@/data/historical.json";

type Theory = {
  id: string;
  name: string;
  domain: string;
  equation: string;
  update_form: string;
  optimization: string;
  fixed_points: string;
  operators: string[];
  patterns: string[];
  variables: Record<string, string>;
  conservation: string[];
  structure: string;
};

type Skeleton = {
  id: number;
  name: string;
  form: string;
  description: string;
  domains: string[];
  color: string;
};

type HistoricalCase = {
  id: string;
  title: string;
  year: number;
  domains: string[];
  bridge_from: string;
  bridge_to: string;
  breakthrough: string;
  skeleton: string;
};

const theories = theoriesData as unknown as Record<string, Theory>;
const skeletons = skeletonsData as Skeleton[];
const historical = historicalData as HistoricalCase[];

// Domain color mapping
const DOMAIN_COLORS: Record<string, string> = {
  "Evolutionary Game Theory": "text-red-400 border-red-400/30 bg-red-400/10",
  "Statistical Mechanics": "text-orange-400 border-orange-400/30 bg-orange-400/10",
  "Statistical Physics": "text-orange-300 border-orange-300/30 bg-orange-300/10",
  "Control Theory": "text-green-400 border-green-400/30 bg-green-400/10",
  "Information Theory": "text-blue-400 border-blue-400/30 bg-blue-400/10",
  "Cognitive Science": "text-purple-400 border-purple-400/30 bg-purple-400/10",
  "Neuroscience": "text-pink-400 border-pink-400/30 bg-pink-400/10",
  "Neuroscience / Cognitive Science": "text-pink-400 border-pink-400/30 bg-pink-400/10",
  "Machine Learning": "text-cyan-400 border-cyan-400/30 bg-cyan-400/10",
  "Dynamic Systems": "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
  "Physics": "text-indigo-400 border-indigo-400/30 bg-indigo-400/10",
  "Quantum Physics": "text-violet-400 border-violet-400/30 bg-violet-400/10",
  "Meta-Frameworks": "text-emerald-400 border-emerald-400/30 bg-emerald-400/10",
  "Mathematics": "text-teal-400 border-teal-400/30 bg-teal-400/10",
  "Optimization": "text-lime-400 border-lime-400/30 bg-lime-400/10",
  "Reinforcement Learning": "text-sky-400 border-sky-400/30 bg-sky-400/10",
  "Statistics": "text-amber-400 border-amber-400/30 bg-amber-400/10",
  "Economics": "text-rose-400 border-rose-400/30 bg-rose-400/10",
  "Topology": "text-fuchsia-400 border-fuchsia-400/30 bg-fuchsia-400/10",
  "Biology": "text-green-300 border-green-300/30 bg-green-300/10",
  "Computer Science": "text-slate-400 border-slate-400/30 bg-slate-400/10",
  "Game Theory": "text-red-300 border-red-300/30 bg-red-300/10",
  "Network Science": "text-blue-300 border-blue-300/30 bg-blue-300/10",
  "Signal Processing": "text-yellow-300 border-yellow-300/30 bg-yellow-300/10",
  "Thermodynamics": "text-orange-500 border-orange-500/30 bg-orange-500/10",
};

function getDomainColor(domain: string) {
  return DOMAIN_COLORS[domain] || "text-gray-400 border-gray-400/30 bg-gray-400/10";
}

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function TheoryDetailDialog({ theory, open, onClose }: { theory: Theory | null; open: boolean; onClose: () => void }) {
  if (!theory) return null;
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-card border-card-border max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl">{theory.name}</DialogTitle>
          <DialogDescription>
            <Badge variant="outline" className={`mt-1 text-[11px] ${getDomainColor(theory.domain)}`}>
              {theory.domain}
            </Badge>
          </DialogDescription>
        </DialogHeader>

        {/* Equation */}
        {theory.equation && (
          <div className="bg-background border border-border rounded-lg p-4">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Core Equation</p>
            <code className="text-sm text-cyan-400 font-mono leading-relaxed break-all">{theory.equation}</code>
          </div>
        )}

        {/* Properties Grid */}
        <div className="grid grid-cols-2 gap-3">
          {theory.update_form && (
            <div className="bg-background border border-border rounded-lg p-3">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">Update Form</p>
              <p className="text-sm font-medium">{formatLabel(theory.update_form)}</p>
            </div>
          )}
          {theory.optimization && (
            <div className="bg-background border border-border rounded-lg p-3">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">Optimization</p>
              <p className="text-sm font-medium">{formatLabel(theory.optimization)}</p>
            </div>
          )}
          {theory.fixed_points && (
            <div className="bg-background border border-border rounded-lg p-3">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">Fixed Points</p>
              <p className="text-sm font-medium">{formatLabel(theory.fixed_points)}</p>
            </div>
          )}
          {theory.structure && (
            <div className="bg-background border border-border rounded-lg p-3">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">Structure</p>
              <p className="text-sm font-medium">{formatLabel(theory.structure)}</p>
            </div>
          )}
        </div>

        {/* Variables */}
        {Object.keys(theory.variables).length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Variable Mappings</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(theory.variables).map(([role, value]) => (
                <div key={role} className="bg-background border border-border rounded-md px-2.5 py-1.5 text-xs">
                  <span className="text-muted-foreground">{role}:</span>{" "}
                  <span className="font-medium text-foreground">{formatLabel(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Patterns */}
        {theory.patterns.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Structural Patterns</p>
            <div className="flex flex-wrap gap-1.5">
              {theory.patterns.map(p => (
                <Badge key={p} variant="outline" className="text-[10px] text-cyan-400 border-cyan-400/30 bg-cyan-400/5">
                  {formatLabel(p)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Operators */}
        {theory.operators.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Operators</p>
            <div className="flex flex-wrap gap-1.5">
              {theory.operators.map(o => (
                <Badge key={o} variant="outline" className="text-[10px] text-amber-400 border-amber-400/30 bg-amber-400/5">
                  {formatLabel(o)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Conservation */}
        {theory.conservation.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Conserved Quantities</p>
            <div className="flex flex-wrap gap-1.5">
              {theory.conservation.map(c => (
                <Badge key={c} variant="outline" className="text-[10px] text-green-400 border-green-400/30 bg-green-400/5">
                  {formatLabel(c)}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function TheoriesGrid({ search }: { search: string }) {
  const theoryList = useMemo(() => Object.values(theories), []);

  // Group by domain
  const grouped = useMemo(() => {
    const filtered = theoryList.filter(t => {
      const q = search.toLowerCase();
      return !q ||
        t.name.toLowerCase().includes(q) ||
        t.domain.toLowerCase().includes(q) ||
        t.equation.toLowerCase().includes(q) ||
        t.patterns.some(p => p.includes(q));
    });
    const map: Record<string, Theory[]> = {};
    for (const t of filtered) {
      if (!map[t.domain]) map[t.domain] = [];
      map[t.domain].push(t);
    }
    return Object.entries(map).sort((a, b) => b[1].length - a[1].length);
  }, [theoryList, search]);

  const [selected, setSelected] = useState<Theory | null>(null);

  return (
    <>
      <TheoryDetailDialog theory={selected} open={!!selected} onClose={() => setSelected(null)} />

      {grouped.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          No theories match your search.
        </div>
      )}

      {grouped.map(([domain, domainTheories]) => (
        <div key={domain} className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <Badge variant="outline" className={`text-xs font-semibold ${getDomainColor(domain)}`}>
              {domain}
            </Badge>
            <span className="text-xs text-muted-foreground">{domainTheories.length} theories</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {domainTheories.map(t => (
              <Card
                key={t.id}
                className="bg-card/50 border-card-border cursor-pointer hover:bg-accent/20 transition-all hover:shadow-md group"
                onClick={() => setSelected(t)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-sm leading-tight group-hover:text-cyan-400 transition-colors">
                      {t.name}
                    </h3>
                    <ChevronRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-0.5" />
                  </div>
                  {t.equation && (
                    <code className="text-[11px] text-muted-foreground font-mono block mb-2 truncate">
                      {t.equation}
                    </code>
                  )}
                  <div className="flex flex-wrap gap-1 mt-auto">
                    {t.patterns.slice(0, 3).map(p => (
                      <span key={p} className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-400/5 text-cyan-400/70 border border-cyan-400/10">
                        {formatLabel(p)}
                      </span>
                    ))}
                    {t.patterns.length > 3 && (
                      <span className="text-[9px] px-1.5 py-0.5 text-muted-foreground">
                        +{t.patterns.length - 3}
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

function SkeletonsView() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground mb-4">
        The same abstract mathematical skeleton appears in different domains because nature reuses a small set of deep patterns.
      </p>
      {skeletons.map(s => (
        <Card key={s.id} className="bg-card/50 border-card-border overflow-hidden">
          <CardContent className="p-5">
            <div className="flex items-start gap-3 mb-3">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0"
                style={{ background: s.color + "20", color: s.color }}
              >
                {s.id}
              </div>
              <div>
                <h3 className="font-semibold text-sm" style={{ color: s.color }}>{s.name}</h3>
                <code className="text-xs text-muted-foreground font-mono">{s.form}</code>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-3">{s.description}</p>
            <div className="flex flex-wrap gap-1.5">
              {s.domains.map(d => (
                <Badge key={d} variant="outline" className={`text-[10px] ${getDomainColor(d)}`}>
                  {d}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function HistoricalView() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground mb-4">
        Six major breakthroughs where mathematical structures from one domain applied perfectly in another.
      </p>
      {historical.map(h => (
        <Card key={h.id} className="bg-card/50 border-card-border">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-400/30 bg-amber-400/10">
                {h.year}
              </Badge>
              <Badge variant="outline" className="text-[10px] text-purple-400 border-purple-400/30 bg-purple-400/10">
                {h.skeleton}
              </Badge>
            </div>
            <h3 className="font-semibold text-sm mb-3">{h.title}</h3>

            <div className="bg-background border border-border rounded-lg p-3 mb-3 space-y-2">
              <div className="flex items-start gap-2">
                <span className="text-[10px] uppercase tracking-widest text-muted-foreground w-12 flex-shrink-0 pt-0.5">From</span>
                <code className="text-xs text-red-400 font-mono">{h.bridge_from}</code>
              </div>
              <div className="flex items-center justify-center">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div className="flex items-start gap-2">
                <span className="text-[10px] uppercase tracking-widest text-muted-foreground w-12 flex-shrink-0 pt-0.5">To</span>
                <code className="text-xs text-green-400 font-mono">{h.bridge_to}</code>
              </div>
            </div>

            <p className="text-sm text-muted-foreground">{h.breakthrough}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function TheoriesPage() {
  const [search, setSearch] = useState("");
  const totalTheories = Object.keys(theories).length;
  const domains = new Set(Object.values(theories).map(t => t.domain));

  return (
    <div className="p-6 lg:p-10 max-w-7xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Theory Library</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {totalTheories} mathematical theories across {domains.size} domains
        </p>
      </div>

      <Tabs defaultValue="theories">
        <TabsList>
          <TabsTrigger value="theories" className="gap-1.5">
            <Atom className="w-3.5 h-3.5" />
            All Theories
          </TabsTrigger>
          <TabsTrigger value="skeletons" className="gap-1.5">
            <Zap className="w-3.5 h-3.5" />
            7 Universal Skeletons
          </TabsTrigger>
          <TabsTrigger value="historical" className="gap-1.5">
            <BookOpen className="w-3.5 h-3.5" />
            Historical Breakthroughs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="theories">
          {/* Search */}
          <div className="relative my-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search theories, domains, patterns..."
              className="w-full bg-background border border-input rounded-lg pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <TheoriesGrid search={search} />
        </TabsContent>

        <TabsContent value="skeletons">
          <div className="mt-4">
            <SkeletonsView />
          </div>
        </TabsContent>

        <TabsContent value="historical">
          <div className="mt-4">
            <HistoricalView />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
