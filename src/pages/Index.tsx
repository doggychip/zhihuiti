import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import * as THREE from "three";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// ── Realm & Relationship Colors ─────────────────────────────────
const REALM_COLORS: Record<string, string> = { research: "#3b82f6", execution: "#f97316", central: "#a855f7" };
const REALM_LABELS: Record<string, string> = {
  research: "🔬 研发界 Research",
  execution: "⚡ 执行界 Execution",
  central: "🏛 中枢界 Central",
};
const CONN_COLORS: Record<string, string> = {
  transaction: "#22c55e", investment: "#3b82f6", bounty: "#eab308",
  employment: "#60a5fa", subsidy: "#a78bfa", bloodline: "#f472b6",
  host: "#14b8a6", competition: "#ef4444",
};
const ROLE_ICONS: Record<string, string> = {
  researcher: "🔬", analyst: "📊", coder: "💻", trader: "📈",
  judge: "⚖️", orchestrator: "🎯", custom: "🔧",
};

// ── Types ───────────────────────────────────────────────────────
interface Agent {
  id: string;
  role: string;
  budget: number;
  avg_score: number;
  alive: boolean;
  realm: string;
  life_state: string;
  generation: number;
  tasks: number;
  parentId?: string;
}

interface Connection {
  from: string;
  to: string;
  type: string;
}

interface TaskEvent {
  id: string;
  type: "bid" | "assigned" | "completed" | "transfer" | "bankrupt";
  agentId: string;
  agentRole: string;
  realm: string;
  detail: string;
  amount?: number;
  targetAgentId?: string;
  timestamp: number;
}

