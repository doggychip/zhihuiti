import { useState, useEffect, useRef, useCallback } from "react";
import * as THREE from "three";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// ── Realm & Relationship Colors ─────────────────────────────────
const REALM_COLORS = { research: "#3b82f6", execution: "#f97316", central: "#a855f7" };
const REALM_LABELS = {
  research: "🔬 研发界 Research",
  execution: "⚡ 执行界 Execution",
  central: "🏛 中枢界 Central",
};
const CONN_COLORS = {
  transaction: "#22c55e", investment: "#3b82f6", bounty: "#eab308",
  employment: "#60a5fa", subsidy: "#a78bfa", bloodline: "#f472b6",
  host: "#14b8a6", competition: "#ef4444",
};
const ROLE_ICONS = {
  researcher: "🔬", analyst: "📊", coder: "💻", trader: "📈",
  judge: "⚖️", orchestrator: "🎯", custom: "🔧",
};

// ── Demo data (used when API is unavailable) ────────────────────
const DEMO_DATA = {
  economy: { money_supply: 10000, total_minted: 10000, total_burned: 0, treasury_balance: 8969, total_taxes_collected: 23, total_rewards_paid: 154, total_spawn_costs: 900, transactions: 1, tax_rate: "15%" },
  memory: { total_tasks: 4, total_agents: 9, gene_pool_size: 2, avg_task_score: 0.833 },
  agents: [
    { id: "5a4be6b0a3ea", role: "researcher", budget: 133.7, avg_score: 0.85, alive: true, realm: "research", life_state: "active", generation: 0, tasks: 2 },
    { id: "e0dec0f20a49", role: "researcher", budget: 148.5, avg_score: 0.86, alive: true, realm: "research", life_state: "active", generation: 0, tasks: 2 },
    { id: "072cca2a612b", role: "researcher", budget: 85.0, avg_score: 0.5, alive: true, realm: "research", life_state: "active", generation: 1, tasks: 0 },
    { id: "a4fdafbed41c", role: "analyst", budget: 120.5, avg_score: 0.86, alive: true, realm: "research", life_state: "active", generation: 0, tasks: 1 },
    { id: "fe17430249d9", role: "analyst", budget: 134.5, avg_score: 0.86, alive: true, realm: "research", life_state: "active", generation: 0, tasks: 1 },
    { id: "35449823fa40", role: "custom", budget: 95.0, avg_score: 0.75, alive: true, realm: "execution", life_state: "active", generation: 0, tasks: 1 },
    { id: "6858f471ef49", role: "custom", budget: 128.2, avg_score: 0.75, alive: true, realm: "execution", life_state: "active", generation: 1, tasks: 1 },
    { id: "719d49a43ed7", role: "researcher", budget: 85.0, avg_score: 0.5, alive: true, realm: "research", life_state: "active", generation: 1, tasks: 0 },
    { id: "69ef96b5ed3e", role: "analyst", budget: 85.0, avg_score: 0.5, alive: true, realm: "research", life_state: "active", generation: 1, tasks: 0 },
  ],
  realms: {
    research: { budget_allocated: 2500, budget_remaining: 2200, agents_active: 6, agents_frozen: 0, agents_bankrupt: 0, tasks_completed: 3, tasks_failed: 0, avg_score: 0.86 },
    execution: { budget_allocated: 1750, budget_remaining: 1550, agents_active: 3, agents_frozen: 0, agents_bankrupt: 0, tasks_completed: 1, tasks_failed: 0, avg_score: 0.75 },
    central: { budget_allocated: 750, budget_remaining: 750, agents_active: 0, agents_frozen: 0, agents_bankrupt: 0, tasks_completed: 0, tasks_failed: 0, avg_score: 0 },
  },
  bloodline: { total_genes: 9, alive_genes: 9, max_generation: 1, avg_score: 0.7 },
  auctions: { total_auctions: 4, total_savings: 62.6, avg_savings: 15.65, avg_winning_bid: 13.9, avg_bids_per_auction: 3 },
  inspection: { total_inspections: 4, accepted: 4, rejected: 0, acceptance_rate: 1.0, avg_score: 0.833 },
  circuit_breaker: { total_trips: 0, emergencies: 0, halts: 0, warnings: 0, overridden: 0, laws_active: 4 },
  behavior: { total_violations: 0, agents_flagged: 0, total_penalties: 0, by_type: {} },
  relationships: { total_relationships: 0, agents_connected: 0, by_type: {} },
  loans: { total_loans: 0, active: 0, repaid: 0, defaulted: 0, total_principal: 0, total_repaid: 0 },
  market: { total_orders: 0, total_trades: 0, total_volume: 0 },
  futures: { total_stakes: 0, active: 0, won: 0, lost: 0, total_staked: 0 },
  arbitration: { total_disputes: 0, open: 0, resolved: 0, dismissed: 0 },
  factory: { total_orders: 0, shipped: 0, qa_fail: 0, in_progress: 0, total_revenue: 0 },
  messaging: { total_messages: 8, unread: 0 },
  goal_history: [
    { goal: "list 3 programming languages and their best use cases", task_count: 4, avg_score: 0.83 },
  ],
  transactions: {},
};

