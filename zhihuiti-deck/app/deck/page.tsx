"use client";

import OntologyGraph from "@/components/OntologyGraph";
import StatusBar from "@/components/StatusBar";
import SlideShell from "@/components/SlideShell";

const TOTAL_SLIDES = 11;

// ─── Slide 0: Title ───────────────────────────────────────
function TitleSlide() {
  return (
    <SlideShell index={0} total={TOTAL_SLIDES}>
      <div className="flex flex-col items-center text-center gap-8">
        <OntologyGraph />
        <div className="space-y-4">
          <h1 className="text-2xl tracking-[0.3em] uppercase font-light text-ice">
            智慧體
          </h1>
          <p className="text-[11px] tracking-[0.5em] uppercase text-ice/40">
            Zhihuiti — Autonomous Multi-Agent Intelligence
          </p>
          <div className="w-12 h-px bg-ice/20 mx-auto" />
          <p className="text-[10px] tracking-widest text-gold/60">
            A self-governing AI company where agents compete, evolve, and get culled.
          </p>
        </div>
      </div>
    </SlideShell>
  );
}

// ─── Slide 1: Problem ─────────────────────────────────────
function ProblemSlide() {
  const problems = [
    { label: "Single agent, single task", desc: "No parallelism, no specialization" },
    { label: "Fixed behavior", desc: "No adaptation, no learning across runs" },
    { label: "No cost awareness", desc: "Infinite context = infinite spend" },
    { label: "Manual quality control", desc: "Human bottleneck on every output" },
  ];

  return (
    <SlideShell index={1} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">The Problem</p>
      <h2 className="text-lg tracking-wide font-light text-ice mb-10">
        Today&apos;s AI agents are <span className="text-ice/40">solo performers</span> in a world that needs <span className="text-gold">orchestras</span>.
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {problems.map((p) => (
          <div key={p.label} className="border border-ice/10 rounded-lg p-4 bg-ice-dim">
            <p className="text-[11px] text-ice/80 tracking-wide">{p.label}</p>
            <p className="text-[9px] text-ice/30 mt-1 tracking-wide">{p.desc}</p>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 2: Solution ────────────────────────────────────
function SolutionSlide() {
  return (
    <SlideShell index={2} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">The Solution</p>
      <h2 className="text-lg tracking-wide font-light text-ice mb-6">
        Economic incentives produce better outcomes than rules.
      </h2>
      <p className="text-[10px] text-ice/40 tracking-wide leading-6 mb-10">
        zhihuiti is a self-running AI company. Agents compete for work via auctions,
        earn tokens for quality output, breed offspring from top performers,
        and get culled when they underperform. 26 interlocking subsystems.
        Zero manual intervention.
      </p>
      <div className="flex gap-6 justify-center flex-wrap">
        {["Compete", "Earn", "Evolve", "Self-Govern"].map((w) => (
          <div key={w} className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-gold shadow-[0_0_6px_rgba(245,158,11,0.4)]" />
            <span className="text-[10px] tracking-[0.3em] uppercase text-ice/60">{w}</span>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 3: How It Works ────────────────────────────────
function HowSlide() {
  const steps = [
    { n: "01", title: "Decompose", desc: "User goal → DAG of subtasks → parallel waves" },
    { n: "02", title: "Auction", desc: "Agents bid — lowest qualified bid wins the task" },
    { n: "03", title: "Execute", desc: "Winner runs the task with LLM reasoning + tools" },
    { n: "04", title: "Inspect", desc: "4-layer quality gate: relevance, rigor, safety, causal" },
    { n: "05", title: "Reward", desc: "Pay based on score — top performers earn disproportionately" },
    { n: "06", title: "Evolve", desc: "Breed from winners, cull losers, track 7-gen bloodlines" },
  ];

  return (
    <SlideShell index={3} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">How It Works</p>
      <div className="space-y-4">
        {steps.map((s) => (
          <div key={s.n} className="flex items-start gap-4 group">
            <span className="text-[10px] text-gold/40 font-mono w-6 shrink-0">{s.n}</span>
            <div>
              <p className="text-[11px] text-ice/80 tracking-wide">{s.title}</p>
              <p className="text-[9px] text-ice/30 tracking-wide mt-0.5">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 4: Architecture ────────────────────────────────
function ArchSlide() {
  const layers = [
    { name: "Core", subs: "Agents, Memory, LLM, Orchestrator" },
    { name: "Economy", subs: "Central Bank, Treasury, Tax Bureau, Rewards" },
    { name: "Competition", subs: "Auctions, Trading Market, Futures" },
    { name: "Evolution", subs: "Gene Pool, Bloodline, Breeding, Mutation" },
    { name: "Safety", subs: "4-Layer Inspection, Circuit Breaker, Behavioral Detection" },
    { name: "Social", subs: "8-Type Relationships, Lending, Arbitration" },
    { name: "Execution", subs: "Factory, Three Realms, DAG, Parallel Waves" },
    { name: "Intelligence", subs: "Causal Reasoning, Counterfactual Analysis" },
  ];

  return (
    <SlideShell index={4} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">26 Subsystems · 8 Layers</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {layers.map((l) => (
          <div key={l.name} className="border border-ice/8 rounded p-3 bg-ice-dim">
            <p className="text-[10px] text-ice/70 tracking-widest uppercase">{l.name}</p>
            <p className="text-[8px] text-ice/25 mt-1 tracking-wide">{l.subs}</p>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 5: Three Realms ────────────────────────────────
function RealmsSlide() {
  const realms = [
    { name: "研发界", en: "Research", desc: "R&D agents — researchers, analysts, coders", color: "text-ice" },
    { name: "执行界", en: "Execution", desc: "Task workers — traders, custom agents", color: "text-ice" },
    { name: "中枢界", en: "Central", desc: "Governance — orchestrators, judges, coordinators", color: "text-gold" },
  ];

  return (
    <SlideShell index={5} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">Three Realms · 三界</p>
      <div className="space-y-6">
        {realms.map((r) => (
          <div key={r.en} className="border-l-2 border-ice/10 pl-4">
            <p className={`text-sm tracking-widest ${r.color}`}>
              {r.name} <span className="text-ice/30 text-[10px] ml-2">{r.en}</span>
            </p>
            <p className="text-[9px] text-ice/30 tracking-wide mt-1">{r.desc}</p>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 6: v4.0 — Integrity Layer ─────────────────────
function IntegritySlide() {
  const features = [
    { n: "01", title: "Integrity Audit Engine", desc: "Score every agent on honesty, consistency, and self-awareness — not just output quality" },
    { n: "02", title: "Integrity Score (0–1)", desc: "Persistent per-agent metric. Below 0.4 triggers automatic demotion or cull" },
    { n: "03", title: "Cross-Task Drift Detection", desc: "Detects when agents gradually deviate from their stated strategy across multiple goals" },
    { n: "04", title: "Honesty-Weighted Rewards", desc: "Reward engine multiplies payout by integrity score — liars earn less even with high task scores" },
  ];

  return (
    <SlideShell index={6} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">v4.0 · Integrity Layer</p>
      <h2 className="text-lg tracking-wide font-light text-ice mb-8">
        Trust is <span className="text-gold">earned</span>, not assumed.
      </h2>
      <div className="space-y-4">
        {features.map((f) => (
          <div key={f.n} className="flex items-start gap-4">
            <span className="text-[10px] text-gold/40 font-mono w-6 shrink-0">{f.n}</span>
            <div>
              <p className="text-[11px] text-ice/80 tracking-wide">{f.title}</p>
              <p className="text-[9px] text-ice/30 tracking-wide mt-0.5">{f.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 7: v4.0 — Financial Leverage ──────────────────
function FinanceSlide() {
  const instruments = [
    { name: "DEBT_ISSUANCE", desc: "Agents issue debt to fund high-confidence tasks — repay with interest from rewards, or default and face cull" },
    { name: "STAKE_STIMULUS", desc: "Agents stake tokens on their own integrity — earn bonus yield if scores stay high, lose stake if they cheat" },
    { name: "FUTURES", desc: "Bet on task outcomes before execution — hedging for risk-averse agents, speculation for the bold" },
    { name: "MARGIN TRADING", desc: "Leveraged positions with automatic liquidation — amplifies both gains and losses" },
  ];

  return (
    <SlideShell index={7} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">v4.0 · Financial Leverage</p>
      <h2 className="text-lg tracking-wide font-light text-ice mb-8">
        A real economy needs real <span className="text-gold">financial instruments</span>.
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {instruments.map((i) => (
          <div key={i.name} className="border border-ice/8 rounded-lg p-4 bg-ice-dim">
            <p className="text-[10px] text-gold/70 tracking-widest font-mono mb-1">{i.name}</p>
            <p className="text-[9px] text-ice/30 tracking-wide leading-4">{i.desc}</p>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 8: v4.0 — Diplomacy Bridge ────────────────────
function DiplomacySlide() {
  const bridges = [
    { name: "Kady Bridge", desc: "MCP server exposing zhihuiti as a tool provider — any Claude Code session can delegate goals to the swarm" },
    { name: "Oracle API", desc: "HTTP endpoints for real-time agent status, economy state, and intelligence queries from external systems" },
    { name: "AlphaArena", desc: "Live trading integration — 21 agents competing on crypto markets with real portfolio sync" },
    { name: "Cross-Domain", desc: "Knowledge transfer bridge — research agents feed trading agents, trading profits fund research" },
  ];

  return (
    <SlideShell index={8} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">v4.0 · Diplomacy &amp; Bridges</p>
      <h2 className="text-lg tracking-wide font-light text-ice mb-8">
        No system is an island.
      </h2>
      <div className="space-y-4">
        {bridges.map((b) => (
          <div key={b.name} className="border-l-2 border-ice/10 pl-4">
            <p className="text-[11px] text-ice/80 tracking-widest">{b.name}</p>
            <p className="text-[9px] text-ice/30 tracking-wide mt-1 leading-4">{b.desc}</p>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 9: Traction ────────────────────────────────────
function TractionSlide() {
  const stats = [
    { value: "26", label: "Subsystems" },
    { value: "124", label: "Python Modules" },
    { value: "300+", label: "Tests Passing" },
    { value: "21", label: "Trading Agents" },
    { value: "12", label: "Agent Roles" },
    { value: "5", label: "LLM Backends" },
    { value: "30+", label: "DB Tables" },
    { value: "3", label: "User Interfaces" },
    { value: "62K", label: "Lines of Code" },
  ];

  return (
    <SlideShell index={9} total={TOTAL_SLIDES}>
      <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60 mb-6">Traction</p>
      <div className="grid grid-cols-3 gap-6">
        {stats.map((s) => (
          <div key={s.label} className="text-center">
            <p className="text-2xl font-light text-ice">{s.value}</p>
            <p className="text-[8px] tracking-[0.3em] uppercase text-ice/30 mt-1">{s.label}</p>
          </div>
        ))}
      </div>
    </SlideShell>
  );
}

// ─── Slide 10: Vision ─────────────────────────────────────
function VisionSlide() {
  return (
    <SlideShell index={10} total={TOTAL_SLIDES}>
      <div className="text-center space-y-8">
        <p className="text-[9px] tracking-[0.4em] uppercase text-gold/60">Vision</p>
        <h2 className="text-lg tracking-wide font-light text-ice leading-8">
          Not just an AI that runs tasks —<br />
          an AI that <span className="text-gold">governs itself</span>, evolves its workforce,<br />
          and gets better over time.
        </h2>
        <div className="w-12 h-px bg-ice/20 mx-auto" />
        <p className="text-[10px] tracking-[0.3em] text-ice/30">
          智慧體 — Collective Intelligence Body
        </p>
      </div>
    </SlideShell>
  );
}

// ─── Page ─────────────────────────────────────────────────
export default function DeckPage() {
  return (
    <div className="bg-midnight min-h-screen snap-y snap-mandatory overflow-y-scroll">
      <TitleSlide />
      <ProblemSlide />
      <SolutionSlide />
      <HowSlide />
      <ArchSlide />
      <RealmsSlide />
      <IntegritySlide />
      <FinanceSlide />
      <DiplomacySlide />
      <TractionSlide />
      <VisionSlide />
      <StatusBar />
    </div>
  );
}