// ── Demo data ───────────────────────────────────────────────────
const DEMO_DATA = {
  economy: { money_supply: 10000, total_minted: 10000, total_burned: 0, treasury_balance: 8969, total_taxes_collected: 23, total_rewards_paid: 154, total_spawn_costs: 900, transactions: 1, tax_rate: "15%" },
  memory: { total_tasks: 4, total_agents: 9, gene_pool_size: 2, avg_task_score: 0.833 },
  agents: [
    { id: "5a4be6b0a3ea", role: "researcher", budget: 133.7, avg_score: 0.85, alive: true, realm: "research", life_state: "active", generation: 0, tasks: 2 },
    { id: "e0dec0f20a49", role: "researcher", budget: 148.5, avg_score: 0.86, alive: true, realm: "research", life_state: "active", generation: 0, tasks: 2 },
    { id: "072cca2a612b", role: "researcher", budget: 85.0, avg_score: 0.5, alive: true, realm: "research", life_state: "active", generation: 1, tasks: 0, parentId: "5a4be6b0a3ea" },
    { id: "a4fdafbed41c", role: "analyst", budget: 120.5, avg_score: 0.86, alive: true, realm: "research", life_state: "active", generation: 0, tasks: 1 },
    { id: "fe17430249d9", role: "analyst", budget: 134.5, avg_score: 0.86, alive: true, realm: "research", life_state: "active", generation: 0, tasks: 1 },
    { id: "35449823fa40", role: "custom", budget: 95.0, avg_score: 0.75, alive: true, realm: "execution", life_state: "active", generation: 0, tasks: 1 },
    { id: "6858f471ef49", role: "custom", budget: 128.2, avg_score: 0.75, alive: true, realm: "execution", life_state: "active", generation: 1, tasks: 1, parentId: "35449823fa40" },
    { id: "719d49a43ed7", role: "researcher", budget: 85.0, avg_score: 0.5, alive: true, realm: "research", life_state: "active", generation: 1, tasks: 0, parentId: "e0dec0f20a49" },
    { id: "69ef96b5ed3e", role: "analyst", budget: 85.0, avg_score: 0.5, alive: true, realm: "research", life_state: "active", generation: 1, tasks: 0, parentId: "a4fdafbed41c" },
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

const EVENT_ICONS: Record<string, string> = {
  bid: "🏷️", assigned: "📋", completed: "✅", transfer: "💸", bankrupt: "💀",
};
const EVENT_COLORS: Record<string, string> = {
  bid: "#eab308", assigned: "#60a5fa", completed: "#22c55e", transfer: "#a78bfa", bankrupt: "#ef4444",
};

// ── Simulated live task feed generator ──────────────────────────
function useSimulatedFeed(agents: Agent[]): TaskEvent[] {
  const [events, setEvents] = useState<TaskEvent[]>([]);

  useEffect(() => {
    if (!agents.length) return;
    const taskGoals = [
      "Analyze market trends", "Compile research report", "Optimize token flow",
      "Validate auction results", "Benchmark agent scores", "Review inspection data",
      "Process bloodline merge", "Execute trade order", "Audit tax records",
      "Train sub-model", "Rank candidate genes", "Assess risk factors",
    ];
    const genEvent = (): TaskEvent => {
      const types: TaskEvent["type"][] = ["bid", "assigned", "completed", "transfer", "bankrupt"];
      const weights = [30, 25, 25, 18, 2]; // bankrupt is rare
      let r = Math.random() * 100;
      let type: TaskEvent["type"] = "bid";
      for (let i = 0; i < types.length; i++) {
        r -= weights[i];
        if (r <= 0) { type = types[i]; break; }
      }
      const agent = agents[Math.floor(Math.random() * agents.length)];
      const goal = taskGoals[Math.floor(Math.random() * taskGoals.length)];
      let detail = "";
      let targetAgentId: string | undefined;
      let amount: number | undefined;
      switch (type) {
        case "bid":
          amount = Math.round(8 + Math.random() * 30);
          detail = `Bidding ${amount} ◆ on "${goal}"`;
          break;
        case "assigned":
          detail = `Assigned to "${goal}"`;
          break;
        case "completed": {
          const score = (0.5 + Math.random() * 0.5).toFixed(2);
          amount = Math.round(10 + Math.random() * 40);
          detail = `Completed "${goal}" — score ${score}, earned ${amount} ◆`;
          break;
        }
        case "transfer": {
          const target = agents.filter(a => a.id !== agent.id)[Math.floor(Math.random() * (agents.length - 1))];
          targetAgentId = target?.id;
          amount = Math.round(5 + Math.random() * 25);
          detail = `Transferred ${amount} ◆ to ${ROLE_ICONS[target?.role || ""] || "🤖"} ${target?.role || "agent"}`;
          break;
        }
        case "bankrupt":
          detail = `Budget depleted — agent going bankrupt!`;
          break;
      }
      return {
        id: Math.random().toString(36).slice(2, 10),
        type, agentId: agent.id, agentRole: agent.role,
        realm: agent.realm, detail, amount, targetAgentId,
        timestamp: Date.now(),
      };
    };

    // Seed initial events
    const initial: TaskEvent[] = [];
    for (let i = 0; i < 6; i++) initial.push({ ...genEvent(), timestamp: Date.now() - (6 - i) * 3000 });
    setEvents(initial);

    const interval = setInterval(() => {
      setEvents(prev => [genEvent(), ...prev].slice(0, 50));
    }, 2500 + Math.random() * 2000);
    return () => clearInterval(interval);
  }, [agents]);

  return events;
}

// ── 3D Effect types ─────────────────────────────────────────────
interface RippleEffect {
  agentId: string;
  startTime: number;
  ring: THREE.Mesh;
}

interface ParticleTrail {
  fromId: string;
  toId: string;
  startTime: number;
  particles: THREE.Points;
  curve: THREE.QuadraticBezierCurve3;
}

interface BankruptEffect {
  agentId: string;
  startTime: number;
  particles: THREE.Points;
  flash: THREE.PointLight;
}

// ── 3D Agent Graph (with effects) ───────────────────────────────
function ThreeGraph({ agents, connections, onSelect, selectedId, events }: {
  agents: Agent[];
  connections: Connection[];
  onSelect: (id: string) => void;
  selectedId: string | null;
  events: TaskEvent[];
}) {
  const mountRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<Record<string, { mesh: THREE.Mesh; glow: THREE.Mesh; baseY: number; size: number }>>({});
  const frameRef = useRef(0);
  const mouseRef = useRef({ down: false, prevX: 0, prevY: 0 });
  const rotRef = useRef({ x: 0.3, y: 0 });
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseVec = useRef(new THREE.Vector2());
  const worldRef = useRef<THREE.Group | null>(null);
  const ripplesRef = useRef<RippleEffect[]>([]);
  const trailsRef = useRef<ParticleTrail[]>([]);
  const bankruptRef = useRef<BankruptEffect[]>([]);
  const processedEventsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const container = mountRef.current;
    if (!container || !agents.length) return;

    const w = container.clientWidth;
    const h = container.clientHeight;
    nodesRef.current = {};
    ripplesRef.current = [];
    trailsRef.current = [];
    bankruptRef.current = [];
    processedEventsRef.current = new Set();

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
    worldRef.current = world;
    scene.add(world);

    // Realm rings
    const realmRadii = [2.5, 5.5, 7.5];
    const realmKeys = ["central", "research", "execution"];
    const realmChineseLabels: Record<string, string> = { central: "中枢界", research: "研发界", execution: "执行界" };
    realmRadii.forEach((r, ri) => {
      const pts: THREE.Vector3[] = [];
      for (let a = 0; a < Math.PI * 2; a += 0.05) {
        pts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
      }
      pts.push(pts[0].clone());
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const mat = new THREE.LineBasicMaterial({ color: Object.values(REALM_COLORS)[ri], transparent: true, opacity: 0.06 });
      world.add(new THREE.Line(geo, mat));

      // Floating Chinese label sprite
      const canvas = document.createElement("canvas");
      canvas.width = 256; canvas.height = 64;
      const ctx = canvas.getContext("2d")!;
      ctx.clearRect(0, 0, 256, 64);
      ctx.font = "bold 32px 'Inter', system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const realmColor = Object.values(REALM_COLORS)[ri];
      ctx.shadowColor = realmColor;
      ctx.shadowBlur = 12;
      ctx.fillStyle = realmColor;
      ctx.fillText(realmChineseLabels[realmKeys[ri]], 128, 32);
      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;
      const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 0.4, depthWrite: false });
      const sprite = new THREE.Sprite(spriteMat);
      const labelAngle = ri * (Math.PI * 2 / 3) + 0.5;
      sprite.position.set(Math.cos(labelAngle) * (r + 0.8), 2.2, Math.sin(labelAngle) * (r + 0.8));
      sprite.scale.set(3, 0.75, 1);
      world.add(sprite);
    });

    // Ambient particle dust
    const dustCount = 200;
    const dustPosArr = new Float32Array(dustCount * 3);
    const dustVelArr = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount; i++) {
      dustPosArr[i * 3] = (Math.random() - 0.5) * 24;
      dustPosArr[i * 3 + 1] = (Math.random() - 0.5) * 12;
      dustPosArr[i * 3 + 2] = (Math.random() - 0.5) * 24;
      dustVelArr[i * 3] = (Math.random() - 0.5) * 0.003;
      dustVelArr[i * 3 + 1] = (Math.random() - 0.5) * 0.002;
      dustVelArr[i * 3 + 2] = (Math.random() - 0.5) * 0.003;
    }
    const dustGeo = new THREE.BufferGeometry();
    dustGeo.setAttribute("position", new THREE.BufferAttribute(dustPosArr, 3));
    const dustMat = new THREE.PointsMaterial({
      color: "#6366f1", size: 0.04, transparent: true, opacity: 0.35,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const dustPoints = new THREE.Points(dustGeo, dustMat);
    world.add(dustPoints);

    // Position agents
    const realmIdx: Record<string, number> = { central: 0, research: 0, execution: 0 };
    const realmCounts: Record<string, number> = {};
    agents.forEach(a => { realmCounts[a.realm] = (realmCounts[a.realm] || 0) + 1; });

    const positions: Record<string, THREE.Vector3> = {};
    agents.forEach((a) => {
      const rc = realmCounts[a.realm] || 1;
      const idx = realmIdx[a.realm] || 0;
      realmIdx[a.realm] = idx + 1;
      const angle = (idx / rc) * Math.PI * 2 + (a.realm === "research" ? 0.3 : a.realm === "execution" ? 1.2 : 2.5);
      const r = a.realm === "central" ? 2.5 : a.realm === "research" ? 5.5 : 7.5;
      const y = (Math.random() - 0.5) * 3;
      positions[a.id] = new THREE.Vector3(
        Math.cos(angle) * r + (Math.random() - 0.5), y,
        Math.sin(angle) * r + (Math.random() - 0.5)
      );
    });

    // Connection lines
    connections.forEach((c) => {
      const p1 = positions[c.from], p2 = positions[c.to];
      if (!p1 || !p2) return;
      const mid = p1.clone().lerp(p2, 0.5); mid.y += 0.5;
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

      const glowGeo = new THREE.SphereGeometry(size * 2, 16, 16);
      const glowMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: a.alive ? 0.06 : 0.02 });
      const glow = new THREE.Mesh(glowGeo, glowMat);
      glow.position.copy(pos); world.add(glow);

      const geo = new THREE.SphereGeometry(size, 32, 32);
      const mat = new THREE.MeshStandardMaterial({
        color: a.alive ? color : "#333", emissive: a.alive ? color : "#111",
        emissiveIntensity: a.alive ? 0.5 : 0.1, metalness: 0.6, roughness: 0.2,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.copy(pos); mesh.userData = { agentId: a.id };
      world.add(mesh);

      nodesRef.current[a.id] = { mesh, glow, baseY: pos.y, size };
    });

    // ── Helper: spawn ripple ring ───────────────────────────────
    const spawnRipple = (agentId: string) => {
      const node = nodesRef.current[agentId];
      if (!node) return;
      const color = new THREE.Color(REALM_COLORS[agents.find(a => a.id === agentId)?.realm || "research"] || "#3b82f6");
      const ringGeo = new THREE.RingGeometry(0.01, 0.08, 32);
      const ringMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8, side: THREE.DoubleSide });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(node.mesh.position);
      ring.lookAt(camera.position);
      world.add(ring);
      ripplesRef.current.push({ agentId, startTime: performance.now(), ring });
    };

    // ── Helper: spawn particle trail ────────────────────────────
    const spawnTrail = (fromId: string, toId: string) => {
      const fromNode = nodesRef.current[fromId];
      const toNode = nodesRef.current[toId];
      if (!fromNode || !toNode) return;
      const p1 = fromNode.mesh.position.clone();
      const p2 = toNode.mesh.position.clone();
      const mid = p1.clone().lerp(p2, 0.5); mid.y += 1.5;
      const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);

      const count = 20;
      const posArr = new Float32Array(count * 3);
      const alphaArr = new Float32Array(count);
      for (let i = 0; i < count; i++) { alphaArr[i] = 1 - i / count; }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(posArr, 3));

      const mat = new THREE.PointsMaterial({
        color: "#a78bfa", size: 0.12, transparent: true, opacity: 0.9,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      const particles = new THREE.Points(geo, mat);
      world.add(particles);
      trailsRef.current.push({ fromId, toId, startTime: performance.now(), particles, curve });
    };

    // ── Helper: spawn bankruptcy explosion ──────────────────────
    const spawnBankruptcy = (agentId: string) => {
      const node = nodesRef.current[agentId];
      if (!node) return;
      const count = 40;
      const posArr = new Float32Array(count * 3);
      const velArr = new Float32Array(count * 3);
      for (let i = 0; i < count; i++) {
        posArr[i * 3] = node.mesh.position.x;
        posArr[i * 3 + 1] = node.mesh.position.y;
        posArr[i * 3 + 2] = node.mesh.position.z;
        velArr[i * 3] = (Math.random() - 0.5) * 0.15;
        velArr[i * 3 + 1] = (Math.random() - 0.5) * 0.15;
        velArr[i * 3 + 2] = (Math.random() - 0.5) * 0.15;
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(posArr, 3));
      geo.setAttribute("velocity", new THREE.BufferAttribute(velArr, 3));
      const mat = new THREE.PointsMaterial({
        color: "#ef4444", size: 0.15, transparent: true, opacity: 1,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      const particles = new THREE.Points(geo, mat);
      world.add(particles);

      const flash = new THREE.PointLight(0xef4444, 3, 8);
      flash.position.copy(node.mesh.position);
      world.add(flash);

      bankruptRef.current.push({ agentId, startTime: performance.now(), particles, flash });

      // Fade out the node
      (node.mesh.material as THREE.MeshStandardMaterial).color.set("#1a0000");
      (node.mesh.material as THREE.MeshStandardMaterial).emissive.set("#330000");
      (node.glow.material as THREE.MeshBasicMaterial).opacity = 0.01;
    };

    // Expose helpers via ref-accessible closure
    (container as any).__spawnRipple = spawnRipple;
    (container as any).__spawnTrail = spawnTrail;
    (container as any).__spawnBankruptcy = spawnBankruptcy;

    let running = true;
    const animate = () => {
      if (!running) return;
      frameRef.current++;
      const t = frameRef.current * 0.008;
      const now = performance.now();

      // Animate dust
      const dustPos = dustGeo.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < dustCount; i++) {
        let x = dustPos.getX(i) + dustVelArr[i * 3];
        let y = dustPos.getY(i) + dustVelArr[i * 3 + 1];
        let z = dustPos.getZ(i) + dustVelArr[i * 3 + 2];
        if (Math.abs(x) > 12) dustVelArr[i * 3] *= -1;
        if (Math.abs(y) > 6) dustVelArr[i * 3 + 1] *= -1;
        if (Math.abs(z) > 12) dustVelArr[i * 3 + 2] *= -1;
        dustPos.setXYZ(i, x, y, z);
      }
      dustPos.needsUpdate = true;
      dustMat.opacity = 0.25 + Math.sin(t * 0.5) * 0.1;

      // Animate nodes
      Object.entries(nodesRef.current).forEach(([id, n]) => {
        const off = parseInt(id.replace(/\D/g, ""), 10) || 0;
        n.mesh.position.y = n.baseY + Math.sin(t + off * 0.7) * 0.12;
        n.glow.position.y = n.mesh.position.y;
        if (id === selectedId) {
          n.glow.scale.setScalar(1 + Math.sin(t * 4) * 0.35);
          (n.mesh.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.6 + Math.sin(t * 4) * 0.2;
        }
      });

      // Animate ripples
      ripplesRef.current = ripplesRef.current.filter(r => {
        const elapsed = (now - r.startTime) / 1000;
        if (elapsed > 1.5) { world.remove(r.ring); r.ring.geometry.dispose(); return false; }
        const scale = 1 + elapsed * 12;
        r.ring.scale.setScalar(scale);
        (r.ring.material as THREE.MeshBasicMaterial).opacity = Math.max(0, 0.7 * (1 - elapsed / 1.5));
        const node = nodesRef.current[r.agentId];
        if (node) { r.ring.position.copy(node.mesh.position); r.ring.lookAt(camera.position); }
        return true;
      });

      // Animate particle trails
      trailsRef.current = trailsRef.current.filter(tr => {
        const elapsed = (now - tr.startTime) / 1000;
        if (elapsed > 2) { world.remove(tr.particles); tr.particles.geometry.dispose(); return false; }
        const progress = Math.min(elapsed / 1.5, 1);
        const positions = tr.particles.geometry.attributes.position as THREE.BufferAttribute;
        const count = positions.count;
        for (let i = 0; i < count; i++) {
          const t2 = Math.max(0, progress - (i / count) * 0.4);
          const pt = tr.curve.getPoint(Math.min(t2, 1));
          positions.setXYZ(i, pt.x, pt.y, pt.z);
        }
        positions.needsUpdate = true;
        (tr.particles.material as THREE.PointsMaterial).opacity = Math.max(0, 0.9 * (1 - elapsed / 2));
        return true;
      });

      // Animate bankruptcy explosions
      bankruptRef.current = bankruptRef.current.filter(b => {
        const elapsed = (now - b.startTime) / 1000;
        if (elapsed > 2) {
          world.remove(b.particles); b.particles.geometry.dispose();
          world.remove(b.flash);
          return false;
        }
        const positions = b.particles.geometry.attributes.position as THREE.BufferAttribute;
        const velocities = b.particles.geometry.attributes.velocity as THREE.BufferAttribute;
        for (let i = 0; i < positions.count; i++) {
          positions.setX(i, positions.getX(i) + velocities.getX(i));
          positions.setY(i, positions.getY(i) + velocities.getY(i));
          positions.setZ(i, positions.getZ(i) + velocities.getZ(i));
        }
        positions.needsUpdate = true;
        (b.particles.material as THREE.PointsMaterial).opacity = Math.max(0, 1 - elapsed / 1.5);
        b.flash.intensity = Math.max(0, 3 * (1 - elapsed / 0.5));
        return true;
      });

      world.rotation.x = rotRef.current.x;
      world.rotation.y = rotRef.current.y + t * 0.03;
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    };
    animate();

    const onDown = (e: MouseEvent) => { mouseRef.current = { down: true, prevX: e.clientX, prevY: e.clientY }; };
    const onMove = (e: MouseEvent) => {
      if (!mouseRef.current.down) return;
      rotRef.current.y += (e.clientX - mouseRef.current.prevX) * 0.005;
      rotRef.current.x = Math.max(-1.2, Math.min(1.2, rotRef.current.x + (e.clientY - mouseRef.current.prevY) * 0.005));
      mouseRef.current.prevX = e.clientX; mouseRef.current.prevY = e.clientY;
    };
    const onUp = () => { mouseRef.current.down = false; };
    const onClick = (e: MouseEvent) => {
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
      camera.aspect = nw / nh; camera.updateProjectionMatrix(); renderer.setSize(nw, nh);
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

  // React to new events and trigger 3D effects
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;
    const spawnRipple = (container as any).__spawnRipple;
    const spawnTrail = (container as any).__spawnTrail;
    const spawnBankruptcy = (container as any).__spawnBankruptcy;
    if (!spawnRipple) return;

    events.forEach(ev => {
      if (processedEventsRef.current.has(ev.id)) return;
      processedEventsRef.current.add(ev.id);

      if (ev.type === "completed") spawnRipple(ev.agentId);
      if (ev.type === "transfer" && ev.targetAgentId) spawnTrail(ev.agentId, ev.targetAgentId);
      if (ev.type === "bankrupt") spawnBankruptcy(ev.agentId);
    });
  }, [events]);

  return <div ref={mountRef} style={{ width: "100%", height: "100%" }} />;
}

// ── Stat Card ───────────────────────────────────────────────────
function Stat({ label, value, sub, color = "#a78bfa" }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="text-xs uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.4)" }}>{label}</div>
      <div className="text-2xl font-bold mt-1" style={{ color }}>{value}</div>
      {sub && <div className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.3)" }}>{sub}</div>}
    </div>
  );
}