// ── 3D Agent Graph ──────────────────────────────────────────────
function ThreeGraph({ agents, connections, onSelect, selectedId }) {
  const mountRef = useRef(null);
  const nodesRef = useRef({});
  const frameRef = useRef(0);
  const mouseRef = useRef({ down: false, prevX: 0, prevY: 0 });
  const rotRef = useRef({ x: 0.3, y: 0 });
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseVec = useRef(new THREE.Vector2());

  useEffect(() => {
    const container = mountRef.current;
    if (!container || !agents.length) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    nodesRef.current = {};

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 1000);
    camera.position.z = 18;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0x404060, 0.6));
    const pl1 = new THREE.PointLight(0x6366f1, 1.5, 50); pl1.position.set(5, 5, 10); scene.add(pl1);
    const pl2 = new THREE.PointLight(0xf97316, 0.8, 40); pl2.position.set(-5, -3, 8); scene.add(pl2);
    const pl3 = new THREE.PointLight(0xa855f7, 0.6, 35); pl3.position.set(0, 8, -5); scene.add(pl3);

    const world = new THREE.Group();
    scene.add(world);

    // Realm ring particles (subtle orbital rings)
    [2.5, 5.5, 7.5].forEach((r, ri) => {
      const pts = [];
      for (let a = 0; a < Math.PI * 2; a += 0.05) {
        pts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
      }
      pts.push(pts[0].clone());
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const mat = new THREE.LineBasicMaterial({ color: Object.values(REALM_COLORS)[ri], transparent: true, opacity: 0.06 });
      world.add(new THREE.Line(geo, mat));
    });

    // Position agents by realm
    const realmIdx = { central: 0, research: 0, execution: 0 };
    const realmCounts = {};
    agents.forEach(a => { realmCounts[a.realm] = (realmCounts[a.realm] || 0) + 1; });

    const positions = {};
    agents.forEach((a) => {
      const rc = realmCounts[a.realm] || 1;
      const idx = realmIdx[a.realm] || 0;
      realmIdx[a.realm] = idx + 1;
      const angle = (idx / rc) * Math.PI * 2 + (a.realm === "research" ? 0.3 : a.realm === "execution" ? 1.2 : 2.5);
      const r = a.realm === "central" ? 2.5 : a.realm === "research" ? 5.5 : 7.5;
      const y = (Math.random() - 0.5) * 3;
      positions[a.id] = new THREE.Vector3(
        Math.cos(angle) * r + (Math.random() - 0.5),
        y,
        Math.sin(angle) * r + (Math.random() - 0.5)
      );
    });

    // Connections
    connections.forEach((c) => {
      const p1 = positions[c.from], p2 = positions[c.to];
      if (!p1 || !p2) return;
      const mid = p1.clone().lerp(p2, 0.5);
      mid.y += 0.5;
      const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
      const pts = curve.getPoints(20);
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const mat = new THREE.LineBasicMaterial({ color: CONN_COLORS[c.type] || "#444", transparent: true, opacity: 0.18 });
      world.add(new THREE.Line(geo, mat));
    });

    // Agent nodes
    const maxBudget = Math.max(...agents.map(x => x.budget), 1);
    agents.forEach((a) => {
      const pos = positions[a.id];
      if (!pos) return;
      const size = 0.18 + (a.budget / maxBudget) * 0.45;
      const color = REALM_COLORS[a.realm] || "#888";

      // Outer glow
      const glowGeo = new THREE.SphereGeometry(size * 2, 16, 16);
      const glowMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: a.alive ? 0.06 : 0.02 });
      const glow = new THREE.Mesh(glowGeo, glowMat);
      glow.position.copy(pos);
      world.add(glow);

      // Core sphere
      const geo = new THREE.SphereGeometry(size, 32, 32);
      const mat = new THREE.MeshStandardMaterial({
        color: a.alive ? color : "#333",
        emissive: a.alive ? color : "#111",
        emissiveIntensity: a.alive ? 0.5 : 0.1,
        metalness: 0.6, roughness: 0.2,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.copy(pos);
      mesh.userData = { agentId: a.id };
      world.add(mesh);
      nodesRef.current[a.id] = { mesh, glow, baseY: pos.y, size };
    });

    let running = true;
    const animate = () => {
      if (!running) return;
      frameRef.current++;
      const t = frameRef.current * 0.008;
      Object.entries(nodesRef.current).forEach(([id, n]) => {
        const off = parseInt(id.replace(/\D/g, ""), 10) || 0;
        n.mesh.position.y = n.baseY + Math.sin(t + off * 0.7) * 0.12;
        n.glow.position.y = n.mesh.position.y;
        if (id === selectedId) {
          n.glow.scale.setScalar(1 + Math.sin(t * 4) * 0.35);
          n.mesh.material.emissiveIntensity = 0.6 + Math.sin(t * 4) * 0.2;
        }
      });
      world.rotation.x = rotRef.current.x;
      world.rotation.y = rotRef.current.y + t * 0.03;
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    };
    animate();

    const onDown = (e) => { mouseRef.current = { down: true, prevX: e.clientX, prevY: e.clientY }; };
    const onMove = (e) => {
      if (!mouseRef.current.down) return;
      rotRef.current.y += (e.clientX - mouseRef.current.prevX) * 0.005;
      rotRef.current.x = Math.max(-1.2, Math.min(1.2, rotRef.current.x + (e.clientY - mouseRef.current.prevY) * 0.005));
      mouseRef.current.prevX = e.clientX;
      mouseRef.current.prevY = e.clientY;
    };
    const onUp = () => { mouseRef.current.down = false; };
    const onClick = (e) => {
      const rect = container.getBoundingClientRect();
      mouseVec.current.set(((e.clientX - rect.left) / w) * 2 - 1, -((e.clientY - rect.top) / h) * 2 + 1);
      raycasterRef.current.setFromCamera(mouseVec.current, camera);
      const hits = raycasterRef.current.intersectObjects(Object.values(nodesRef.current).map(n => n.mesh));
      if (hits.length) onSelect(hits[0].object.userData.agentId);
    };

    container.addEventListener("mousedown", onDown);
    container.addEventListener("mousemove", onMove);
    container.addEventListener("mouseup", onUp);
    container.addEventListener("click", onClick);

    const onResize = () => {
      const nw = container.clientWidth, nh = container.clientHeight;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener("resize", onResize);

    return () => {
      running = false;
      container.removeEventListener("mousedown", onDown);
      container.removeEventListener("mousemove", onMove);
      container.removeEventListener("mouseup", onUp);
      container.removeEventListener("click", onClick);
      window.removeEventListener("resize", onResize);
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, [agents, connections, selectedId, onSelect]);

  return <div ref={mountRef} style={{ width: "100%", height: "100%" }} />;
}

