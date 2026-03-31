import { useState, useEffect, useRef, useCallback } from "react";
import * as THREE from "three";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// ── Realm & Relationship Colors ─────────────────────────────────
const REALM_COLORS = {
  research: "#3b82f6",   // 研发界
  execution: "#f97316",  // 执行界
  central: "#a855f7",    // 中枢界
};

const REALM_LABELS = {
  research: "🔬 研发界 Research",
  execution: "⚡ 执行界 Execution",
  central: "🏛 中枢界 Central",
};

const CONN_COLORS = {
  transaction: "#22c55e",
  investment: "#3b82f6",
  bounty: "#eab308",
  employment: "#60a5fa",
  subsidy: "#a78bfa",
  bloodline: "#f472b6",
  host: "#14b8a6",
  competition: "#ef4444",
};

const ROLE_ICONS = {
  researcher: "🔬",
  analyst: "📊",
  coder: "💻",
  trader: "📈",
  judge: "⚖️",
  orchestrator: "🎯",
  custom: "🔧",
};

// ── 3D Agent Graph ──────────────────────────────────────────────
function ThreeGraph({ agents, connections, onSelect, selectedId }) {
  const mountRef = useRef(null);
  const nodesRef = useRef({});
  const frameRef = useRef(0);
  const mouseRef = useRef({ x: 0, y: 0, down: false, prevX: 0, prevY: 0 });
  const rotRef = useRef({ x: 0.3, y: 0 });
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseVec = useRef(new THREE.Vector2());

  useEffect(() => {
    const container = mountRef.current;
    if (!container || !agents.length) return;
    const w = container.clientWidth;
    const h = container.clientHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 1000);
    camera.position.z = 18;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0x404060, 0.6));
    const pl = new THREE.PointLight(0x6366f1, 1.5, 50);
    pl.position.set(5, 5, 10);
    scene.add(pl);
    const pl2 = new THREE.PointLight(0xf97316, 0.8, 40);
    pl2.position.set(-5, -3, 8);
    scene.add(pl2);

    const world = new THREE.Group();
    scene.add(world);

    // Position agents — realm determines radius ring
    const positions = {};
    const realmAngles = { central: 0, research: 0, execution: 0 };
    const realmCounts = {};
    agents.forEach(a => { realmCounts[a.realm] = (realmCounts[a.realm] || 0) + 1; });

    agents.forEach((a) => {
      const rc = realmCounts[a.realm] || 1;
      const angle = (realmAngles[a.realm] / rc) * Math.PI * 2;
      realmAngles[a.realm] = (realmAngles[a.realm] || 0) + 1;
      const r = a.realm === "central" ? 2 : a.realm === "research" ? 5 : 7;
      const y = (Math.random() - 0.5) * 4;
      positions[a.id] = new THREE.Vector3(
        Math.cos(angle) * r + (Math.random() - 0.5) * 1.5,
        y,
        Math.sin(angle) * r + (Math.random() - 0.5) * 1.5
      );
    });

    // Draw connections
    connections.forEach((c) => {
      const p1 = positions[c.from];
      const p2 = positions[c.to];
      if (!p1 || !p2) return;
      const geo = new THREE.BufferGeometry().setFromPoints([p1, p2]);
      const color = CONN_COLORS[c.type] || "#444";
      const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.2 });
      world.add(new THREE.Line(geo, mat));
    });

    // Draw agent nodes
    agents.forEach((a) => {
      const pos = positions[a.id];
      if (!pos) return;
      const maxBudget = Math.max(...agents.map(x => x.budget), 1);
      const size = 0.2 + (a.budget / maxBudget) * 0.5;
      const color = REALM_COLORS[a.realm] || "#888";

      // Glow
      const glowGeo = new THREE.SphereGeometry(size * 1.8, 16, 16);
      const glowMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: a.alive ? 0.08 : 0.02 });
      const glow = new THREE.Mesh(glowGeo, glowMat);
      glow.position.copy(pos);
      world.add(glow);

      // Core
      const geo = new THREE.SphereGeometry(size, 24, 24);
      const mat = new THREE.MeshStandardMaterial({
        color: a.alive ? color : "#333",
        emissive: a.alive ? color : "#111",
        emissiveIntensity: a.alive ? 0.4 : 0.1,
        metalness: 0.5,
        roughness: 0.3,
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
      const t = frameRef.current * 0.01;
      Object.entries(nodesRef.current).forEach(([id, n]) => {
        const offset = parseInt(id.replace(/\D/g, ""), 10) || 0;
        n.mesh.position.y = n.baseY + Math.sin(t + offset) * 0.15;
        n.glow.position.y = n.mesh.position.y;
        if (id === selectedId) {
          n.glow.scale.setScalar(1 + Math.sin(t * 3) * 0.3);
        }
      });
      world.rotation.x = rotRef.current.x;
      world.rotation.y = rotRef.current.y + t * 0.05;
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    };
    animate();

    const onMouseDown = (e) => { mouseRef.current = { ...mouseRef.current, down: true, prevX: e.clientX, prevY: e.clientY }; };
    const onMouseMove = (e) => {
      if (mouseRef.current.down) {
        rotRef.current.y += (e.clientX - mouseRef.current.prevX) * 0.005;
        rotRef.current.x = Math.max(-1.2, Math.min(1.2, rotRef.current.x + (e.clientY - mouseRef.current.prevY) * 0.005));
        mouseRef.current.prevX = e.clientX;
        mouseRef.current.prevY = e.clientY;
      }
    };
    const onMouseUp = () => { mouseRef.current.down = false; };
    const onClick = (e) => {
      const rect = container.getBoundingClientRect();
      mouseVec.current.x = ((e.clientX - rect.left) / w) * 2 - 1;
      mouseVec.current.y = -((e.clientY - rect.top) / h) * 2 + 1;
      raycasterRef.current.setFromCamera(mouseVec.current, camera);
      const hits = raycasterRef.current.intersectObjects(Object.values(nodesRef.current).map(n => n.mesh));
      if (hits.length > 0) onSelect(hits[0].object.userData.agentId);
    };

    container.addEventListener("mousedown", onMouseDown);
    container.addEventListener("mousemove", onMouseMove);
    container.addEventListener("mouseup", onMouseUp);
    container.addEventListener("click", onClick);

    return () => {
      running = false;
      container.removeEventListener("mousedown", onMouseDown);
      container.removeEventListener("mousemove", onMouseMove);
      container.removeEventListener("mouseup", onMouseUp);
      container.removeEventListener("click", onClick);
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

// ── System Card ─────────────────────────────────────────────────
function SystemCard({ icon, title, items }) {
  return (
    <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.4)" }}>
        {icon} {title}
      </div>
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
  const successRate = agent.tasks > 0 ? ((1 - (agent.failed || 0) / agent.tasks) * 100).toFixed(0) : "—";

  return (
    <div className="absolute top-4 right-4 w-80 rounded-xl p-5 z-20" style={{
      background: "rgba(10,10,20,0.95)", border: `1px solid ${color}40`, boxShadow: `0 0 30px ${color}15`,
    }}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="text-lg font-bold" style={{ color }}>
            {ROLE_ICONS[agent.role] || "🤖"} {agent.role}
          </div>
          <div className="text-xs font-mono" style={{ color: "rgba(255,255,255,0.4)" }}>{agent.id}</div>
        </div>
        <button onClick={onClose} className="text-white opacity-40 hover:opacity-100 text-lg">✕</button>
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
          <div className="w-full h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.1)" }}>
            <div className="h-full rounded-full" style={{
              width: `${agent.avg_score * 100}%`,
              background: agent.avg_score >= 0.8 ? "#22c55e" : agent.avg_score >= 0.5 ? "#eab308" : "#ef4444",
            }} />
          </div>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>Budget</span>
          <span className="text-yellow-400 font-mono font-bold">{agent.budget.toLocaleString()} ◆</span>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>Tasks</span>
          <span className="text-white">{agent.tasks}</span>
        </div>
      </div>
      {connections.length > 0 && (
        <div className="mt-4 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Connections</div>
          {connections.map((c, i) => {
            const otherId = c.from === agent.id ? c.to : c.from;
            const other = agents.find(a => a.id === otherId);
            return (
              <div key={i} className="flex items-center gap-2 text-xs py-0.5">
                <span className="w-2 h-2 rounded-full" style={{ background: CONN_COLORS[c.type] || "#666" }} />
                <span style={{ color: "rgba(255,255,255,0.5)" }}>{c.type}</span>
                <span className="text-white font-mono">{(other?.id || otherId).slice(0, 8)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────────
export default function ZhihuiTiDashboard() {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);

  // Fetch from zhihuiti API
  const fetchData = useCallback(() => {
    const apiUrl = window.__ZHIHUITI_API || "/api/data";
    fetch(apiUrl)
      .then(r => r.json())
      .then(d => { setData(d); setError(null); })
      .catch(e => setError(e.message));
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (error) return (
    <div className="min-h-screen flex items-center justify-center text-white" style={{ background: "#0a0a14" }}>
      <div className="text-center">
        <div className="text-4xl mb-4">智慧体</div>
        <div className="text-red-400">Cannot connect to zhihuiti API</div>
        <div className="text-xs text-gray-500 mt-2">Run: zhihuiti dashboard --port 8377</div>
        <button onClick={fetchData} className="mt-4 px-4 py-2 rounded bg-purple-600 text-white text-sm">Retry</button>
      </div>
    </div>
  );

  if (!data) return (
    <div className="min-h-screen flex items-center justify-center text-white" style={{ background: "#0a0a14" }}>
      <div className="text-purple-400 animate-pulse text-xl">Loading 智慧体...</div>
    </div>
  );

  const agents = data.agents || [];
  const relationships = data.relationships?.by_type ? Object.entries(data.relationships.by_type) : [];

  // Build connections from relationship data
  // The API doesn't expose individual edges, so we synthesize from agent realm proximity
  // In production, you'd add a /api/relationships endpoint
  const connections = [];
  for (let i = 0; i < agents.length; i++) {
    for (let j = i + 1; j < agents.length; j++) {
      if (agents[i].realm === agents[j].realm) {
        connections.push({ from: agents[i].id, to: agents[j].id, type: "transaction" });
      }
    }
  }

  const selectedAgent = agents.find(a => a.id === selected);
  const selectedConns = connections.filter(c => c.from === selected || c.to === selected);
  const handleSelect = useCallback(id => setSelected(prev => prev === id ? null : id), []);

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

  // Economy history (synthesize from current data for the chart)
  const econHistory = Array.from({ length: 20 }, (_, i) => ({
    day: i + 1,
    supply: (econ.money_supply || 10000) * (0.8 + Math.sin(i * 0.4) * 0.2),
    taxed: (econ.total_taxes_collected || 0) / 20 * (0.5 + Math.random()),
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
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {Object.entries(REALM_COLORS).map(([r, c]) => (
            <span key={r} className="px-2 py-1 rounded text-xs" style={{ background: `${c}15`, color: c, border: `1px solid ${c}30` }}>
              {REALM_LABELS[r]?.slice(0, 5)} · {agents.filter(a => a.realm === r).length}
            </span>
          ))}
        </div>
      </div>

      <div className="flex" style={{ height: "calc(100vh - 57px)" }}>
        {/* Left sidebar */}
        <div className="w-72 p-4 space-y-3 overflow-y-auto" style={{ borderRight: "1px solid rgba(255,255,255,0.05)" }}>
          <Stat label="Money Supply" value={`${(econ.money_supply || 0).toLocaleString()} ◆`} sub={`Treasury: ${(econ.treasury_balance || 0).toLocaleString()}`} color="#eab308" />
          <Stat label="Total Tasks" value={mem.total_tasks || 0} sub={`Avg score: ${(mem.avg_task_score || 0).toFixed(2)}`} color="#22c55e" />
          <Stat label="Gene Pool" value={mem.gene_pool_size || 0} sub={`Max gen: ${bl.max_generation || 0}`} color="#a855f7" />
          <Stat label="Auctions" value={au.total_auctions || 0} sub={`Savings: ${(au.total_savings || 0).toFixed(0)} ◆`} color="#3b82f6" />

          {/* Subsystem cards */}
          <SystemCard icon="🔍" title="Inspection" items={[
            ["Total", ins.total_inspections || 0],
            ["Accepted", ins.accepted || 0, "#22c55e"],
            ["Rejected", ins.rejected || 0, "#ef4444"],
          ]} />
          <SystemCard icon="🚨" title="Circuit Breaker" items={[
            ["Trips", cb.total_trips || 0, cb.total_trips > 0 ? "#ef4444" : "#22c55e"],
            ["Emergencies", cb.emergencies || 0, "#ef4444"],
            ["Laws Active", cb.laws_active || 0],
          ]} />
          <SystemCard icon="👁" title="Behavior" items={[
            ["Violations", bh.total_violations || 0, bh.total_violations > 0 ? "#ef4444" : "#22c55e"],
            ["Agents Flagged", bh.agents_flagged || 0],
          ]} />
          <SystemCard icon="💳" title="Lending" items={[
            ["Active Loans", ln.active || 0],
            ["Defaulted", ln.defaulted || 0, ln.defaulted > 0 ? "#ef4444" : "#fff"],
          ]} />
          <SystemCard icon="💱" title="Market" items={[
            ["Orders", mk.total_orders || 0],
            ["Trades", mk.total_trades || 0],
          ]} />
          <SystemCard icon="📈" title="Futures" items={[
            ["Active Stakes", ft.active || 0],
            ["Won", ft.won || 0, "#22c55e"],
            ["Lost", ft.lost || 0, "#ef4444"],
          ]} />
          <SystemCard icon="⚖️" title="Arbitration" items={[
            ["Disputes", ar.total_disputes || 0],
            ["Resolved", ar.resolved || 0, "#22c55e"],
          ]} />
          <SystemCard icon="🏭" title="Factory" items={[
            ["Shipped", fa.shipped || 0, "#22c55e"],
            ["QA Fail", fa.qa_fail || 0, "#ef4444"],
          ]} />
          <SystemCard icon="📨" title="Messaging" items={[
            ["Total Messages", msg.total_messages || 0],
            ["Unread", msg.unread || 0, msg.unread > 0 ? "#eab308" : "#fff"],
          ]} />
          <SystemCard icon="📚" title="Goal History" items={
            goals.slice(0, 3).map(g => [g.goal?.slice(0, 25) + "...", g.avg_score?.toFixed(2) || "—"])
          } />

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
            {agents.sort((a, b) => b.budget - a.budget).map(a => (
              <button key={a.id} onClick={() => handleSelect(a.id)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs text-left hover:bg-white hover:bg-opacity-5 transition-colors"
                style={{ background: selected === a.id ? "rgba(255,255,255,0.05)" : "transparent" }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{
                  background: a.alive ? REALM_COLORS[a.realm] : "#555",
                }} />
                <span className="flex-1 truncate text-white">{ROLE_ICONS[a.role] || "🤖"} {a.role}</span>
                <span className="font-mono" style={{ color: "rgba(255,255,255,0.3)" }}>{a.budget.toFixed(0)}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Center — 3D Graph */}
        <div className="flex-1 flex flex-col relative">
          <div className="flex-1 relative">
            <ThreeGraph agents={agents} connections={connections} onSelect={handleSelect} selectedId={selected} />
            <div className="absolute bottom-4 left-4 text-xs" style={{ color: "rgba(255,255,255,0.2)" }}>
              drag to rotate · click node for details
            </div>
            {selectedAgent && (
              <AgentDetail
                agent={selectedAgent}
                connections={selectedConns}
                agents={agents}
                onClose={() => setSelected(null)}
              />
            )}
          </div>

          {/* Bottom charts */}
          <div className="h-48 flex gap-4 px-4 pb-4" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            {/* Economy chart */}
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

            {/* Tax chart */}
            <div className="w-64 pt-3">
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

            {/* Leaderboard */}
            <div className="w-52 pt-3">
              <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Top Agents</div>
              <div className="space-y-1">
                {agents.filter(a => a.alive).sort((a, b) => b.avg_score - a.avg_score).slice(0, 6).map((a, i) => (
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
