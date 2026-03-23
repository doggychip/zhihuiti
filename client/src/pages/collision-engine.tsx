import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Zap, Shuffle, ChevronRight, Star, Clock, Link2, Atom,
  Sparkles, ArrowRight, X, History, AlertTriangle,
} from "lucide-react";
import {
  THEORIES, DOMAINS, COLLISION_MODES, DOMAIN_COLORS, DOMAIN_CLASSES,
  getTheoriesByDomain,
  type CollisionTheory, type DomainKey, type CollisionMode,
} from "@/data/collision-theories";

// ─── Types ───────────────────────────────────────────────────
interface CollisionResult {
  id: string;
  theoryA: CollisionTheory;
  theoryB: CollisionTheory;
  mode: CollisionMode;
  modeLabel: string;
  framework_name: string;
  core_insight: string;
  structural_similarities: string[];
  novel_connections: string[];
  practical_applications: string[];
  quality_score: number;
  reasoning: string;
  timestamp: number;
}

// ─── Collision Animation ─────────────────────────────────────
function CollisionAnimation({ colorA, colorB }: { colorA: string; colorB: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="relative w-40 h-40">
        {/* Circle A */}
        <div
          className="absolute w-16 h-16 rounded-full animate-collision-left"
          style={{ background: `radial-gradient(circle, ${colorA}60, ${colorA}20)`, border: `2px solid ${colorA}`, boxShadow: `0 0 20px ${colorA}40` }}
        />
        {/* Circle B */}
        <div
          className="absolute right-0 w-16 h-16 rounded-full animate-collision-right"
          style={{ background: `radial-gradient(circle, ${colorB}60, ${colorB}20)`, border: `2px solid ${colorB}`, boxShadow: `0 0 20px ${colorB}40` }}
        />
        {/* Center flash */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-8 h-8 rounded-full animate-collision-flash bg-white/0" />
        </div>
      </div>
    </div>
  );
}

// ─── Score Badge ─────────────────────────────────────────────
function ScoreBadge({ score }: { score: number }) {
  const color = score >= 8 ? "text-emerald-400 border-emerald-400/30 bg-emerald-400/10"
    : score >= 6 ? "text-amber-400 border-amber-400/30 bg-amber-400/10"
    : "text-red-400 border-red-400/30 bg-red-400/10";
  return (
    <Badge variant="outline" className={`text-sm font-bold px-2.5 py-1 ${color}`}>
      <Star className="w-3.5 h-3.5 mr-1" />
      {score}/10
    </Badge>
  );
}

// ─── Theory Card (selectable) ────────────────────────────────
function TheoryCard({
  theory,
  selected,
  disabled,
  onSelect,
}: {
  theory: CollisionTheory;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  const dc = DOMAIN_CLASSES[theory.domain as DomainKey];
  return (
    <div
      onClick={disabled && !selected ? undefined : onSelect}
      className={`
        px-3 py-2.5 rounded-lg border transition-all text-left
        ${selected
          ? `border-[${DOMAIN_COLORS[theory.domain as DomainKey]}] ring-1 bg-white/5`
          : disabled
            ? "border-border/30 opacity-40 cursor-not-allowed"
            : "border-border/50 cursor-pointer hover:bg-white/[0.03] hover:border-border"
        }
      `}
      style={selected ? { borderColor: DOMAIN_COLORS[theory.domain as DomainKey], boxShadow: `0 0 12px ${DOMAIN_COLORS[theory.domain as DomainKey]}20` } : {}}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="min-w-0">
          <p className={`text-xs font-semibold leading-tight ${selected ? dc.text : "text-foreground/90"}`}>
            {theory.name}
          </p>
          <p className="text-[10px] text-muted-foreground">{theory.nameCn}</p>
        </div>
        {selected && (
          <div className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
            style={{ background: DOMAIN_COLORS[theory.domain as DomainKey] }}>
            <span className="text-[8px] text-black font-bold">✓</span>
          </div>
        )}
      </div>
      <p className="text-[10px] text-muted-foreground/70 leading-relaxed mb-1.5 line-clamp-2">{theory.core}</p>
      <div className="flex flex-wrap gap-1">
        {theory.factors.map(f => (
          <span key={f} className={`text-[8px] px-1.5 py-0.5 rounded-full border ${dc.border} ${dc.bg} ${dc.text}`}>
            {f}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Result Card ─────────────────────────────────────────────
function ResultCard({ result, compact, onClick }: { result: CollisionResult; compact?: boolean; onClick?: () => void }) {
  const dcA = DOMAIN_CLASSES[result.theoryA.domain as DomainKey];
  const dcB = DOMAIN_CLASSES[result.theoryB.domain as DomainKey];

  if (compact) {
    return (
      <div
        onClick={onClick}
        className="px-3 py-2.5 rounded-lg border border-border/50 cursor-pointer hover:bg-white/[0.03] hover:border-border transition-all group"
      >
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs font-semibold truncate flex-1 group-hover:text-cyan-400 transition-colors">
            {result.framework_name}
          </p>
          <ScoreBadge score={result.quality_score} />
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <span className={dcA.text}>{result.theoryA.name}</span>
          <Zap className="w-2.5 h-2.5 text-amber-400" />
          <span className={dcB.text}>{result.theoryB.name}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">{result.framework_name}</h3>
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span className={dcA.text}>{result.theoryA.name}</span>
            <Zap className="w-3 h-3 text-amber-400" />
            <span className={dcB.text}>{result.theoryB.name}</span>
            <span className="text-muted-foreground/40">|</span>
            <span>{result.modeLabel}</span>
          </div>
        </div>
        <ScoreBadge score={result.quality_score} />
      </div>

      {/* Core Insight */}
      <div className="bg-background border border-border rounded-lg p-4">
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Core Insight</p>
        <p className="text-sm text-foreground/90 leading-relaxed">{result.core_insight}</p>
      </div>

      {/* Structural Similarities */}
      {result.structural_similarities.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Structural Similarities</p>
          <div className="space-y-1.5">
            {result.structural_similarities.map((s, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                <ArrowRight className="w-3 h-3 text-cyan-400 mt-0.5 flex-shrink-0" />
                {s}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Novel Connections */}
      {result.novel_connections.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Novel Connections</p>
          <div className="space-y-1.5">
            {result.novel_connections.map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                <Sparkles className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                {c}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Practical Applications */}
      {result.practical_applications.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Practical Applications</p>
          <div className="flex flex-wrap gap-1.5">
            {result.practical_applications.map((a, i) => (
              <Badge key={i} variant="outline" className="text-[10px] text-emerald-400 border-emerald-400/30 bg-emerald-400/5">
                {a}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Reasoning */}
      {result.reasoning && (
        <p className="text-xs text-muted-foreground/60 italic">{result.reasoning}</p>
      )}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────
export default function CollisionEnginePage() {
  const [activeDomain, setActiveDomain] = useState<DomainKey>("Quantum Physics");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [collisionMode, setCollisionMode] = useState<CollisionMode>("fuse");
  const [isColliding, setIsColliding] = useState(false);
  const [currentResult, setCurrentResult] = useState<CollisionResult | null>(null);
  const [history, setHistory] = useState<CollisionResult[]>([]);
  const [viewingResult, setViewingResult] = useState<CollisionResult | null>(null);
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("zh_claude_api_key") ?? "");
  const [apiKeyOpen, setApiKeyOpen] = useState(false);
  const [error, setError] = useState("");
  const resultRef = useRef<HTMLDivElement>(null);

  const selectedTheories = useMemo(
    () => selectedIds.map(id => THEORIES.find(t => t.id === id)!).filter(Boolean),
    [selectedIds],
  );

  const domainTheories = useMemo(
    () => getTheoriesByDomain(activeDomain),
    [activeDomain],
  );

  // Save API key
  useEffect(() => {
    if (apiKey) localStorage.setItem("zh_claude_api_key", apiKey);
  }, [apiKey]);

  const handleSelect = useCallback((id: number) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
    setCurrentResult(null);
    setError("");
  }, []);

  const handleRandomPair = useCallback(() => {
    const domainKeys = [...DOMAINS];
    // Pick two different domains
    const d1Idx = Math.floor(Math.random() * domainKeys.length);
    let d2Idx = Math.floor(Math.random() * (domainKeys.length - 1));
    if (d2Idx >= d1Idx) d2Idx++;
    const theories1 = getTheoriesByDomain(domainKeys[d1Idx]);
    const theories2 = getTheoriesByDomain(domainKeys[d2Idx]);
    const t1 = theories1[Math.floor(Math.random() * theories1.length)];
    const t2 = theories2[Math.floor(Math.random() * theories2.length)];
    setSelectedIds([t1.id, t2.id]);
    setCurrentResult(null);
    setError("");
  }, []);

  const handleCollide = useCallback(async () => {
    if (selectedTheories.length !== 2) return;
    if (!apiKey) {
      setApiKeyOpen(true);
      return;
    }

    const [theoryA, theoryB] = selectedTheories;
    const mode = COLLISION_MODES.find(m => m.key === collisionMode)!;

    setIsColliding(true);
    setCurrentResult(null);
    setError("");

    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
          "anthropic-dangerous-direct-browser-access": "true",
        },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1200,
          messages: [{
            role: "user",
            content: `You are a cross-disciplinary synthesis engine. Given two theories from different domains, find deep structural connections and generate a novel framework.

THEORY A: ${theoryA.name} (${theoryA.domain})
Core: ${theoryA.core}
Key factors: ${theoryA.factors.join(", ")}

THEORY B: ${theoryB.name} (${theoryB.domain})
Core: ${theoryB.core}
Key factors: ${theoryB.factors.join(", ")}

COLLISION MODE: ${mode.label} (${mode.labelCn}) — ${mode.desc}

Respond ONLY in JSON (no markdown, no backticks):
{
  "framework_name": "A creative name for the new framework (English + Chinese)",
  "core_insight": "2-3 sentences describing the novel insight from this collision",
  "structural_similarities": ["list of 3-4 deep structural parallels found"],
  "novel_connections": ["list of 2-3 genuinely surprising cross-domain links"],
  "practical_applications": ["list of 2-3 concrete business/product applications"],
  "quality_score": 7,
  "reasoning": "1 sentence on why this collision is or isn't productive"
}`,
          }],
        }),
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({ error: { message: `HTTP ${res.status}` } }));
        throw new Error(errBody.error?.message ?? `API error: ${res.status}`);
      }

      const data = await res.json();
      const text = data.content?.[0]?.text ?? "";

      // Parse JSON from response (handle potential markdown wrapping)
      let jsonStr = text.trim();
      if (jsonStr.startsWith("```")) {
        jsonStr = jsonStr.replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "");
      }
      const parsed = JSON.parse(jsonStr);

      const result: CollisionResult = {
        id: crypto.randomUUID(),
        theoryA,
        theoryB,
        mode: collisionMode,
        modeLabel: mode.label,
        ...parsed,
        quality_score: Math.min(10, Math.max(1, Math.round(parsed.quality_score ?? 5))),
        timestamp: Date.now(),
      };

      setCurrentResult(result);
      setHistory(prev => [result, ...prev]);

      // Scroll to result
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (err: any) {
      setError(err.message ?? "Collision failed");
    } finally {
      setIsColliding(false);
    }
  }, [selectedTheories, collisionMode, apiKey]);

  const handleChainCollide = useCallback((result: CollisionResult) => {
    // Create a virtual theory from the collision result
    const virtualTheory: CollisionTheory = {
      id: -result.timestamp,
      name: result.framework_name,
      nameCn: "",
      domain: `${result.theoryA.domain} x ${result.theoryB.domain}` as any,
      core: result.core_insight,
      factors: result.structural_similarities.slice(0, 3),
    };
    // Store it temporarily and select it
    THEORIES.push(virtualTheory);
    setSelectedIds([virtualTheory.id]);
    setCurrentResult(null);
    setError("");
  }, []);

  const modeInfo = COLLISION_MODES.find(m => m.key === collisionMode)!;
  const colorA = selectedTheories[0] ? (DOMAIN_COLORS[selectedTheories[0].domain as DomainKey] ?? "#666") : "#666";
  const colorB = selectedTheories[1] ? (DOMAIN_COLORS[selectedTheories[1].domain as DomainKey] ?? "#666") : "#666";

  return (
    <div className="p-4 lg:p-6 max-w-[1600px] h-[calc(100vh-48px)] md:h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <Atom className="w-5 h-5 text-cyan-400" />
            Theory Collision Engine
            <span className="text-muted-foreground text-sm font-normal ml-1">智力合成引擎</span>
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Select 2 theories from different domains, pick a collision mode, and discover novel frameworks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="text-xs h-7"
            onClick={() => setApiKeyOpen(true)}
          >
            {apiKey ? "API Key Set" : "Set API Key"}
          </Button>
        </div>
      </div>

      {/* Three-panel layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[280px_1fr_260px] gap-4 min-h-0">
        {/* ─── LEFT: Theory Library ─── */}
        <div className="flex flex-col min-h-0 border border-border/50 rounded-lg bg-card/30 overflow-hidden">
          <div className="px-3 py-2.5 border-b border-border/50 flex-shrink-0">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-foreground/80">Theory Library</p>
              <Button
                variant="outline"
                size="sm"
                className="h-6 px-2 text-[10px] gap-1"
                onClick={handleRandomPair}
              >
                <Shuffle className="w-3 h-3" />
                Random Pair
              </Button>
            </div>
            {/* Domain tabs */}
            <div className="flex flex-wrap gap-1">
              {DOMAINS.map(d => {
                const dc = DOMAIN_CLASSES[d];
                const isActive = activeDomain === d;
                const count = getTheoriesByDomain(d).length;
                const hasSelected = selectedIds.some(id => THEORIES.find(t => t.id === id)?.domain === d);
                return (
                  <button
                    key={d}
                    onClick={() => setActiveDomain(d)}
                    className={`px-2 py-1 rounded text-[9px] font-medium transition-colors ${
                      isActive
                        ? `${dc.bg} ${dc.text} ${dc.border} border`
                        : "text-muted-foreground hover:text-foreground bg-muted/30 hover:bg-muted/50"
                    }`}
                  >
                    {d.split(" ").map(w => w[0]).join("")}
                    <span className="ml-0.5 opacity-60">{count}</span>
                    {hasSelected && <span className="ml-0.5 w-1 h-1 rounded-full inline-block" style={{ background: DOMAIN_COLORS[d] }} />}
                  </button>
                );
              })}
            </div>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1.5">
              {domainTheories.map(t => (
                <TheoryCard
                  key={t.id}
                  theory={t}
                  selected={selectedIds.includes(t.id)}
                  disabled={selectedIds.length >= 2 && !selectedIds.includes(t.id)}
                  onSelect={() => handleSelect(t.id)}
                />
              ))}
            </div>
          </ScrollArea>

          {selectedIds.length > 0 && (
            <div className="px-3 py-2 border-t border-border/50 flex-shrink-0">
              <p className="text-[10px] text-muted-foreground mb-1">Selected ({selectedIds.length}/2)</p>
              <div className="space-y-1">
                {selectedTheories.map(t => (
                  <div key={t.id} className="flex items-center justify-between text-[10px]">
                    <span className={DOMAIN_CLASSES[t.domain as DomainKey].text}>{t.name}</span>
                    <button onClick={() => handleSelect(t.id)} className="text-muted-foreground hover:text-foreground">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ─── CENTER: Collision Zone ─── */}
        <div className="flex flex-col min-h-0 overflow-auto">
          {/* Selected theories display */}
          <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-start mb-4 flex-shrink-0">
            {/* Theory A */}
            <Card className={`bg-card/50 border-card-border ${selectedTheories[0] ? "" : "opacity-40"}`}>
              <CardContent className="p-4">
                {selectedTheories[0] ? (
                  <>
                    <Badge variant="outline" className={`text-[10px] mb-2 ${DOMAIN_CLASSES[selectedTheories[0].domain as DomainKey].text} ${DOMAIN_CLASSES[selectedTheories[0].domain as DomainKey].border} ${DOMAIN_CLASSES[selectedTheories[0].domain as DomainKey].bg}`}>
                      {selectedTheories[0].domain}
                    </Badge>
                    <h3 className="text-sm font-semibold mb-0.5">{selectedTheories[0].name}</h3>
                    <p className="text-[10px] text-muted-foreground mb-0.5">{selectedTheories[0].nameCn}</p>
                    <p className="text-xs text-muted-foreground/70 leading-relaxed">{selectedTheories[0].core}</p>
                  </>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-xs text-muted-foreground">Select Theory A</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* VS / Collide controls */}
            <div className="flex flex-col items-center gap-2 pt-4">
              <Zap className="w-5 h-5 text-amber-400" />
              <select
                value={collisionMode}
                onChange={e => setCollisionMode(e.target.value as CollisionMode)}
                className="bg-background border border-input rounded-md px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring w-[130px] text-center"
              >
                {COLLISION_MODES.map(m => (
                  <option key={m.key} value={m.key}>{m.label} ({m.labelCn})</option>
                ))}
              </select>
              <p className="text-[9px] text-muted-foreground text-center max-w-[130px] leading-tight">
                {modeInfo.desc}
              </p>
              <Button
                onClick={handleCollide}
                disabled={selectedTheories.length !== 2 || isColliding}
                className="mt-1 font-bold text-sm text-white px-6 py-2 h-auto"
                style={{
                  background: selectedTheories.length === 2
                    ? `linear-gradient(135deg, ${colorA}, ${colorB})`
                    : undefined,
                }}
              >
                {isColliding ? "COLLIDING..." : "COLLIDE"}
              </Button>
            </div>

            {/* Theory B */}
            <Card className={`bg-card/50 border-card-border ${selectedTheories[1] ? "" : "opacity-40"}`}>
              <CardContent className="p-4">
                {selectedTheories[1] ? (
                  <>
                    <Badge variant="outline" className={`text-[10px] mb-2 ${DOMAIN_CLASSES[selectedTheories[1].domain as DomainKey].text} ${DOMAIN_CLASSES[selectedTheories[1].domain as DomainKey].border} ${DOMAIN_CLASSES[selectedTheories[1].domain as DomainKey].bg}`}>
                      {selectedTheories[1].domain}
                    </Badge>
                    <h3 className="text-sm font-semibold mb-0.5">{selectedTheories[1].name}</h3>
                    <p className="text-[10px] text-muted-foreground mb-0.5">{selectedTheories[1].nameCn}</p>
                    <p className="text-xs text-muted-foreground/70 leading-relaxed">{selectedTheories[1].core}</p>
                  </>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-xs text-muted-foreground">Select Theory B</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm mb-4 flex-shrink-0">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-xs">Collision Failed</p>
                <p className="text-[11px] opacity-80">{error}</p>
              </div>
            </div>
          )}

          {/* Collision animation */}
          {isColliding && (
            <CollisionAnimation colorA={colorA} colorB={colorB} />
          )}

          {/* Result */}
          <div ref={resultRef}>
            {currentResult && !isColliding && (
              <Card className="bg-card/50 border-card-border">
                <CardContent className="p-5">
                  <ResultCard result={currentResult} />
                </CardContent>
              </Card>
            )}
          </div>

          {/* Empty state */}
          {!currentResult && !isColliding && !error && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center py-12">
                <Atom className="w-12 h-12 text-muted-foreground/20 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground/40">
                  Select two theories and collide them to discover novel frameworks
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ─── RIGHT: History ─── */}
        <div className="flex flex-col min-h-0 border border-border/50 rounded-lg bg-card/30 overflow-hidden">
          <div className="px-3 py-2.5 border-b border-border/50 flex-shrink-0">
            <div className="flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-muted-foreground" />
              <p className="text-xs font-semibold text-foreground/80">Collision History</p>
              <span className="text-[10px] text-muted-foreground ml-auto">{history.length}</span>
            </div>
          </div>

          <ScrollArea className="flex-1">
            {history.length === 0 ? (
              <div className="p-4 text-center">
                <Clock className="w-6 h-6 text-muted-foreground/20 mx-auto mb-2" />
                <p className="text-[10px] text-muted-foreground/40">No collisions yet</p>
              </div>
            ) : (
              <div className="p-2 space-y-1.5">
                {history.map(r => (
                  <div key={r.id}>
                    <ResultCard
                      result={r}
                      compact
                      onClick={() => setViewingResult(r)}
                    />
                    <button
                      onClick={() => handleChainCollide(r)}
                      className="w-full mt-1 flex items-center justify-center gap-1 text-[9px] text-muted-foreground hover:text-cyan-400 transition-colors py-1"
                    >
                      <Link2 className="w-2.5 h-2.5" />
                      Chain Collide
                    </button>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      </div>

      {/* View past result dialog */}
      <Dialog open={!!viewingResult} onOpenChange={() => setViewingResult(null)}>
        <DialogContent className="bg-card border-card-border max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Collision Result</DialogTitle>
          </DialogHeader>
          {viewingResult && <ResultCard result={viewingResult} />}
        </DialogContent>
      </Dialog>

      {/* API Key dialog */}
      <Dialog open={apiKeyOpen} onOpenChange={setApiKeyOpen}>
        <DialogContent className="bg-card border-card-border max-w-md">
          <DialogHeader>
            <DialogTitle>Claude API Key</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <p className="text-xs text-muted-foreground">
              Enter your Anthropic API key to power theory collisions. The key is stored locally in your browser only.
            </p>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="sk-ant-..."
              className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <Button
              className="w-full bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
              onClick={() => setApiKeyOpen(false)}
              disabled={!apiKey}
            >
              Save Key
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