// ── Stat Card ───────────────────────────────────────────────────
function Stat({ label, value, sub, color = "#a78bfa" }) {
  return (
    <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="text-xs uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.4)" }}>{label}</div>
      <div className="text-2xl font-bold mt-1" style={{ color }}>{value}</div>
      {sub && <div className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.3)" }}>{sub}</div>}
    </div>
  );
}

function SystemCard({ icon, title, items }) {
  return (
    <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.4)" }}>{icon} {title}</div>
      {items.map(([label, value, color], i) => (
        <div key={i} className="flex justify-between text-xs py-0.5">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>{label}</span>
          <span className="font-mono" style={{ color: color || "#fff" }}>{value}</span>
        </div>
      ))}
    </div>
  );
}

// ── Agent Detail Panel ──────────────────────────────────────────
function AgentDetail({ agent, connections, agents, onClose }) {
  if (!agent) return null;
  const color = REALM_COLORS[agent.realm];
  return (
    <div className="absolute top-4 right-4 w-80 rounded-xl p-5 z-20" style={{
      background: "rgba(10,10,20,0.95)", border: `1px solid ${color}40`, boxShadow: `0 0 40px ${color}20`,
      backdropFilter: "blur(10px)",
    }}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="text-lg font-bold" style={{ color }}>{ROLE_ICONS[agent.role] || "🤖"} {agent.role}</div>
          <div className="text-xs font-mono" style={{ color: "rgba(255,255,255,0.4)" }}>{agent.id}</div>
        </div>
        <button onClick={onClose} className="text-white opacity-40 hover:opacity-100 text-lg cursor-pointer">✕</button>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>Realm</span>
          <span className="px-2 py-0.5 rounded text-xs" style={{ background: `${color}20`, color }}>{REALM_LABELS[agent.realm]}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>Generation</span>
          <span className="text-white">Gen {agent.generation}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>Status</span>
          <span style={{ color: agent.alive ? "#4ade80" : "#f87171" }}>
            {agent.alive ? "● active" : "● dead"} · {agent.life_state}
          </span>
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span style={{ color: "rgba(255,255,255,0.5)" }}>Score</span>
            <span className="text-white">{(agent.avg_score * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full h-2 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
            <div className="h-full rounded-full transition-all" style={{
              width: `${agent.avg_score * 100}%`,
              background: `linear-gradient(90deg, ${agent.avg_score >= 0.8 ? "#22c55e" : agent.avg_score >= 0.5 ? "#eab308" : "#ef4444"}, ${color})`,
            }} />
          </div>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>Budget</span>
          <span className="text-yellow-400 font-mono font-bold">{agent.budget.toFixed(0)} ◆</span>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>Tasks</span>
          <span className="text-white">{agent.tasks}</span>
        </div>
      </div>
      {connections.length > 0 && (
        <div className="mt-4 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Connections</div>
          {connections.slice(0, 8).map((c, i) => {
            const otherId = c.from === agent.id ? c.to : c.from;
            const other = agents.find(a => a.id === otherId);
            return (
              <div key={i} className="flex items-center gap-2 text-xs py-0.5">
                <span className="w-2 h-2 rounded-full" style={{ background: CONN_COLORS[c.type] || "#666" }} />
                <span style={{ color: "rgba(255,255,255,0.5)" }}>{c.type}</span>
                <span className="text-white font-mono">{other ? `${ROLE_ICONS[other.role] || ""} ${other.role}` : otherId.slice(0, 8)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Theory Collision Panel ───────────────────────────────────────
const THEORY_OPTIONS = [
  { value: "darwinian", label: "🧬 Darwinian Selection", desc: "Survival of the fittest agents" },
  { value: "mutualist", label: "🤝 Symbiotic Mutualism", desc: "Cooperation amplifies both" },
  { value: "hybrid", label: "⚡ Hybrid Equilibrium", desc: "Competition + cooperation" },
  { value: "elitist", label: "👑 Elite Meritocracy", desc: "Only the top performers survive" },
];

function CollisionPanel({ onResult, live }) {
  const [theoryA, setTheoryA] = useState("darwinian");
  const [theoryB, setTheoryB] = useState("mutualist");
  const [goal, setGoal] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [open, setOpen] = useState(false);

  const handleCollide = async () => {
    if (!goal.trim() || !live) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await fetch("/api/collide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: goal.trim(), theory_a: theoryA, theory_b: theoryB }),
      });
      const data = await res.json();
      setResult(data);
      if (onResult) onResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setRunning(false);
  };

  const optA = THEORY_OPTIONS.find(t => t.value === theoryA);
  const optB = THEORY_OPTIONS.find(t => t.value === theoryB);

  return (
    <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(168,85,247,0.2)" }}>
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between text-xs uppercase tracking-wider cursor-pointer"
        style={{ color: "#a855f7" }}>
        <span>💥 Theory Collision Engine</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          {/* Goal input */}
          <input
            type="text"
            value={goal}
            onChange={e => setGoal(e.target.value)}
            placeholder="Enter a goal to test..."
            className="w-full px-3 py-2 rounded text-sm text-white placeholder-gray-500 outline-none"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}
          />

          {/* Theory selectors */}
          <div className="flex gap-2">
            <div className="flex-1">
              <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "#f472b6" }}>Theory A</div>
              <select value={theoryA} onChange={e => setTheoryA(e.target.value)}
                className="w-full px-2 py-1.5 rounded text-xs text-white cursor-pointer outline-none"
                style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.1)" }}>
                {THEORY_OPTIONS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
              <div className="text-[10px] mt-1" style={{ color: "rgba(255,255,255,0.3)" }}>{optA?.desc}</div>
            </div>
            <div className="flex-1">
              <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "#60a5fa" }}>Theory B</div>
              <select value={theoryB} onChange={e => setTheoryB(e.target.value)}
                className="w-full px-2 py-1.5 rounded text-xs text-white cursor-pointer outline-none"
                style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.1)" }}>
                {THEORY_OPTIONS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
              <div className="text-[10px] mt-1" style={{ color: "rgba(255,255,255,0.3)" }}>{optB?.desc}</div>
            </div>
          </div>

          {/* Collide button */}
          <button onClick={handleCollide} disabled={running || !goal.trim() || !live}
            className="w-full py-2.5 rounded-lg text-sm font-bold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            style={{
              background: running ? "rgba(168,85,247,0.3)" : "linear-gradient(135deg, #ec4899, #a855f7)",
              color: "#fff",
            }}>
            {running ? "⏳ Colliding..." : "💥 COLLIDE THEORIES"}
          </button>
          {!live && <div className="text-[10px] text-center text-yellow-500">Connect to zhihuiti API to enable</div>}

          {/* Result */}
          {result && !result.error && (
            <div className="p-3 rounded-lg space-y-2" style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.06)" }}>
              <div className="text-xs font-bold" style={{ color: "#a855f7" }}>Collision Result</div>
              <div className="flex justify-between text-xs">
                <span style={{ color: "#f472b6" }}>{optA?.label}</span>
                <span className="font-mono font-bold" style={{ color: result.score_a >= result.score_b ? "#22c55e" : "rgba(255,255,255,0.4)" }}>
                  {result.score_a?.toFixed(3)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span style={{ color: "#60a5fa" }}>{optB?.label}</span>
                <span className="font-mono font-bold" style={{ color: result.score_b >= result.score_a ? "#22c55e" : "rgba(255,255,255,0.4)" }}>
                  {result.score_b?.toFixed(3)}
                </span>
              </div>
              {/* Score bars */}
              <div className="flex gap-1 h-4 rounded overflow-hidden" style={{ background: "rgba(255,255,255,0.05)" }}>
                <div style={{
                  width: `${(result.score_a / (result.score_a + result.score_b) * 100) || 50}%`,
                  background: "linear-gradient(90deg, #ec4899, #a855f7)",
                  borderRadius: "4px 0 0 4px",
                }} />
                <div style={{
                  width: `${(result.score_b / (result.score_a + result.score_b) * 100) || 50}%`,
                  background: "linear-gradient(90deg, #3b82f6, #60a5fa)",
                  borderRadius: "0 4px 4px 0",
                }} />
              </div>
              <div className="text-center text-xs font-bold" style={{
                color: result.winner === "tie" ? "#eab308" : "#22c55e",
              }}>
                {result.winner === "tie" ? "TIE" : `Winner: ${THEORY_OPTIONS.find(t => t.value === result.winner)?.label || result.winner}`}
              </div>
            </div>
          )}
          {result?.error && (
            <div className="text-xs text-red-400 text-center">{result.error}</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────────
export default function ZhihuiTiDashboard() {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);
  const [live, setLive] = useState(true);
  const handleSelect = useCallback(id => setSelected(prev => prev === id ? null : id), []);

  const fetchData = useCallback(() => {
    fetch("/api/data")
      .then(r => r.json())
      .then(d => { setData(d); setLive(true); })
      .catch(() => { setData(DEMO_DATA); setLive(false); });
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (!data) return (
    <div className="min-h-screen flex items-center justify-center text-white" style={{ background: "#0a0a14" }}>
      <div className="text-purple-400 animate-pulse text-xl">Loading 智慧体...</div>
    </div>
  );

  const agents = data.agents || [];
  const connections = [];
  for (let i = 0; i < agents.length; i++) {
    for (let j = i + 1; j < agents.length; j++) {
      if (agents[i].realm === agents[j].realm) {
        const types = ["transaction", "bloodline", "competition", "investment"];
        connections.push({ from: agents[i].id, to: agents[j].id, type: types[(i + j) % types.length] });
      }
    }
  }

  const selectedAgent = agents.find(a => a.id === selected);
  const selectedConns = connections.filter(c => c.from === selected || c.to === selected);

  const econ = data.economy || {};
  const mem = data.memory || {};
  const ins = data.inspection || {};
  const cb = data.circuit_breaker || {};
  const bh = data.behavior || {};
  const au = data.auctions || {};
  const ln = data.loans || {};
  const mk = data.market || {};
  const ft = data.futures || {};
  const ar = data.arbitration || {};
  const fa = data.factory || {};
  const msg = data.messaging || {};
  const goals = data.goal_history || [];
  const bl = data.bloodline || {};

  const econHistory = Array.from({ length: 20 }, (_, i) => ({
    day: i + 1,
    supply: (econ.money_supply || 10000) * (0.85 + Math.sin(i * 0.4) * 0.15 + i * 0.005),
    taxed: (econ.total_taxes_collected || 10) / 15 * (0.6 + Math.random() * 0.8),
  }));

  return (
    <div className="min-h-screen text-white" style={{
      background: "linear-gradient(135deg, #0a0a14 0%, #0d0d1a 50%, #0a0f18 100%)",
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center text-xl font-bold"
            style={{ background: "linear-gradient(135deg, #6366f1, #a855f7)" }}>慧</div>
          <div>
            <div className="text-sm font-bold tracking-wide">智慧体 ZHIHUITI</div>
            <div className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
              Autonomous Multi-Agent Ecosystem · {agents.length} agents
              {!live && <span className="ml-2 text-yellow-500">(demo mode)</span>}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {Object.entries(REALM_COLORS).map(([r, c]) => (
            <span key={r} className="px-2 py-1 rounded text-xs" style={{ background: `${c}15`, color: c, border: `1px solid ${c}30` }}>
              {REALM_LABELS[r]?.split(" ")[0]} · {agents.filter(a => a.realm === r).length}
            </span>
          ))}
        </div>
      </div>

      <div className="flex" style={{ height: "calc(100vh - 57px)" }}>
        {/* Left sidebar */}
        <div className="w-72 p-4 space-y-3 overflow-y-auto" style={{ borderRight: "1px solid rgba(255,255,255,0.05)" }}>
          <Stat label="Money Supply" value={`${(econ.money_supply || 0).toLocaleString()} ◆`} sub={`Treasury: ${(econ.treasury_balance || 0).toLocaleString()}`} color="#eab308" />
          <Stat label="Tasks Completed" value={mem.total_tasks || 0} sub={`Avg score: ${(mem.avg_task_score || 0).toFixed(2)}`} color="#22c55e" />
          <Stat label="Gene Pool" value={mem.gene_pool_size || 0} sub={`${bl.alive_genes || 0} alive · Gen ${bl.max_generation || 0}`} color="#a855f7" />
          <Stat label="Auctions Won" value={au.total_auctions || 0} sub={`Saved ${(au.total_savings || 0).toFixed(0)} ◆`} color="#3b82f6" />

          {/* Theory Collision Engine */}
          <CollisionPanel onResult={() => fetchData()} live={live} />

          <SystemCard icon="🔍" title="3-Layer Inspection" items={[
            ["Inspections", ins.total_inspections || 0],
            ["Accepted", ins.accepted || 0, "#22c55e"],
            ["Rejected", ins.rejected || 0, "#ef4444"],
            ["Avg Score", (ins.avg_score || 0).toFixed(2)],
          ]} />
          <SystemCard icon="🚨" title="Circuit Breaker" items={[
            ["Trips", cb.total_trips || 0, cb.total_trips > 0 ? "#ef4444" : "#22c55e"],
            ["Laws Active", cb.laws_active || 0],
          ]} />
          <SystemCard icon="👁" title="Behavioral Detection" items={[
            ["Violations", bh.total_violations || 0, bh.total_violations > 0 ? "#ef4444" : "#22c55e"],
            ["Agents Flagged", bh.agents_flagged || 0],
          ]} />
          <SystemCard icon="💳" title="Lending" items={[
            ["Active", ln.active || 0],
            ["Defaulted", ln.defaulted || 0, ln.defaulted > 0 ? "#ef4444" : "#fff"],
          ]} />
          <SystemCard icon="💱" title="Market / Futures" items={[
            ["Orders", mk.total_orders || 0],
            ["Trades", mk.total_trades || 0],
            ["Stakes", ft.active || 0],
          ]} />
          <SystemCard icon="⚖️" title="Arbitration" items={[
            ["Disputes", ar.total_disputes || 0],
            ["Resolved", ar.resolved || 0, "#22c55e"],
          ]} />
          <SystemCard icon="🏭" title="Factory" items={[
            ["Shipped", fa.shipped || 0, "#22c55e"],
            ["QA Fail", fa.qa_fail || 0, fa.qa_fail > 0 ? "#ef4444" : "#fff"],
          ]} />
          <SystemCard icon="📨" title="Agent Messaging" items={[
            ["Messages", msg.total_messages || 0],
            ["Unread", msg.unread || 0, msg.unread > 0 ? "#eab308" : "#fff"],
          ]} />

          {goals.length > 0 && (
            <SystemCard icon="📚" title="Goal History" items={
              goals.slice(0, 4).map(g => [
                (g.goal || "").slice(0, 22) + (g.goal?.length > 22 ? "..." : ""),
                (g.avg_score || 0).toFixed(2),
                g.avg_score >= 0.8 ? "#22c55e" : "#eab308",
              ])
            } />
          )}

          {/* Connection legend */}
          <div className="pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Relationship Types</div>
            {Object.entries(CONN_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-2 text-xs py-0.5">
                <span className="w-3 h-0.5 rounded" style={{ background: color }} />
                <span style={{ color: "rgba(255,255,255,0.5)" }}>{type}</span>
              </div>
            ))}
          </div>

          {/* Agent list */}
          <div className="pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Agents</div>
            {[...agents].sort((a, b) => b.budget - a.budget).map(a => (
              <button key={a.id} onClick={() => handleSelect(a.id)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs text-left hover:bg-white/5 transition-colors cursor-pointer"
                style={{ background: selected === a.id ? "rgba(255,255,255,0.08)" : "transparent" }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: a.alive ? REALM_COLORS[a.realm] : "#555" }} />
                <span className="flex-1 truncate text-white">{ROLE_ICONS[a.role] || "🤖"} {a.role}</span>
                <span className="font-mono text-[10px]" style={{ color: "rgba(255,255,255,0.3)" }}>{a.budget.toFixed(0)}◆</span>
              </button>
            ))}
          </div>
        </div>

        {/* Center — 3D Graph */}
        <div className="flex-1 flex flex-col relative">
          <div className="flex-1 relative">
            <ThreeGraph agents={agents} connections={connections} onSelect={handleSelect} selectedId={selected} />
            <div className="absolute bottom-4 left-4 text-xs" style={{ color: "rgba(255,255,255,0.15)" }}>
              drag to rotate · click node for details
            </div>
            {selectedAgent && (
              <AgentDetail agent={selectedAgent} connections={selectedConns} agents={agents} onClose={() => setSelected(null)} />
            )}
          </div>

          {/* Bottom charts */}
          <div className="h-44 flex gap-4 px-4 pb-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            <div className="flex-1 pt-3">
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: "rgba(255,255,255,0.3)" }}>Token Economy</div>
              <ResponsiveContainer width="100%" height="85%">
                <AreaChart data={econHistory}>
                  <defs>
                    <linearGradient id="supplyGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#a855f7" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#a855f7" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" hide />
                  <YAxis hide />
                  <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8, fontSize: 11 }} />
                  <Area type="monotone" dataKey="supply" stroke="#a855f7" fill="url(#supplyGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="w-60 pt-3">
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: "rgba(255,255,255,0.3)" }}>Tax Revenue</div>
              <ResponsiveContainer width="100%" height="85%">
                <BarChart data={econHistory.slice(-10)}>
                  <XAxis dataKey="day" hide />
                  <YAxis hide />
                  <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8, fontSize: 11 }} />
                  <Bar dataKey="taxed" fill="#eab30850" stroke="#eab308" strokeWidth={1} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="w-52 pt-3">
              <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Top Agents</div>
              <div className="space-y-1">
                {[...agents].filter(a => a.alive).sort((a, b) => b.avg_score - a.avg_score).slice(0, 6).map((a, i) => (
                  <div key={a.id} className="flex items-center gap-2 text-xs">
                    <span className="w-4 text-right font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>{i + 1}</span>
                    <span className="w-2 h-2 rounded-full" style={{ background: REALM_COLORS[a.realm] }} />
                    <span className="flex-1 text-white truncate">{a.role}</span>
                    <span className="font-mono" style={{ color: a.avg_score >= 0.8 ? "#22c55e" : "#eab308" }}>
                      {a.avg_score.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