function SystemCard({ icon, title, items }: { icon: string; title: string; items: [string, string | number, string?][] }) {
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

// ── Live Task Feed Panel ────────────────────────────────────────
function TaskFeed({ events, onSelectAgent }: { events: TaskEvent[]; onSelectAgent: (id: string) => void }) {
  const feedRef = useRef<HTMLDivElement>(null);

  return (
    <div className="w-64 flex flex-col overflow-hidden" style={{ borderLeft: "1px solid rgba(255,255,255,0.05)" }}>
      <div className="px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        <div className="text-xs uppercase tracking-widest flex items-center gap-2" style={{ color: "rgba(255,255,255,0.4)" }}>
          <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#22c55e" }} />
          Live Task Feed
        </div>
      </div>
      <div ref={feedRef} className="flex-1 overflow-y-auto p-2 space-y-1">
        {events.map((ev, idx) => (
          <button
            key={ev.id}
            onClick={() => onSelectAgent(ev.agentId)}
            className="w-full text-left p-2 rounded-lg transition-all cursor-pointer hover:bg-white/5"
            style={{
              background: idx === 0 ? "rgba(255,255,255,0.04)" : "transparent",
              border: "1px solid transparent",
              borderColor: idx === 0 ? "rgba(255,255,255,0.06)" : "transparent",
              animation: idx === 0 ? "fadeSlideIn 0.4s ease-out" : undefined,
            }}
          >
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-xs">{EVENT_ICONS[ev.type]}</span>
              <span className="text-[10px] uppercase tracking-wider font-bold" style={{ color: EVENT_COLORS[ev.type] }}>
                {ev.type}
              </span>
              <span className="flex-1" />
              <span className="text-[9px] font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>
                {new Date(ev.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            </div>
            <div className="flex items-center gap-1 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: REALM_COLORS[ev.realm] }} />
              <span className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.5)" }}>
                {ROLE_ICONS[ev.agentRole] || "🤖"} {ev.agentRole}
              </span>
            </div>
            <div className="text-[11px] leading-tight" style={{ color: "rgba(255,255,255,0.6)" }}>
              {ev.detail}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Realm Health Bars ───────────────────────────────────────────
function RealmHealthBars({ realms }: { realms: typeof DEMO_DATA["realms"] }) {
  const realmEntries = Object.entries(realms) as [string, typeof realms["research"]][];
  return (
    <div className="flex gap-4 px-6 py-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(255,255,255,0.01)" }}>
      {realmEntries.map(([key, r]) => {
        const color = REALM_COLORS[key] || "#888";
        const energy = r.budget_allocated > 0 ? r.budget_remaining / r.budget_allocated : 0;
        const agentHealth = r.agents_active / Math.max(r.agents_active + r.agents_frozen + r.agents_bankrupt, 1);
        const combined = energy * 0.6 + agentHealth * 0.2 + r.avg_score * 0.2;
        return (
          <div key={key} className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] uppercase tracking-wider font-bold" style={{ color }}>
                {REALM_LABELS[key]?.split(" ").slice(0, 2).join(" ")}
              </span>
              <span className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.4)" }}>
                {(combined * 100).toFixed(0)}%
              </span>
            </div>
            <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
              <div className="h-full rounded-full transition-all duration-1000" style={{
                width: `${combined * 100}%`,
                background: `linear-gradient(90deg, ${color}90, ${color})`,
                boxShadow: `0 0 8px ${color}40`,
              }} />
            </div>
            <div className="flex justify-between mt-0.5">
              <span className="text-[9px]" style={{ color: "rgba(255,255,255,0.25)" }}>
                ⚡ {r.budget_remaining.toLocaleString()}/{r.budget_allocated.toLocaleString()} ◆
              </span>
              <span className="text-[9px]" style={{ color: "rgba(255,255,255,0.25)" }}>
                {r.agents_active} active · {r.tasks_completed} tasks
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Bloodline Tree ──────────────────────────────────────────────
function BloodlineTree({ agent, agents, onSelect }: { agent: Agent; agents: Agent[]; onSelect: (id: string) => void }) {
  // Build lineage: walk up from agent to root
  const lineage: Agent[] = [];
  let current: Agent | undefined = agent;
  const visited = new Set<string>();
  while (current) {
    if (visited.has(current.id)) break;
    visited.add(current.id);
    lineage.unshift(current);
    current = current.parentId ? agents.find(a => a.id === current!.parentId) : undefined;
  }

  // Find children of the selected agent
  const children = agents.filter(a => a.parentId === agent.id);

  return (
    <div className="mt-3 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="text-xs uppercase tracking-wider mb-3" style={{ color: "rgba(255,255,255,0.3)" }}>🧬 Bloodline</div>
      <div className="relative pl-4">
        {/* Vertical line */}
        <div className="absolute left-[7px] top-0 bottom-0 w-px" style={{ background: "rgba(255,255,255,0.08)" }} />

        {lineage.map((a, i) => {
          const isSelected = a.id === agent.id;
          const color = REALM_COLORS[a.realm] || "#888";
          return (
            <button
              key={a.id}
              onClick={() => onSelect(a.id)}
              className="relative flex items-center gap-2 py-1.5 w-full text-left cursor-pointer hover:bg-white/5 rounded px-1 transition-colors"
            >
              {/* Node dot on the vertical line */}
              <div className="absolute -left-3 w-3 h-3 rounded-full flex items-center justify-center" style={{
                background: isSelected ? color : "rgba(255,255,255,0.1)",
                border: `2px solid ${isSelected ? color : "rgba(255,255,255,0.15)"}`,
                boxShadow: isSelected ? `0 0 8px ${color}60` : "none",
              }}>
                {isSelected && <div className="w-1 h-1 rounded-full" style={{ background: "#fff" }} />}
              </div>
              <span className="text-[10px] font-mono" style={{ color: isSelected ? color : "rgba(255,255,255,0.4)" }}>
                Gen {a.generation}
              </span>
              <span className="text-xs" style={{ color: isSelected ? "#fff" : "rgba(255,255,255,0.5)" }}>
                {ROLE_ICONS[a.role] || "🤖"} {a.role}
              </span>
              {i < lineage.length - 1 && (
                <span className="text-[9px]" style={{ color: "rgba(255,255,255,0.2)" }}>→</span>
              )}
            </button>
          );
        })}

        {/* Children */}
        {children.length > 0 && (
          <div className="ml-3 mt-1 pl-3" style={{ borderLeft: `1px dashed ${REALM_COLORS[agent.realm]}30` }}>
            <div className="text-[9px] uppercase tracking-wider mb-1" style={{ color: "rgba(255,255,255,0.2)" }}>offspring</div>
            {children.map(child => (
              <button
                key={child.id}
                onClick={() => onSelect(child.id)}
                className="flex items-center gap-2 py-1 w-full text-left cursor-pointer hover:bg-white/5 rounded px-1 transition-colors"
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: REALM_COLORS[child.realm] }} />
                <span className="text-xs" style={{ color: "rgba(255,255,255,0.5)" }}>
                  {ROLE_ICONS[child.role] || "🤖"} {child.role}
                </span>
                <span className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.3)" }}>
                  Gen {child.generation}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Collision Engine Panel ───────────────────────────────────────
const THEORIES = [
  { id: "darwinian", name: "🧬 Darwinian Selection", desc: "Survival of the fittest agents", weights: { score: 0.7, budget: 0.2, gen: 0.1 } },
  { id: "lamarckian", name: "📚 Lamarckian Inheritance", desc: "Acquired traits pass to offspring", weights: { score: 0.3, budget: 0.5, gen: 0.2 } },
  { id: "symbiotic", name: "🤝 Symbiotic Mutualism", desc: "Cooperation amplifies both", weights: { score: 0.4, budget: 0.4, gen: 0.2 } },
  { id: "punctuated", name: "💥 Punctuated Equilibrium", desc: "Long stasis, sudden shifts", weights: { score: 0.5, budget: 0.1, gen: 0.4 } },
  { id: "redqueen", name: "♛ Red Queen", desc: "Constant adaptation to compete", weights: { score: 0.6, budget: 0.3, gen: 0.1 } },
  { id: "neutral", name: "🎲 Neutral Drift", desc: "Random walk dominates", weights: { score: 0.1, budget: 0.1, gen: 0.8 } },
];

interface CollisionResult {
  dominant: string;
  emergence: string;
  stability: number;
  mutationRate: number;
  prediction: string;
}

function collideTheories(a: typeof THEORIES[0], b: typeof THEORIES[0]): CollisionResult {
  const tension = Math.abs(a.weights.score - b.weights.score) + Math.abs(a.weights.budget - b.weights.budget);
  const stability = Math.max(0, 1 - tension);
  const mutationRate = tension * 0.5 + Math.random() * 0.1;
  const dominant = a.weights.score + a.weights.budget > b.weights.score + b.weights.budget ? a.name : b.name;
  const emergences = [
    "Hybrid vigor — both theories reinforce each other",
    "Antagonistic interference — unstable oscillation",
    "Novel synthesis — emergent strategy detected",
    "Dominant absorption — weaker theory subsumed",
    "Phase transition — system enters new regime",
    "Epistatic lock — neither can dominate alone",
  ];
  const emergence = emergences[Math.floor(tension * 5.99) % emergences.length];
  const predictions = [
    "Agents will converge toward cooperative equilibrium",
    "Expect divergent specialization across realms",
    "High mutation pressure — generational turnover accelerates",
    "Stable attractor detected — system will resist perturbation",
    "Chaotic regime — outcomes become unpredictable",
    "Gradual drift toward budgetary optimization",
  ];
  const prediction = predictions[Math.floor((stability + mutationRate) * 3) % predictions.length];
  return { dominant, emergence, stability, mutationRate, prediction };
}

function CollisionEngine({ show, onClose }: { show: boolean; onClose: () => void }) {
  const [theoryA, setTheoryA] = useState(THEORIES[0].id);
  const [theoryB, setTheoryB] = useState(THEORIES[2].id);
  const [result, setResult] = useState<CollisionResult | null>(null);
  const [animating, setAnimating] = useState(false);

  const runCollision = () => {
    const a = THEORIES.find(t => t.id === theoryA)!;
    const b = THEORIES.find(t => t.id === theoryB)!;
    setAnimating(true);
    setResult(null);
    setTimeout(() => {
      setResult(collideTheories(a, b));
      setAnimating(false);
    }, 800);
  };

  if (!show) return null;

  return (
    <div className="absolute bottom-48 left-1/2 -translate-x-1/2 w-[420px] rounded-xl p-5 z-30" style={{
      background: "rgba(10,10,20,0.97)", border: "1px solid rgba(255,255,255,0.08)",
      boxShadow: "0 0 60px rgba(0,0,0,0.5)", backdropFilter: "blur(12px)",
    }}>
      <div className="flex justify-between items-center mb-4">
        <div className="text-sm font-bold" style={{ color: "#f472b6" }}>⚛️ Theory Collision Engine</div>
        <button onClick={onClose} className="text-white opacity-40 hover:opacity-100 cursor-pointer">✕</button>
      </div>

      <div className="flex gap-3 mb-3">
        {[
          { value: theoryA, onChange: setTheoryA, label: "Theory A" },
          { value: theoryB, onChange: setTheoryB, label: "Theory B" },
        ].map(({ value, onChange, label }) => (
          <div key={label} className="flex-1">
            <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "rgba(255,255,255,0.3)" }}>{label}</div>
            <select
              value={value}
              onChange={e => onChange(e.target.value)}
              className="w-full text-xs rounded-lg px-2 py-2 cursor-pointer"
              style={{
                background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                color: "#fff", outline: "none",
              }}
            >
              {THEORIES.map(t => (
                <option key={t.id} value={t.id} style={{ background: "#1a1a2e" }}>{t.name}</option>
              ))}
            </select>
            <div className="text-[9px] mt-1" style={{ color: "rgba(255,255,255,0.25)" }}>
              {THEORIES.find(t => t.id === value)?.desc}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={runCollision}
        disabled={animating || theoryA === theoryB}
        className="w-full py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer"
        style={{
          background: animating ? "rgba(244,114,182,0.15)" : theoryA === theoryB ? "rgba(255,255,255,0.03)" : "linear-gradient(135deg, #f472b6, #a855f7)",
          color: theoryA === theoryB ? "rgba(255,255,255,0.2)" : "#fff",
          border: "1px solid rgba(255,255,255,0.1)",
        }}
      >
        {animating ? "⚡ Colliding..." : theoryA === theoryB ? "Pick two different theories" : "💥 Collide Theories"}
      </button>

      {result && (
        <div className="mt-4 space-y-2" style={{ animation: "fadeSlideIn 0.4s ease-out" }}>
          <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "rgba(255,255,255,0.3)" }}>Emergence</div>
            <div className="text-xs" style={{ color: "#f472b6" }}>{result.emergence}</div>
          </div>
          <div className="flex gap-2">
            <div className="flex-1 p-2 rounded-lg" style={{ background: "rgba(255,255,255,0.03)" }}>
              <div className="text-[9px] uppercase" style={{ color: "rgba(255,255,255,0.3)" }}>Stability</div>
              <div className="flex items-center gap-1 mt-1">
                <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                  <div className="h-full rounded-full" style={{
                    width: `${result.stability * 100}%`,
                    background: result.stability > 0.6 ? "#22c55e" : result.stability > 0.3 ? "#eab308" : "#ef4444",
                  }} />
                </div>
                <span className="text-[10px] font-mono text-white">{(result.stability * 100).toFixed(0)}%</span>
              </div>
            </div>
            <div className="flex-1 p-2 rounded-lg" style={{ background: "rgba(255,255,255,0.03)" }}>
              <div className="text-[9px] uppercase" style={{ color: "rgba(255,255,255,0.3)" }}>Mutation Rate</div>
              <div className="flex items-center gap-1 mt-1">
                <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                  <div className="h-full rounded-full" style={{
                    width: `${result.mutationRate * 100}%`,
                    background: "#a855f7",
                  }} />
                </div>
                <span className="text-[10px] font-mono text-white">{(result.mutationRate * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
          <div className="p-2 rounded-lg" style={{ background: "rgba(255,255,255,0.02)" }}>
            <div className="text-[9px] uppercase" style={{ color: "rgba(255,255,255,0.3)" }}>Dominant</div>
            <div className="text-xs text-white mt-0.5">{result.dominant}</div>
          </div>
          <div className="p-2 rounded-lg" style={{ background: "rgba(168,85,247,0.05)", border: "1px solid rgba(168,85,247,0.1)" }}>
            <div className="text-[9px] uppercase" style={{ color: "#a855f7" }}>🔮 Prediction</div>
            <div className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.7)" }}>{result.prediction}</div>
          </div>
        </div>
      )}
    </div>
  );
}


function AgentDetail({ agent, connections, agents, onClose, onSelect }: {
  agent: Agent; connections: Connection[]; agents: Agent[]; onClose: () => void; onSelect: (id: string) => void;
}) {
  const color = REALM_COLORS[agent.realm];
  return (
    <div className="absolute top-4 right-4 w-80 rounded-xl p-5 z-20 max-h-[calc(100%-2rem)] overflow-y-auto" style={{
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
          <span style={{ color: "#eab308" }} className="font-mono font-bold">{agent.budget.toFixed(0)} ◆</span>
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
      <BloodlineTree agent={agent} agents={agents} onSelect={onSelect} />
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────────
export default function ZhihuiTiDashboard() {
  const [data, setData] = useState<typeof DEMO_DATA | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [live, setLive] = useState(true);
  const [showCollision, setShowCollision] = useState(false);

  const handleSelect = useCallback((id: string) => setSelected(prev => prev === id ? null : id), []);

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

  const agents: Agent[] = data?.agents || [];
  const events = useSimulatedFeed(agents);

  if (!data) return (
    <div className="min-h-screen flex items-center justify-center text-white" style={{ background: "#0a0a14" }}>
      <div className="animate-pulse text-xl" style={{ color: "#a855f7" }}>Loading 智慧体...</div>
    </div>
  );

  const connections: Connection[] = [];
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

  const econ = data.economy;
  const mem = data.memory;
  const ins = data.inspection;
  const cb = data.circuit_breaker;
  const bh = data.behavior;
  const au = data.auctions;
  const ln = data.loans;
  const mk = data.market;
  const ft = data.futures;
  const ar = data.arbitration;
  const fa = data.factory;
  const msg = data.messaging;
  const goals = data.goal_history || [];
  const bl = data.bloodline;

  const econHistory = Array.from({ length: 20 }, (_, i) => ({
    day: i + 1,
    supply: (econ.money_supply || 10000) * (0.85 + Math.sin(i * 0.4) * 0.15 + i * 0.005),
    taxed: (econ.total_taxes_collected || 10) / 15 * (0.6 + Math.random() * 0.8),
  }));

  return (
    <div className="min-h-screen text-white relative" style={{
      background: "linear-gradient(135deg, #0a0a14 0%, #0d0d1a 50%, #0a0f18 100%)",
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* CSS for effects */}
      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes crtFlicker {
          0%, 100% { opacity: 1; }
          3% { opacity: 0.97; }
          6% { opacity: 1; }
          42% { opacity: 0.98; }
          44% { opacity: 1; }
          92% { opacity: 0.96; }
          94% { opacity: 1; }
        }
        @keyframes tronGrid {
          0% { background-position: 0px 0px; }
          100% { background-position: 0px 40px; }
        }
        .crt-overlay {
          pointer-events: none;
          position: fixed;
          inset: 0;
          z-index: 9999;
          background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 0, 0, 0.06) 2px,
            rgba(0, 0, 0, 0.06) 4px
          );
          animation: crtFlicker 4s infinite;
        }
        .tron-grid {
          pointer-events: none;
          position: fixed;
          inset: 0;
          z-index: 0;
          background-image:
            linear-gradient(rgba(99, 102, 241, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(99, 102, 241, 0.03) 1px, transparent 1px);
          background-size: 40px 40px;
          animation: tronGrid 8s linear infinite;
        }
      `}</style>
      <div className="crt-overlay" />
      <div className="tron-grid" />

      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center text-xl font-bold"
            style={{ background: "linear-gradient(135deg, #6366f1, #a855f7)" }}>慧</div>
          <div>
            <div className="text-sm font-bold tracking-wide">智慧体 ZHIHUITI</div>
            <div className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
              Autonomous Multi-Agent Ecosystem · {agents.length} agents
              {!live && <span className="ml-2" style={{ color: "#eab308" }}>(demo mode)</span>}
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

      {/* Realm Health Bars */}
      <RealmHealthBars realms={data.realms} />

      <div className="flex" style={{ height: "calc(100vh - 97px)" }}>
        {/* Left sidebar */}
        <div className="w-72 p-4 space-y-3 overflow-y-auto" style={{ borderRight: "1px solid rgba(255,255,255,0.05)" }}>
          <Stat label="Money Supply" value={`${(econ.money_supply || 0).toLocaleString()} ◆`} sub={`Treasury: ${(econ.treasury_balance || 0).toLocaleString()}`} color="#eab308" />
          <Stat label="Tasks Completed" value={mem.total_tasks || 0} sub={`Avg score: ${(mem.avg_task_score || 0).toFixed(2)}`} color="#22c55e" />
          <Stat label="Gene Pool" value={mem.gene_pool_size || 0} sub={`${bl.alive_genes || 0} alive · Gen ${bl.max_generation || 0}`} color="#a855f7" />
          <Stat label="Auctions Won" value={au.total_auctions || 0} sub={`Saved ${(au.total_savings || 0).toFixed(0)} ◆`} color="#3b82f6" />

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
                (g.goal || "").slice(0, 22) + ((g.goal?.length || 0) > 22 ? "..." : ""),
                (g.avg_score || 0).toFixed(2),
                (g.avg_score || 0) >= 0.8 ? "#22c55e" : "#eab308",
              ] as [string, string, string])
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
            <ThreeGraph agents={agents} connections={connections} onSelect={handleSelect} selectedId={selected} events={events} />
            <div className="absolute bottom-4 left-4 flex items-center gap-3">
              <span className="text-xs" style={{ color: "rgba(255,255,255,0.15)" }}>drag to rotate · click node for details</span>
              <button
                onClick={() => setShowCollision(s => !s)}
                className="text-[10px] px-2 py-1 rounded cursor-pointer transition-colors"
                style={{
                  background: showCollision ? "rgba(244,114,182,0.15)" : "rgba(255,255,255,0.05)",
                  color: showCollision ? "#f472b6" : "rgba(255,255,255,0.4)",
                  border: `1px solid ${showCollision ? "rgba(244,114,182,0.3)" : "rgba(255,255,255,0.08)"}`,
                }}
              >
                ⚛️ Collision Engine
              </button>
            </div>
            {selectedAgent && (
              <AgentDetail agent={selectedAgent} connections={selectedConns} agents={agents} onClose={() => setSelected(null)} onSelect={handleSelect} />
            )}
            <CollisionEngine show={showCollision} onClose={() => setShowCollision(false)} />
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

        {/* Right — Live Task Feed */}
        <TaskFeed events={events} onSelectAgent={handleSelect} />
      </div>
    </div>
  );
}