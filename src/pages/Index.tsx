import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { LeaderboardTable } from "@/components/LeaderboardTable";
import { ResizableWidget } from "@/components/ResizableWidget";
import { createPortal } from "react-dom";
import * as THREE from "three";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// ── Realm & Relationship Colors ─────────────────────────────────
const REALM_COLORS: Record<string, string> = { research: "#3b82f6", execution: "#f97316", central: "#a855f7" };
const REALM_LABELS: Record<string, string> = {
  research: "🔬 研发界 Research",
  execution: "⚡ 执行界 Execution",
  central: "🏛 中枢界 Central"
};
const CONN_COLORS: Record<string, string> = {
  transaction: "#22c55e", investment: "#3b82f6", bounty: "#eab308",
  employment: "#60a5fa", subsidy: "#a78bfa", bloodline: "#f472b6",
  host: "#14b8a6", competition: "#ef4444"
};
const ROLE_ICONS: Record<string, string> = {
  researcher: "🔬", analyst: "📊", coder: "💻", trader: "📈",
  judge: "⚖️", orchestrator: "🎯", custom: "🔧"
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
  name?: string;
  group?: "zhihuiti" | "hedge_fund";
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
  { id: "69ef96b5ed3e", role: "analyst", budget: 85.0, avg_score: 0.5, alive: true, realm: "research", life_state: "active", generation: 1, tasks: 0, parentId: "a4fdafbed41c" }],

  realms: {
    research: { budget_allocated: 2500, budget_remaining: 2200, agents_active: 6, agents_frozen: 0, agents_bankrupt: 0, tasks_completed: 3, tasks_failed: 0, avg_score: 0.86 },
    execution: { budget_allocated: 1750, budget_remaining: 1550, agents_active: 3, agents_frozen: 0, agents_bankrupt: 0, tasks_completed: 1, tasks_failed: 0, avg_score: 0.75 },
    central: { budget_allocated: 750, budget_remaining: 750, agents_active: 0, agents_frozen: 0, agents_bankrupt: 0, tasks_completed: 0, tasks_failed: 0, avg_score: 0 }
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
  { goal: "list 3 programming languages and their best use cases", task_count: 4, avg_score: 0.83 }],

  transactions: {},
  risk: { halted: false, peak_equity: 10000, current_drawdown: 0, trades_today: 0, max_drawdown_limit: 20 }
};

const EVENT_ICONS: Record<string, string> = {
  bid: "🏷️", assigned: "📋", completed: "✅", transfer: "💸", bankrupt: "💀"
};
const EVENT_COLORS: Record<string, string> = {
  bid: "#eab308", assigned: "#60a5fa", completed: "#22c55e", transfer: "#a78bfa", bankrupt: "#ef4444"
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
    "Train sub-model", "Rank candidate genes", "Assess risk factors"];

    const genEvent = (): TaskEvent => {
      const types: TaskEvent["type"][] = ["bid", "assigned", "completed", "transfer", "bankrupt"];
      const weights = [30, 25, 25, 18, 2]; // bankrupt is rare
      let r = Math.random() * 100;
      let type: TaskEvent["type"] = "bid";
      for (let i = 0; i < types.length; i++) {
        r -= weights[i];
        if (r <= 0) {type = types[i];break;}
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
        case "completed":{
            const score = (0.5 + Math.random() * 0.5).toFixed(2);
            amount = Math.round(10 + Math.random() * 40);
            detail = `Completed "${goal}" — score ${score}, earned ${amount} ◆`;
            break;
          }
        case "transfer":{
            const target = agents.filter((a) => a.id !== agent.id)[Math.floor(Math.random() * (agents.length - 1))];
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
        timestamp: Date.now()
      };
    };

    // Seed initial events
    const initial: TaskEvent[] = [];
    for (let i = 0; i < 6; i++) initial.push({ ...genEvent(), timestamp: Date.now() - (6 - i) * 3000 });
    setEvents(initial);

    const interval = setInterval(() => {
      setEvents((prev) => [genEvent(), ...prev].slice(0, 50));
    }, 2500 + Math.random() * 2000);
    return () => clearInterval(interval);
  }, [agents]);

  return events;
}

// ── 3D Realm-Grouped Graph ─────────────────────────────────────
const REALM_X: Record<string, number> = { research: -4, execution: 0, central: 4 };
const REALM_SPHERE_COLORS: Record<string, string> = { research: "#3b82f6", execution: "#f97316", central: "#a855f7" };

function ThreeGraph({ agents, connections, onSelect, selectedId, events, showZhihuiti = true, showHedgeFund = true, lodCount = 30
}: {agents: Agent[];connections: Connection[];onSelect: (id: string) => void;selectedId: string | null;events: TaskEvent[];showZhihuiti?: boolean;showHedgeFund?: boolean;lodCount?: number;}) {
  const [webglError, setWebglError] = useState(false);
  const mountRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<Record<string, {mesh: THREE.Mesh; label?: THREE.Sprite; basePos: THREE.Vector3; vel: THREE.Vector3; size: number;}>>({});
  const linesRef = useRef<{ line: THREE.Line; from: string; to: string; baseColor: string }[]>([]);
  const tokensRef = useRef<{ mesh: THREE.Mesh; from: string; to: string; progress: number; speed: number; color: string }[]>([]);
  const frameRef = useRef(0);
  const mouseRef = useRef({ down: false, prevX: 0, prevY: 0 });
  const rotRef = useRef({ x: 0.25, y: 0 });
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseVec = useRef(new THREE.Vector2());
  const worldRef = useRef<THREE.Group | null>(null);
  const positionsRef = useRef<Record<string, THREE.Vector3>>({});

  useEffect(() => {
    const container = mountRef.current;
    if (!container || !agents.length) return;

    const w = container.clientWidth;
    const h = container.clientHeight;
    nodesRef.current = {};

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 500);
    camera.position.z = 28;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, powerPreference: "low-power", failIfMajorPerformanceCaveat: false });
    } catch (e) {
      console.warn("WebGL context creation failed, showing fallback", e);
      setWebglError(true);
      return;
    }
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0x334466, 0.8));
    const keyLight = new THREE.DirectionalLight(0x6366f1, 0.6);
    keyLight.position.set(10, 12, 15);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xa855f7, 0.3);
    fillLight.position.set(-8, -4, 10);
    scene.add(fillLight);

    const world = new THREE.Group();
    worldRef.current = world;
    scene.add(world);

    // Filter & score agents
    const visibleAgents = agents.filter(a => {
      if (a.group === "zhihuiti" && !showZhihuiti) return false;
      if (a.group === "hedge_fund" && !showHedgeFund) return false;
      return a.alive;
    });

    const INITIAL_BUDGET = 100;
    const scored = visibleAgents.map(a => {
      const returnPct = ((a.budget - INITIAL_BUDGET) / INITIAL_BUDGET) * 100;
      const score = (a.avg_score * 0.4) + (Math.max(0, returnPct) / 100 * 0.3) + (a.avg_score * 0.3);
      return { ...a, lodScore: score };
    }).sort((a, b) => b.lodScore - a.lodScore);

    // Only show top N
    const showCount = lodCount === -1 ? scored.length : Math.min(lodCount, scored.length);
    const topAgents = scored.slice(0, showCount);

    // Group by realm and position
    const realmGroups: Record<string, typeof topAgents> = { research: [], execution: [], central: [] };
    topAgents.forEach(a => {
      const r = a.realm in realmGroups ? a.realm : "execution";
      realmGroups[r].push(a);
    });

    const positions: Record<string, THREE.Vector3> = {};
    const maxBudget = Math.max(...topAgents.map(x => x.budget), 1);

    Object.entries(realmGroups).forEach(([realm, group]) => {
      const cx = REALM_X[realm] || 0;
      const radius = Math.sqrt(group.length) * 2.2;
      group.forEach((a, i) => {
        const angle = (i / group.length) * Math.PI * 2 + (Math.random() - 0.5) * 1.2;
        const r = Math.sqrt(Math.random()) * radius;
        const x = cx + Math.cos(angle) * r + (Math.random() - 0.5) * 2.5;
        const y = Math.sin(angle) * r + (Math.random() - 0.5) * 2.5;
        const z = (Math.random() - 0.5) * 4;
        positions[a.id] = new THREE.Vector3(x, y, z);
      });
    });

    positionsRef.current = positions;

    // Realm labels
    Object.entries(REALM_X).forEach(([realm, cx]) => {
      const canvas = document.createElement("canvas");
      canvas.width = 256; canvas.height = 48;
      const ctx = canvas.getContext("2d")!;
      ctx.clearRect(0, 0, 256, 48);
      ctx.font = "bold 20px 'Inter', system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = REALM_SPHERE_COLORS[realm] || "#888";
      ctx.fillText(realm.toUpperCase(), 128, 24);
      const tex = new THREE.CanvasTexture(canvas);
      const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.4, depthWrite: false });
      const sprite = new THREE.Sprite(mat);
      const maxRows = Math.ceil((realmGroups[realm]?.length || 1) / Math.ceil(Math.sqrt(realmGroups[realm]?.length || 1)));
      sprite.position.set(cx, maxRows * 1.1 + 1.5, 0);
      sprite.scale.set(4, 0.75, 1);
      world.add(sprite);
    });

    // Create spheres
    topAgents.forEach(a => {
      const pos = positions[a.id];
      if (!pos) return;
      const color = REALM_SPHERE_COLORS[a.realm] || "#888";
      const size = 0.2 + (a.budget / maxBudget) * 0.6;

      const geo = new THREE.SphereGeometry(size, 24, 24);
      const mat = new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.35,
        metalness: 0.5,
        roughness: 0.3,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.copy(pos);
      mesh.userData = { agentId: a.id };
      world.add(mesh);

      // Label: role + score
      const labelCanvas = document.createElement("canvas");
      labelCanvas.width = 512; labelCanvas.height = 96;
      const lctx = labelCanvas.getContext("2d")!;
      lctx.clearRect(0, 0, 512, 96);
      lctx.font = "bold 24px 'Inter', system-ui, sans-serif";
      lctx.textAlign = "center";
      lctx.textBaseline = "middle";
      lctx.fillStyle = "rgba(255,255,255,0.75)";
      lctx.fillText(a.name || a.role, 256, 30);
      lctx.font = "16px 'Inter', system-ui, sans-serif";
      lctx.fillStyle = "rgba(255,255,255,0.4)";
      lctx.fillText(`${a.role} · ${a.avg_score.toFixed(2)}`, 256, 62);
      const tex = new THREE.CanvasTexture(labelCanvas);
      tex.needsUpdate = true;
      const sMat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.7, depthWrite: false });
      const labelSprite = new THREE.Sprite(sMat);
      labelSprite.position.set(pos.x, pos.y + size + 0.55, pos.z);
      labelSprite.scale.set(2.4, 0.45, 1);
      world.add(labelSprite);

      nodesRef.current[a.id] = {
        mesh,
        label: labelSprite,
        basePos: pos.clone(),
        vel: new THREE.Vector3(),
        size
      };
    });

    // Connection lines between agents
    const visibleIds = new Set(topAgents.map(a => a.id));
    const visibleConns = connections.filter(c => visibleIds.has(c.from) && visibleIds.has(c.to));
    const lineEntries: typeof linesRef.current = [];
    visibleConns.forEach(conn => {
      const p1 = positions[conn.from];
      const p2 = positions[conn.to];
      if (!p1 || !p2) return;
      const lineGeo = new THREE.BufferGeometry().setFromPoints([p1, p2]);
      const lineColor = CONN_COLORS[conn.type] || "#555";
      const lineMat = new THREE.LineBasicMaterial({
        color: lineColor,
        transparent: true,
        opacity: 0.2,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const line = new THREE.Line(lineGeo, lineMat);
      world.add(line);
      lineEntries.push({ line, from: conn.from, to: conn.to, baseColor: lineColor });
    });
    linesRef.current = lineEntries;

    // Token particles flowing along connections
    const tokenEntries: typeof tokensRef.current = [];
    const maxTokens = Math.min(visibleConns.length * 2, 300);
    for (let i = 0; i < maxTokens; i++) {
      const conn = visibleConns[i % visibleConns.length];
      const color = CONN_COLORS[conn.type] || "#aaa";
      const geo = new THREE.SphereGeometry(0.08, 6, 6);
      const mat = new THREE.MeshBasicMaterial({
        color, transparent: true, opacity: 0.8,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.visible = false;
      world.add(mesh);
      tokenEntries.push({
        mesh, from: conn.from, to: conn.to,
        progress: Math.random(),
        speed: 0.005 + Math.random() * 0.008,
        color,
      });
    }
    tokensRef.current = tokenEntries;

    // Ambient dust
    const dustCount = 80;
    const dustArr = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount; i++) {
      dustArr[i * 3] = (Math.random() - 0.5) * 35;
      dustArr[i * 3 + 1] = (Math.random() - 0.5) * 15;
      dustArr[i * 3 + 2] = (Math.random() - 0.5) * 20;
    }
    const dustGeo = new THREE.BufferGeometry();
    dustGeo.setAttribute("position", new THREE.BufferAttribute(dustArr, 3));
    const dustMat = new THREE.PointsMaterial({
      color: "#6366f1", size: 0.03, transparent: true, opacity: 0.15,
      blending: THREE.AdditiveBlending, depthWrite: false
    });
    world.add(new THREE.Points(dustGeo, dustMat));

    let running = true;
    const animate = () => {
      if (!running) return;
      frameRef.current++;
      const t = frameRef.current * 0.006;

      Object.entries(nodesRef.current).forEach(([id, n]) => {
        const off = parseInt(id.replace(/\D/g, ""), 10) || 0;
        const floatY = Math.sin(t + off * 0.5) * 0.08;
        n.mesh.position.y = n.basePos.y + floatY;
        if (n.label) n.label.position.y = n.basePos.y + floatY + n.size + 0.55;

        if (id === selectedId) {
          const pulse = 1 + Math.sin(t * 5) * 0.15;
          n.mesh.scale.setScalar(pulse);
          (n.mesh.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.4 + Math.sin(t * 5) * 0.2;
        } else {
          n.mesh.scale.setScalar(1);
          (n.mesh.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.35;
        }
      });

      // Dynamic line highlighting
      const hasSelection = !!selectedId;
      linesRef.current.forEach(({ line, from, to }) => {
        const mat = line.material as THREE.LineBasicMaterial;
        const connected = from === selectedId || to === selectedId;
        if (hasSelection) {
          mat.opacity = connected ? 0.7 + Math.sin(t * 4) * 0.15 : 0.03;
          mat.linewidth = connected ? 2 : 1;
        } else {
          mat.opacity = 0.2;
        }
      });

      // Animate token particles along connections
      tokensRef.current.forEach(tok => {
        tok.progress += tok.speed;
        if (tok.progress > 1) tok.progress -= 1;
        const p1 = positionsRef.current[tok.from];
        const p2 = positionsRef.current[tok.to];
        if (p1 && p2) {
          tok.mesh.visible = true;
          tok.mesh.position.lerpVectors(p1, p2, tok.progress);
          const mat = tok.mesh.material as THREE.MeshBasicMaterial;
          const isConnected = tok.from === selectedId || tok.to === selectedId;
          if (hasSelection) {
            mat.opacity = isConnected ? 0.9 : 0.05;
            tok.mesh.scale.setScalar(isConnected ? 1.8 : 0.6);
          } else {
            mat.opacity = 0.8 + Math.sin(tok.progress * Math.PI) * 0.2;
            tok.mesh.scale.setScalar(1);
          }
        }
      });

      world.rotation.x = rotRef.current.x;
      world.rotation.y = rotRef.current.y + t * 0.02;
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    };
    animate();

    const onDown = (e: MouseEvent) => { mouseRef.current = { down: true, prevX: e.clientX, prevY: e.clientY }; };
    const onMove = (e: MouseEvent) => {
      if (!mouseRef.current.down) return;
      rotRef.current.y += (e.clientX - mouseRef.current.prevX) * 0.005;
      rotRef.current.x = Math.max(-1.2, Math.min(1.2, rotRef.current.x + (e.clientY - mouseRef.current.prevY) * 0.005));
      mouseRef.current.prevX = e.clientX;
      mouseRef.current.prevY = e.clientY;
    };
    const onUp = () => { mouseRef.current.down = false; };
    const onClick = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouseVec.current.set((e.clientX - rect.left) / w * 2 - 1, -((e.clientY - rect.top) / h) * 2 + 1);
      raycasterRef.current.setFromCamera(mouseVec.current, camera);
      const hits = raycasterRef.current.intersectObjects(Object.values(nodesRef.current).map(n => n.mesh));
      if (hits.length) onSelect(hits[0].object.userData.agentId);
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      camera.position.z = Math.max(8, Math.min(80, camera.position.z + e.deltaY * 0.03));
    };

    // Pinch-to-zoom for touch devices
    let lastPinchDist = 0;
    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        lastPinchDist = Math.sqrt(dx * dx + dy * dy);
      }
    };
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (lastPinchDist > 0) {
          const delta = lastPinchDist - dist;
          camera.position.z = Math.max(8, Math.min(80, camera.position.z + delta * 0.08));
        }
        lastPinchDist = dist;
      }
    };
    const onTouchEnd = () => { lastPinchDist = 0; };

    container.addEventListener("mousedown", onDown);
    container.addEventListener("mousemove", onMove);
    container.addEventListener("mouseup", onUp);
    container.addEventListener("click", onClick);
    container.addEventListener("wheel", onWheel, { passive: false });
    container.addEventListener("touchstart", onTouchStart, { passive: false });
    container.addEventListener("touchmove", onTouchMove, { passive: false });
    container.addEventListener("touchend", onTouchEnd);

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
      container.removeEventListener("wheel", onWheel);
      container.removeEventListener("touchstart", onTouchStart);
      container.removeEventListener("touchmove", onTouchMove);
      container.removeEventListener("touchend", onTouchEnd);
      window.removeEventListener("resize", onResize);
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, [agents, connections, selectedId, onSelect, showZhihuiti, showHedgeFund, lodCount]);

  if (webglError) {
    return (
      <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.3)", borderRadius: 12, padding: 24 }}>
        <div style={{ textAlign: "center", color: "rgba(255,255,255,0.6)" }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>⚠️</div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>3D Graph Unavailable</div>
          <div style={{ fontSize: 11, opacity: 0.6 }}>WebGL not supported in this environment. Agent data is still available in the sidebar.</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <div ref={mountRef} style={{ width: "100%", height: "100%" }} />
      <div style={{
        position: "absolute", bottom: 12, left: 12,
        background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)",
        borderRadius: 8, padding: "8px 12px",
        border: "1px solid rgba(255,255,255,0.08)",
        pointerEvents: "none",
      }}>
        <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: 1.5, color: "rgba(255,255,255,0.4)", marginBottom: 4 }}>Connections</div>
        {Object.entries(CONN_COLORS).map(([type, color]) => (
          <div key={type} style={{ display: "flex", alignItems: "center", gap: 6, padding: "1px 0" }}>
            <span style={{ width: 14, height: 2, borderRadius: 1, background: color, display: "inline-block" }} />
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", textTransform: "capitalize" }}>{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Stat Card ───────────────────────────────────────────────────
function Stat({ label, value, sub, color = "#a78bfa" }: {label: string;value: string | number;sub?: string;color?: string;}) {
  return (
    <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="text-xs uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.4)" }}>{label}</div>
      <div className="font-bold mt-1 text-base" style={{ color }}>{value}</div>
      {sub && <div className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.3)" }}>{sub}</div>}
    </div>);

}

function SystemCard({ icon, title, items }: {icon: string;title: string;items: [string, string | number, string?][];}) {
  return (
    <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.4)" }}>{icon} {title}</div>
      {items.map(([label, value, color], i) =>
      <div key={i} className="flex justify-between text-xs py-0.5">
          <span style={{ color: "rgba(255,255,255,0.5)" }}>{label}</span>
          <span className="font-mono" style={{ color: color || "#fff" }}>{value}</span>
        </div>
      )}
    </div>);

}

// ── Live Task Feed Panel ────────────────────────────────────────
function TaskFeed({ events, onSelectAgent }: {events: TaskEvent[];onSelectAgent: (id: string) => void;}) {
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
        {events.map((ev, idx) =>
        <button
          key={ev.id}
          onClick={() => onSelectAgent(ev.agentId)}
          className="w-full text-left p-2 rounded-lg transition-all cursor-pointer hover:bg-white/5"
          style={{
            background: idx === 0 ? "rgba(255,255,255,0.04)" : "transparent",
            border: "1px solid transparent",
            borderColor: idx === 0 ? "rgba(255,255,255,0.06)" : "transparent",
            animation: idx === 0 ? "fadeSlideIn 0.4s ease-out" : undefined
          }}>
          
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
        )}
      </div>
    </div>);

}

// ── Results Panel ───────────────────────────────────────────────
function ResultsPanel({ jobId, result, loading, onClose




}: {jobId: string;result: any;loading: boolean;onClose: () => void;}) {
  if (!jobId) return null;

  const isDone = result?.status === "done" || result?.status === "completed";
  const jobData = result?.result || result;
  const tasks = jobData?.tasks || [];
  const goal = jobData?.goal || result?.goal || "";
  const economy = jobData?.economy || {};
  const stats = jobData?.stats || {};

  return (
    <div className="w-80 flex flex-col overflow-hidden" style={{ borderLeft: "1px solid rgba(255,255,255,0.05)" }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        <div className="text-xs uppercase tracking-widest flex items-center gap-2" style={{ color: "rgba(255,255,255,0.4)" }}>
          <span>📋 Job Results</span>
        </div>
        <button onClick={onClose} className="text-white opacity-40 hover:opacity-100 cursor-pointer text-sm">✕</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ scrollbarWidth: "thin" }}>
        {/* Loading state */}
        {(loading || !isDone) && !result ?
        <div className="flex flex-col items-center justify-center py-12 gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "rgba(99,102,241,0.4)", borderTopColor: "transparent" }} />
            <div className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
              {loading ? "Loading job data..." : "Waiting for results..."}
            </div>
            <div className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>
              Polling every 5s...
            </div>
          </div> :
        !isDone && result ?
        <div className="flex flex-col items-center justify-center py-12 gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "#eab308", borderTopColor: "transparent" }} />
            <div className="text-xs font-bold" style={{ color: "#eab308" }}>Job Running...</div>
            <div className="text-xs text-center px-2" style={{ color: "rgba(255,255,255,0.5)" }}>{goal}</div>
            <div className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>
              Auto-refreshing...
            </div>
          </div> :

        <>
            {/* Goal */}
            <div className="p-3 rounded-lg" style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)" }}>
              <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "rgba(99,102,241,0.7)" }}>Goal</div>
              <div className="text-sm text-white leading-snug">{goal}</div>
            </div>

            {/* Job ID */}
            <div className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>
              ID: {jobId}
            </div>

            {/* Tasks */}
            {tasks.length > 0 &&
          <div>
                <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>
                  Tasks ({tasks.length})
                </div>
                <div className="space-y-2">
                  {tasks.map((task: any, i: number) => {
                const scoreColor = (task.score || 0) >= 0.85 ? "#22c55e" : (task.score || 0) >= 0.7 ? "#eab308" : "#ef4444";
                return (
                  <div key={i} className="p-2.5 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs">{ROLE_ICONS[task.role] || "🤖"}</span>
                            <span className="text-[10px] uppercase tracking-wider font-bold" style={{ color: REALM_COLORS[task.role === "researcher" ? "research" : "execution"] || "#a855f7" }}>
                              {task.role}
                            </span>
                          </div>
                          <span className="text-xs font-mono font-bold" style={{ color: scoreColor }}>
                            {((task.score || 0) * 100).toFixed(0)}%
                          </span>
                        </div>

                        {/* Task description - truncated */}
                        <div className="text-[11px] leading-snug mb-2" style={{ color: "rgba(255,255,255,0.6)" }}>
                          {(task.task || "").split("\n")[0].slice(0, 80)}{(task.task || "").length > 80 ? "..." : ""}
                        </div>

                        {/* Score bar */}
                        <div className="w-full h-1.5 rounded-full mb-1.5" style={{ background: "rgba(255,255,255,0.06)" }}>
                          <div className="h-full rounded-full transition-all" style={{
                        width: `${(task.score || 0) * 100}%`,
                        background: scoreColor
                      }} />
                        </div>

                        <div className="flex items-center justify-between text-[10px]">
                          <span className="font-mono" style={{ color: "rgba(255,255,255,0.3)" }}>
                            Agent: {(task.agent_id || "").slice(0, 8)}
                          </span>
                          {task.reward &&
                      <span style={{ color: "#eab308" }}>
                              +{task.reward.net?.toFixed(1) || task.reward.gross?.toFixed(1)} ◆
                            </span>
                      }
                        </div>

                        {task.num_bids &&
                    <div className="text-[10px] mt-1" style={{ color: "rgba(255,255,255,0.2)" }}>
                            Bid: {task.bid?.toFixed(1)} ◆ · {task.num_bids} bidders
                          </div>
                    }
                      </div>);

              })}
                </div>
              </div>
          }

            {/* Economy Summary */}
            {economy.treasury_balance != null &&
          <div className="p-3 rounded-lg" style={{ background: "rgba(234,179,8,0.05)", border: "1px solid rgba(234,179,8,0.15)" }}>
                <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: "#eab308" }}>💰 Economy</div>
                <div className="space-y-1">
                  {[
              ["Treasury", `${economy.treasury_balance?.toLocaleString()} ◆`],
              ["Rewards Paid", `${economy.total_rewards_paid?.toFixed(1)} ◆`],
              ["Taxes Collected", `${economy.total_taxes_collected?.toFixed(1)} ◆`],
              ["Tax Rate", economy.tax_rate || "15%"]].
              map(([label, value], i) =>
              <div key={i} className="flex justify-between text-xs">
                      <span style={{ color: "rgba(255,255,255,0.4)" }}>{label}</span>
                      <span className="font-mono text-white">{value}</span>
                    </div>
              )}
                </div>
              </div>
          }

            {/* Stats Summary */}
            {stats.total_tasks != null &&
          <div className="p-3 rounded-lg" style={{ background: "rgba(34,197,94,0.05)", border: "1px solid rgba(34,197,94,0.15)" }}>
                <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: "#22c55e" }}>📊 Stats</div>
                <div className="space-y-1">
                  {[
              ["Total Tasks", stats.total_tasks],
              ["Total Agents", stats.total_agents],
              ["Avg Score", stats.avg_task_score?.toFixed(3)],
              ["Gene Pool", stats.gene_pool_size]].
              map(([label, value], i) =>
              <div key={i} className="flex justify-between text-xs">
                      <span style={{ color: "rgba(255,255,255,0.4)" }}>{label}</span>
                      <span className="font-mono text-white">{value}</span>
                    </div>
              )}
                </div>
              </div>
          }

            {/* Winning Agents */}
            {tasks.length > 0 &&
          <div className="p-3 rounded-lg" style={{ background: "rgba(168,85,247,0.05)", border: "1px solid rgba(168,85,247,0.15)" }}>
                <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: "#a855f7" }}>🏆 Winning Agents</div>
                <div className="space-y-1">
                  {tasks.map((task: any, i: number) =>
              <div key={i} className="flex items-center gap-2 text-xs">
                      <span>{ROLE_ICONS[task.role] || "🤖"}</span>
                      <span className="font-mono text-[10px]" style={{ color: "rgba(255,255,255,0.5)" }}>
                        {(task.agent_id || "").slice(0, 12)}
                      </span>
                      <span className="flex-1" />
                      <span className="font-mono" style={{ color: task.alive ? "#22c55e" : "#ef4444" }}>
                        {task.alive ? "●" : "○"}
                      </span>
                    </div>
              )}
                </div>
              </div>
          }
          </>
        }
      </div>
    </div>);

}

// ── Realm Health Bars ───────────────────────────────────────────
function RealmHealthBars({ realms, agents }: {realms: typeof DEMO_DATA["realms"]; agents: Agent[];}) {
  const realmEntries = Object.entries(realms) as [string, typeof realms["research"]][];
  return (
    <div className="flex gap-4 px-6 py-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(255,255,255,0.01)" }}>
      {realmEntries.map(([key, r]) => {
        const color = REALM_COLORS[key] || "#888";
        const energy = r.budget_allocated > 0 ? r.budget_remaining / r.budget_allocated : 0;
        const activeCount = agents.filter(a => a.realm === key && a.life_state === 'active').length;
        const agentHealth = activeCount / Math.max(activeCount + r.agents_frozen + r.agents_bankrupt, 1);
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
                boxShadow: `0 0 8px ${color}40`
              }} />
            </div>
            <div className="flex justify-between mt-0.5">
              <span className="text-[9px]" style={{ color: "rgba(255,255,255,0.25)" }}>
                ⚡ {r.budget_remaining.toLocaleString()}/{r.budget_allocated.toLocaleString()} ◆
              </span>
              <span className="text-[9px]" style={{ color: "rgba(255,255,255,0.25)" }}>
                {agents.filter(a => a.realm === key && a.life_state === 'active').length} active · {r.tasks_completed} tasks
              </span>
            </div>
          </div>);

      })}
    </div>);

}

// ── Bloodline Tree ──────────────────────────────────────────────
function BloodlineTree({ agent, agents, onSelect }: {agent: Agent;agents: Agent[];onSelect: (id: string) => void;}) {
  // Build lineage: walk up from agent to root
  const lineage: Agent[] = [];
  let current: Agent | undefined = agent;
  const visited = new Set<string>();
  while (current) {
    if (visited.has(current.id)) break;
    visited.add(current.id);
    lineage.unshift(current);
    current = current.parentId ? agents.find((a) => a.id === current!.parentId) : undefined;
  }

  // Find children of the selected agent
  const children = agents.filter((a) => a.parentId === agent.id);

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
              className="relative flex items-center gap-2 py-1.5 w-full text-left cursor-pointer hover:bg-white/5 rounded px-1 transition-colors">
              
              {/* Node dot on the vertical line */}
              <div className="absolute -left-3 w-3 h-3 rounded-full flex items-center justify-center" style={{
                background: isSelected ? color : "rgba(255,255,255,0.1)",
                border: `2px solid ${isSelected ? color : "rgba(255,255,255,0.15)"}`,
                boxShadow: isSelected ? `0 0 8px ${color}60` : "none"
              }}>
                {isSelected && <div className="w-1 h-1 rounded-full" style={{ background: "#fff" }} />}
              </div>
              <span className="text-[10px] font-mono" style={{ color: isSelected ? color : "rgba(255,255,255,0.4)" }}>
                Gen {a.generation}
              </span>
              <span className="text-xs" style={{ color: isSelected ? "#fff" : "rgba(255,255,255,0.5)" }}>
                {ROLE_ICONS[a.role] || "🤖"} {a.role}
              </span>
              {i < lineage.length - 1 &&
              <span className="text-[9px]" style={{ color: "rgba(255,255,255,0.2)" }}>→</span>
              }
            </button>);

        })}

        {/* Children */}
        {children.length > 0 &&
        <div className="ml-3 mt-1 pl-3" style={{ borderLeft: `1px dashed ${REALM_COLORS[agent.realm]}30` }}>
            <div className="text-[9px] uppercase tracking-wider mb-1" style={{ color: "rgba(255,255,255,0.2)" }}>offspring</div>
            {children.map((child) =>
          <button
            key={child.id}
            onClick={() => onSelect(child.id)}
            className="flex items-center gap-2 py-1 w-full text-left cursor-pointer hover:bg-white/5 rounded px-1 transition-colors">
            
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: REALM_COLORS[child.realm] }} />
                <span className="text-xs" style={{ color: "rgba(255,255,255,0.5)" }}>
                  {ROLE_ICONS[child.role] || "🤖"} {child.role}
                </span>
                <span className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.3)" }}>
                  Gen {child.generation}
                </span>
              </button>
          )}
          </div>
        }
      </div>
    </div>);

}

// ── Collision Engine Panel ───────────────────────────────────────
const THEORIES = [
{ id: "darwinian", name: "🧬 Darwinian Selection", desc: "Survival of the fittest agents", weights: { score: 0.7, budget: 0.2, gen: 0.1 } },
{ id: "lamarckian", name: "📚 Lamarckian Inheritance", desc: "Acquired traits pass to offspring", weights: { score: 0.3, budget: 0.5, gen: 0.2 } },
{ id: "symbiotic", name: "🤝 Symbiotic Mutualism", desc: "Cooperation amplifies both", weights: { score: 0.4, budget: 0.4, gen: 0.2 } },
{ id: "punctuated", name: "💥 Punctuated Equilibrium", desc: "Long stasis, sudden shifts", weights: { score: 0.5, budget: 0.1, gen: 0.4 } },
{ id: "redqueen", name: "♛ Red Queen", desc: "Constant adaptation to compete", weights: { score: 0.6, budget: 0.3, gen: 0.1 } },
{ id: "neutral", name: "🎲 Neutral Drift", desc: "Random walk dominates", weights: { score: 0.1, budget: 0.1, gen: 0.8 } }];


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
  "Epistatic lock — neither can dominate alone"];

  const emergence = emergences[Math.floor(tension * 5.99) % emergences.length];
  const predictions = [
  "Agents will converge toward cooperative equilibrium",
  "Expect divergent specialization across realms",
  "High mutation pressure — generational turnover accelerates",
  "Stable attractor detected — system will resist perturbation",
  "Chaotic regime — outcomes become unpredictable",
  "Gradual drift toward budgetary optimization"];

  const prediction = predictions[Math.floor((stability + mutationRate) * 3) % predictions.length];
  return { dominant, emergence, stability, mutationRate, prediction };
}

function CollisionEngine({ show, onClose }: {show: boolean;onClose: () => void;}) {
  const [theoryA, setTheoryA] = useState(THEORIES[0].id);
  const [theoryB, setTheoryB] = useState(THEORIES[2].id);
  const [result, setResult] = useState<CollisionResult | null>(null);
  const [animating, setAnimating] = useState(false);

  const runCollision = () => {
    const a = THEORIES.find((t) => t.id === theoryA)!;
    const b = THEORIES.find((t) => t.id === theoryB)!;
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
      boxShadow: "0 0 60px rgba(0,0,0,0.5)", backdropFilter: "blur(12px)"
    }}>
      <div className="flex justify-between items-center mb-4">
        <div className="text-sm font-bold" style={{ color: "#f472b6" }}>⚛️ Theory Collision Engine</div>
        <button onClick={onClose} className="text-white opacity-40 hover:opacity-100 cursor-pointer">✕</button>
      </div>

      <div className="flex gap-3 mb-3">
        {[
        { value: theoryA, onChange: setTheoryA, label: "Theory A" },
        { value: theoryB, onChange: setTheoryB, label: "Theory B" }].
        map(({ value, onChange, label }) =>
        <div key={label} className="flex-1">
            <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "rgba(255,255,255,0.3)" }}>{label}</div>
            <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full text-xs rounded-lg px-2 py-2 cursor-pointer"
            style={{
              background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
              color: "#fff", outline: "none"
            }}>
            
              {THEORIES.map((t) =>
            <option key={t.id} value={t.id} style={{ background: "#1a1a2e" }}>{t.name}</option>
            )}
            </select>
            <div className="text-[9px] mt-1" style={{ color: "rgba(255,255,255,0.25)" }}>
              {THEORIES.find((t) => t.id === value)?.desc}
            </div>
          </div>
        )}
      </div>

      <button
        onClick={runCollision}
        disabled={animating || theoryA === theoryB}
        className="w-full py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer"
        style={{
          background: animating ? "rgba(244,114,182,0.15)" : theoryA === theoryB ? "rgba(255,255,255,0.03)" : "linear-gradient(135deg, #f472b6, #a855f7)",
          color: theoryA === theoryB ? "rgba(255,255,255,0.2)" : "#fff",
          border: "1px solid rgba(255,255,255,0.1)"
        }}>
        
        {animating ? "⚡ Colliding..." : theoryA === theoryB ? "Pick two different theories" : "💥 Collide Theories"}
      </button>

      {result &&
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
                  background: result.stability > 0.6 ? "#22c55e" : result.stability > 0.3 ? "#eab308" : "#ef4444"
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
                  background: "#a855f7"
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
      }
    </div>);

}


function AgentDetail({ agent, connections, agents, onClose, onSelect

}: {agent: Agent;connections: Connection[];agents: Agent[];onClose: () => void;onSelect: (id: string) => void;}) {
  const color = REALM_COLORS[agent.realm];
  return (
    <div className="absolute top-4 right-4 w-80 rounded-xl p-5 z-20 max-h-[calc(100%-2rem)] overflow-y-auto" style={{
      background: "rgba(10,10,20,0.95)", border: `1px solid ${color}40`, boxShadow: `0 0 40px ${color}20`,
      backdropFilter: "blur(10px)"
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
              background: `linear-gradient(90deg, ${agent.avg_score >= 0.8 ? "#22c55e" : agent.avg_score >= 0.5 ? "#eab308" : "#ef4444"}, ${color})`
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
      {connections.length > 0 &&
      <div className="mt-4 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Connections</div>
          {connections.slice(0, 8).map((c, i) => {
          const otherId = c.from === agent.id ? c.to : c.from;
          const other = agents.find((a) => a.id === otherId);
          return (
            <div key={i} className="flex items-center gap-2 text-xs py-0.5">
                <span className="w-2 h-2 rounded-full" style={{ background: CONN_COLORS[c.type] || "#666" }} />
                <span style={{ color: "rgba(255,255,255,0.5)" }}>{c.type}</span>
                <span className="text-white font-mono">{other ? `${ROLE_ICONS[other.role] || ""} ${other.role}` : otherId.slice(0, 8)}</span>
              </div>);

        })}
        </div>
      }
      <BloodlineTree agent={agent} agents={agents} onSelect={onSelect} />
    </div>);

}

// ── Main Dashboard ──────────────────────────────────────────────
// ── Boot Sequence ───────────────────────────────────────────────
const BOOT_LINES = [
{ text: "ZHIHUITI KERNEL v3.1.7 — initializing...", delay: 0, color: "#6366f1" },
{ text: "Loading neural mesh topology ████████████ OK", delay: 400, color: "#a855f7" },
{ text: "Spawning agent runtime (9 cores) ··· ONLINE", delay: 900, color: "#22c55e" },
{ text: "Mounting realm partitions: 研发界 · 执行界 · 中枢界", delay: 1400, color: "#3b82f6" },
{ text: "Calibrating auction engine ░░░░░░░░░░░░ READY", delay: 1900, color: "#eab308" },
{ text: "Bloodline index built — 9 genes mapped", delay: 2300, color: "#f472b6" },
{ text: "Circuit breaker armed — 4 laws active", delay: 2600, color: "#ef4444" },
{ text: "Token economy linked — 10,000 ◆ supply", delay: 2900, color: "#eab308" },
{ text: "All subsystems nominal. Entering dashboard ▸", delay: 3300, color: "#22c55e" }];


function BootSequence({ onComplete }: {onComplete: () => void;}) {
  const [visibleLines, setVisibleLines] = useState(0);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    BOOT_LINES.forEach((line, i) => {
      timers.push(setTimeout(() => setVisibleLines(i + 1), line.delay));
    });
    // Start fade out after last line
    timers.push(setTimeout(() => setFading(true), 3800));
    timers.push(setTimeout(() => onComplete(), 4400));
    return () => timers.forEach(clearTimeout);
  }, [onComplete]);

  return (
    <div
      className="fixed inset-0 z-[99999] flex flex-col items-center justify-center"
      style={{
        background: "#0a0a14",
        opacity: fading ? 0 : 1,
        transition: "opacity 0.6s ease-out"
      }}>
      
      {/* Logo pulse */}
      <div className="mb-8 flex flex-col items-center">
        <div
          className="w-16 h-16 rounded-xl flex items-center justify-center text-3xl font-bold mb-3"
          style={{
            background: "linear-gradient(135deg, #6366f1, #a855f7)",
            boxShadow: "0 0 40px rgba(99,102,241,0.3), 0 0 80px rgba(168,85,247,0.15)",
            animation: "bootLogoPulse 1.5s ease-in-out infinite"
          }}>
          
          慧
        </div>
        <div className="text-xs uppercase tracking-[0.3em] font-bold" style={{ color: "rgba(255,255,255,0.3)" }}>
          ZHIHUITI SYSTEM
        </div>
      </div>

      {/* Terminal lines */}
      <div className="w-[480px] max-w-[90vw] font-mono text-xs space-y-1.5">
        {BOOT_LINES.slice(0, visibleLines).map((line, i) =>
        <div
          key={i}
          style={{
            color: line.color,
            opacity: 0,
            animation: "bootLineIn 0.3s ease-out forwards",
            textShadow: `0 0 8px ${line.color}40`
          }}>
          
            <span style={{ color: "rgba(255,255,255,0.15)", marginRight: 8 }}>
              {String(i).padStart(2, "0")}
            </span>
            {line.text}
          </div>
        )}
        {/* Blinking cursor */}
        {visibleLines < BOOT_LINES.length &&
        <span style={{ color: "#6366f1", animation: "bootCursor 0.6s step-end infinite" }}>▌</span>
        }
      </div>

      {/* Progress bar */}
      <div className="mt-8 w-[480px] max-w-[90vw]">
        <div className="w-full h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.05)" }}>
          <div
            className="h-full rounded-full"
            style={{
              width: `${visibleLines / BOOT_LINES.length * 100}%`,
              background: "linear-gradient(90deg, #6366f1, #a855f7)",
              boxShadow: "0 0 12px rgba(99,102,241,0.4)",
              transition: "width 0.4s ease-out"
            }} />
          
        </div>
      </div>
    </div>);

}

export default function ZhihuiTiDashboard() {
  const [data, setData] = useState<typeof DEMO_DATA | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [live, setLive] = useState(true);
  const [showCollision, setShowCollision] = useState(false);
  const [graphFullscreen, setGraphFullscreen] = useState(false);
  const [lodCount, setLodCount] = useState(20);
  const [booted, setBooted] = useState(false);
  const handleBootComplete = useCallback(() => setBooted(true), []);
  const [showZhihuiti, setShowZhihuiti] = useState(true);
  const [showHedgeFund, setShowHedgeFund] = useState(true);

  // Run Goal state
  const [goalInput, setGoalInput] = useState("");
  const [goalRunning, setGoalRunning] = useState(false);

  // Live jobs feed — store as Record<jobId, jobData>
  const [jobsMap, setJobsMap] = useState<Record<string, any>>({});

  // Results panel state
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobResult, setJobResult] = useState<any>(null);
  const [jobResultLoading, setJobResultLoading] = useState(false);

  const handleSelect = useCallback((id: string) => setSelected((prev) => prev === id ? null : id), []);

  const fetchData = useCallback(() => {
    fetch("https://zhihuiti.zeabur.app/api/data").
    then((r) => r.json()).
    then((d) => {setData(d);setLive(true);}).
    catch(() => {setData(DEMO_DATA);setLive(false);});
  }, []);

  // Poll jobs every 5s
  useEffect(() => {
    const fetchJobs = () => {
      fetch("https://zhihuiti.zeabur.app/api/jobs").
      then((r) => r.json()).
      then((d) => {
        if (d && typeof d === "object" && !Array.isArray(d)) {
          setJobsMap(d);
        }
      }).
      catch(() => {});
    };
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  // Poll selected job result until done
  useEffect(() => {
    if (!selectedJobId) {setJobResult(null);return;}
    let cancelled = false;
    const poll = () => {
      setJobResultLoading(true);
      fetch(`https://zhihuiti.zeabur.app/api/job/${selectedJobId}`).
      then((r) => r.json()).
      then((d) => {
        if (cancelled) return;
        setJobResult(d);
        setJobResultLoading(false);
        if (d?.status === "done" || d?.status === "completed") {

          // done, stop polling
        } else {// keep polling
          setTimeout(() => {if (!cancelled) poll();}, 5000);
        }
      }).
      catch(() => {
        if (cancelled) return;
        // fallback: use data from jobsMap
        const fromMap = jobsMap[selectedJobId];
        if (fromMap) setJobResult(fromMap);
        setJobResultLoading(false);
      });
    };
    poll();
    return () => {cancelled = true;};
  }, [selectedJobId]);

  // Derive jobs array for sidebar feed
  const jobs = useMemo(() =>
  Object.entries(jobsMap).map(([id, job]) => ({ id, ...job })),
  [jobsMap]
  );

  const handleRunGoal = useCallback(async () => {
    if (!goalInput.trim() || goalRunning) return;
    setGoalRunning(true);
    try {
      await fetch("https://zhihuiti.zeabur.app/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: goalInput.trim() })
      });
      setGoalInput("");
      fetchData();
    } catch (e) {
      console.error("Run goal failed:", e);
    } finally {
      setGoalRunning(false);
    }
  }, [goalInput, goalRunning, fetchData]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const coreAgents: Agent[] = data?.agents || [];

  // Parse alphaarena agents from API and merge
  const alphaArenaAgents: Agent[] = useMemo(() => {
    const raw = (data as any)?.alphaarena?.agents;
    if (!Array.isArray(raw)) return [];
    return raw.map((a: any) => ({
      id: a.id,
      role: a.name || a.id,
      name: a.name,
      budget: (a.compositeScore || 0.5) * 200,
      avg_score: a.winRate || 0.5,
      alive: true,
      realm: a.type === "algo_bot" ? "central" : "research",
      life_state: "active",
      generation: 0,
      tasks: 0,
      group: (a.type === "algo_bot" ? "zhihuiti" : "hedge_fund") as "zhihuiti" | "hedge_fund",
    }));
  }, [data]);

  const agents: Agent[] = useMemo(() => [...coreAgents, ...alphaArenaAgents], [coreAgents, alphaArenaAgents]);
  const events = useSimulatedFeed(agents);

  // Build sparse economy graph: each agent connects to 2-3 peers (same realm, nearest by score)
  const connections: Connection[] = useMemo(() => {
    const conns: Connection[] = [];
    const types = ["transaction", "investment", "bounty", "employment", "subsidy", "bloodline", "competition"];
    const byRealm: Record<string, Agent[]> = {};
    agents.forEach(a => {
      (byRealm[a.realm] ||= []).push(a);
    });
    Object.values(byRealm).forEach(group => {
      const sorted = [...group].sort((a, b) => b.avg_score - a.avg_score);
      sorted.forEach((a, i) => {
        for (let d = 1; d <= 2; d++) {
          const j = i + d;
          if (j < sorted.length) {
            conns.push({ from: a.id, to: sorted[j].id, type: types[(i + j) % types.length] });
          }
        }
      });
    });
    return conns;
  }, [agents]);

  if (!data) return (
    <div className="min-h-screen flex items-center justify-center text-white" style={{ background: "#0a0a14" }}>
      <div className="animate-pulse text-xl" style={{ color: "#a855f7" }}>Loading 智慧体...</div>
    </div>);


  const selectedAgent = agents.find((a) => a.id === selected);
  const selectedConns = connections.filter((c) => c.from === selected || c.to === selected);

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
  const risk = data.risk || {} as any;

  const econHistory = Array.from({ length: 20 }, (_, i) => ({
    day: i + 1,
    supply: (econ.money_supply || 10000) * (0.85 + Math.sin(i * 0.4) * 0.15 + i * 0.005),
    taxed: (econ.total_taxes_collected || 10) / 15 * (0.6 + Math.random() * 0.8)
  }));

  return (
    <div className="min-h-screen text-white relative" style={{
      background: "linear-gradient(135deg, #0a0a14 0%, #0d0d1a 50%, #0a0f18 100%)",
      fontFamily: "'Inter', system-ui, sans-serif"
    }}>
      {/* Boot sequence overlay */}
      {!booted && <BootSequence onComplete={handleBootComplete} />}
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
        @keyframes hudDash {
          0% { stroke-dashoffset: 0; }
          100% { stroke-dashoffset: -24; }
        }
        @keyframes hudGlow {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.7; }
        }
        @keyframes bootLogoPulse {
          0%, 100% { box-shadow: 0 0 40px rgba(99,102,241,0.3), 0 0 80px rgba(168,85,247,0.15); transform: scale(1); }
          50% { box-shadow: 0 0 60px rgba(99,102,241,0.5), 0 0 120px rgba(168,85,247,0.25); transform: scale(1.05); }
        }
        @keyframes bootLineIn {
          from { opacity: 0; transform: translateX(-12px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes bootCursor {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        .hud-border {
          pointer-events: none;
          position: fixed;
          inset: 0;
          z-index: 9998;
        }
        .hud-corner {
          position: absolute;
          width: 32px;
          height: 32px;
          animation: hudGlow 3s ease-in-out infinite;
        }
        .hud-corner-tl { top: 6px; left: 6px; border-top: 2px solid rgba(99,102,241,0.5); border-left: 2px solid rgba(99,102,241,0.5); }
        .hud-corner-tr { top: 6px; right: 6px; border-top: 2px solid rgba(168,85,247,0.5); border-right: 2px solid rgba(168,85,247,0.5); }
        .hud-corner-bl { bottom: 6px; left: 6px; border-bottom: 2px solid rgba(59,130,246,0.5); border-left: 2px solid rgba(59,130,246,0.5); }
        .hud-corner-br { bottom: 6px; right: 6px; border-bottom: 2px solid rgba(249,115,22,0.5); border-right: 2px solid rgba(249,115,22,0.5); }
      `}</style>
      <div className="crt-overlay" />
      <div className="tron-grid" />
      {/* HUD border */}
      <div className="hud-border">
        <div className="hud-corner hud-corner-tl" />
        <div className="hud-corner hud-corner-tr" />
        <div className="hud-corner hud-corner-bl" />
        <div className="hud-corner hud-corner-br" />
        <svg width="100%" height="100%" style={{ position: "absolute", inset: 0 }}>
          {/* Top edge */}
          <line x1="38" y1="7" x2="99%" y2="7"
          stroke="rgba(99,102,241,0.2)" strokeWidth="1"
          strokeDasharray="8 4" style={{ animation: "hudDash 2s linear infinite" }} />
          {/* Bottom edge */}
          <line x1="38" y1="99.5%" x2="99%" y2="99.5%"
          stroke="rgba(59,130,246,0.2)" strokeWidth="1"
          strokeDasharray="8 4" style={{ animation: "hudDash 2s linear infinite" }} />
          {/* Left edge */}
          <line x1="7" y1="38" x2="7" y2="99%"
          stroke="rgba(99,102,241,0.15)" strokeWidth="1"
          strokeDasharray="6 6" style={{ animation: "hudDash 3s linear infinite" }} />
          {/* Right edge */}
          <line x1="99.5%" y1="38" x2="99.5%" y2="99%"
          stroke="rgba(168,85,247,0.15)" strokeWidth="1"
          strokeDasharray="6 6" style={{ animation: "hudDash 3s linear infinite" }} />
        </svg>
      </div>

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
          {Object.entries(REALM_COLORS).map(([r, c]) =>
          <span key={r} className="px-2 py-1 rounded text-xs" style={{ background: `${c}15`, color: c, border: `1px solid ${c}30` }}>
              {REALM_LABELS[r]?.split(" ")[0]} · {agents.filter((a) => a.realm === r).length}
            </span>
          )}
        </div>
      </div>

      {/* Realm Health Bars */}
      <RealmHealthBars realms={data.realms} agents={data.agents} />

      <div className="flex" style={{ height: "calc(100vh - 97px)" }}>
        {/* Left sidebar */}
        <div className="w-72 p-4 space-y-3 overflow-y-auto" style={{ borderRight: "1px solid rgba(255,255,255,0.05)" }}>
        {/* Run Goal */}
          <div className="pb-3 mb-1" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>🎯 Run Goal</div>
            <div className="flex gap-1.5">
              <input
                type="text"
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRunGoal()}
                placeholder="Enter a goal..."
                disabled={goalRunning}
                className="flex-1 px-2 py-1.5 rounded text-xs font-mono outline-none"
                style={{
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#fff"
                }} />
              
              <button
                onClick={handleRunGoal}
                disabled={goalRunning || !goalInput.trim()}
                className="px-2.5 py-1.5 rounded text-xs font-bold tracking-wide transition-all"
                style={{
                  background: goalRunning ? "rgba(168,85,247,0.3)" : "linear-gradient(135deg, #6366f1, #a855f7)",
                  color: goalRunning ? "rgba(255,255,255,0.5)" : "#fff",
                  cursor: goalRunning || !goalInput.trim() ? "not-allowed" : "pointer",
                  opacity: !goalInput.trim() && !goalRunning ? 0.5 : 1
                }}>
                
                {goalRunning ? "Running..." : "▶ RUN"}
              </button>
            </div>
          </div>

          {/* Live Task Feed */}
          <ResizableWidget defaultHeight={180} minHeight={60} maxHeight={400}>
          <div className="pb-3 mb-1" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>
              📡 Live Task Feed
              <span className="ml-1.5 inline-block w-1.5 h-1.5 rounded-full" style={{ background: "#22c55e", boxShadow: "0 0 6px #22c55e", animation: "bootCursor 1.5s ease-in-out infinite" }} />
            </div>
            <div className="space-y-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
              {jobs.length === 0 ?
              <div className="text-xs py-2 text-center" style={{ color: "rgba(255,255,255,0.2)" }}>No active jobs</div> :

              jobs.slice(0, 10).map((job: any, i: number) => {
                const status = job.status || "unknown";
                const isRunning = status === "running" || status === "pending";
                const statusColor = isRunning ? "#eab308" : status === "completed" || status === "done" ? "#22c55e" : "#ef4444";
                return (
                  <button key={job.id || i} className="w-full flex items-start gap-2 px-2 py-1.5 rounded text-xs text-left transition-colors cursor-pointer hover:bg-white/5"
                  onClick={() => setSelectedJobId(job.id || null)}
                  style={{
                    background: selectedJobId === job.id ? "rgba(99,102,241,0.1)" : "rgba(255,255,255,0.03)",
                    border: selectedJobId === job.id ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent"
                  }}>
                      <span className="mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0" style={{
                      background: statusColor,
                      boxShadow: isRunning ? `0 0 6px ${statusColor}` : "none",
                      animation: isRunning ? "bootCursor 1s ease-in-out infinite" : "none"
                    }} />
                      <div className="flex-1 min-w-0">
                        <div className="truncate" style={{ color: "rgba(255,255,255,0.7)" }}>
                          {job.goal || job.task || job.name || `Job #${i + 1}`}
                        </div>
                        <div className="font-mono text-[10px] mt-0.5" style={{ color: statusColor }}>
                          {status.toUpperCase()}
                        </div>
                      </div>
                    </button>);

              })
              }
            </div>
          </div>
          </ResizableWidget>

          <ResizableWidget minHeight={50} maxHeight={300}>
            <Stat label="Money Supply" value={`${(econ.money_supply || 0).toLocaleString()} ◆`} sub={`Treasury: ${(econ.treasury_balance || 0).toLocaleString()}`} color="#eab308" />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={300}>
            <Stat label="Tasks Completed" value={mem.total_tasks || 0} sub={`Avg score: ${(mem.avg_task_score || 0).toFixed(2)}`} color="#22c55e" />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={300}>
            <Stat label="Gene Pool" value={mem.gene_pool_size || 0} sub={`${bl.alive_genes || 0} alive · Gen ${bl.max_generation || 0}`} color="#a855f7" />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={300}>
            <Stat label="Auctions Won" value={au.total_auctions || 0} sub={`Saved ${(au.total_savings || 0).toFixed(0)} ◆`} color="#3b82f6" />
          </ResizableWidget>

          {/* Risk Manager */}
          <ResizableWidget minHeight={50} maxHeight={400}>
            <div className="p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
              <div className="text-xs uppercase tracking-wider mb-2 flex items-center gap-2" style={{ color: "rgba(255,255,255,0.4)" }}>
                🛡️ Risk Manager
                <span
                  className="w-2 h-2 rounded-full"
                  style={{
                    background: risk.halted ? "#ef4444" : "#22c55e",
                    boxShadow: `0 0 6px ${risk.halted ? "#ef4444" : "#22c55e"}`,
                  }}
                />
                <span className="text-[10px] font-mono" style={{ color: risk.halted ? "#ef4444" : "#22c55e" }}>
                  {risk.halted ? "HALTED" : "ACTIVE"}
                </span>
              </div>
              {[
                ["Peak Equity", `${(risk.peak_equity || 0).toLocaleString()} ◆`, "#eab308"],
                ["Current Drawdown", `${(risk.current_drawdown || 0).toFixed(1)}%`, (risk.current_drawdown || 0) > 10 ? "#ef4444" : "#22c55e"],
                ["Trades Today", risk.trades_today || 0, "#60a5fa"],
                ["Max Drawdown Limit", `${(risk.max_drawdown_limit || 0).toFixed(1)}%`, "#a78bfa"],
              ].map(([label, value, color], i) => (
                <div key={i} className="flex justify-between text-xs py-0.5">
                  <span style={{ color: "rgba(255,255,255,0.5)" }}>{label as string}</span>
                  <span className="font-mono" style={{ color: color as string }}>{value as string | number}</span>
                </div>
              ))}
            </div>
          </ResizableWidget>

          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="🔍" title="3-Layer Inspection" items={[
          ["Inspections", ins.total_inspections || 0],
          ["Accepted", ins.accepted || 0, "#22c55e"],
          ["Rejected", ins.rejected || 0, "#ef4444"],
          ["Avg Score", (ins.avg_score || 0).toFixed(2)]]
          } />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="🚨" title="Circuit Breaker" items={[
          ["Trips", cb.total_trips || 0, cb.total_trips > 0 ? "#ef4444" : "#22c55e"],
          ["Laws Active", cb.laws_active || 0]]
          } />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="👁" title="Behavioral Detection" items={[
          ["Violations", bh.total_violations || 0, bh.total_violations > 0 ? "#ef4444" : "#22c55e"],
          ["Agents Flagged", bh.agents_flagged || 0]]
          } />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="💳" title="Lending" items={[
          ["Active", ln.active || 0],
          ["Defaulted", ln.defaulted || 0, ln.defaulted > 0 ? "#ef4444" : "#fff"]]
          } />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="💱" title="Market / Futures" items={[
          ["Orders", mk.total_orders || 0],
          ["Trades", mk.total_trades || 0],
          ["Stakes", ft.active || 0]]
          } />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="⚖️" title="Arbitration" items={[
          ["Disputes", ar.total_disputes || 0],
          ["Resolved", ar.resolved || 0, "#22c55e"]]
          } />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="🏭" title="Factory" items={[
          ["Shipped", fa.shipped || 0, "#22c55e"],
          ["QA Fail", fa.qa_fail || 0, fa.qa_fail > 0 ? "#ef4444" : "#fff"]]
          } />
          </ResizableWidget>
          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="📨" title="Agent Messaging" items={[
          ["Messages", msg.total_messages || 0],
          ["Unread", msg.unread || 0, msg.unread > 0 ? "#eab308" : "#fff"]]
          } />
          </ResizableWidget>

          {goals.length > 0 &&
          <ResizableWidget minHeight={50} maxHeight={400}>
          <SystemCard icon="📚" title="Goal History" items={
          goals.slice(0, 4).map((g) => [
          (g.goal || "").slice(0, 22) + ((g.goal?.length || 0) > 22 ? "..." : ""),
          (g.avg_score || 0).toFixed(2),
          (g.avg_score || 0) >= 0.8 ? "#22c55e" : "#eab308"] as
          [string, string, string])
          } />
          </ResizableWidget>
          }

          {/* Connection legend */}
          <div className="pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Relationship Types</div>
            {Object.entries(CONN_COLORS).map(([type, color]) =>
            <div key={type} className="flex items-center gap-2 text-xs py-0.5">
                <span className="w-3 h-0.5 rounded" style={{ background: color }} />
                <span style={{ color: "rgba(255,255,255,0.5)" }}>{type}</span>
              </div>
            )}
          </div>

          {/* Agent list */}
          <div className="pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>Agents</div>
            {[...agents].sort((a, b) => b.budget - a.budget).map((a) =>
            <button key={a.id} onClick={() => handleSelect(a.id)}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs text-left hover:bg-white/5 transition-colors cursor-pointer"
            style={{ background: selected === a.id ? "rgba(255,255,255,0.08)" : "transparent" }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: a.alive ? REALM_COLORS[a.realm] : "#555" }} />
                <span className="flex-1 truncate text-white">{ROLE_ICONS[a.role] || "🤖"} {a.role}</span>
                <span className="font-mono text-[10px]" style={{ color: "rgba(255,255,255,0.3)" }}>{a.budget.toFixed(0)}◆</span>
              </button>
            )}
          </div>
        </div>

        {/* Center — 3D Graph */}
        {(() => {
          const graphContent =
          <div className={`flex-1 flex flex-col relative ${graphFullscreen ? "" : ""}`}
          style={graphFullscreen ? { position: "fixed", inset: 0, zIndex: 9999, background: "#08080f" } : undefined}>
              <ResizableWidget defaultHeight={400} minHeight={150} maxHeight={800} className="flex-1 relative">
                <ThreeGraph agents={agents} connections={connections} onSelect={handleSelect} selectedId={selected} events={events} showZhihuiti={showZhihuiti} showHedgeFund={showHedgeFund} lodCount={lodCount} />
                {/* Fullscreen toggle */}
                <button
                onClick={() => setGraphFullscreen((f) => !f)}
                className="absolute top-3 right-3 z-20 w-8 h-8 flex items-center justify-center rounded-md text-sm cursor-pointer transition-all hover:scale-105 active:scale-95"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "rgba(255,255,255,0.5)",
                  backdropFilter: "blur(8px)"
                }}
                title={graphFullscreen ? "Exit fullscreen" : "Fullscreen"}>
                
                  {graphFullscreen ? "✕" : "⛶"}
                </button>
                <div className="absolute bottom-4 left-4 flex items-center gap-3 z-10">
                  <span className="text-xs" style={{ color: "rgba(255,255,255,0.15)" }}>drag to rotate · click node for details</span>
                  <button
                    onClick={() => setShowZhihuiti(s => !s)}
                    className="text-[10px] px-2 py-1 rounded cursor-pointer transition-colors"
                    style={{
                      background: showZhihuiti ? "rgba(234,179,8,0.15)" : "rgba(255,255,255,0.05)",
                      color: showZhihuiti ? "#eab308" : "rgba(255,255,255,0.3)",
                      border: `1px solid ${showZhihuiti ? "rgba(234,179,8,0.3)" : "rgba(255,255,255,0.08)"}`
                    }}>
                    🟡 ZhihuiTi ({alphaArenaAgents.filter(a => a.group === "zhihuiti").length})
                  </button>
                  <button
                    onClick={() => setShowHedgeFund(s => !s)}
                    className="text-[10px] px-2 py-1 rounded cursor-pointer transition-colors"
                    style={{
                      background: showHedgeFund ? "rgba(59,130,246,0.15)" : "rgba(255,255,255,0.05)",
                      color: showHedgeFund ? "#3b82f6" : "rgba(255,255,255,0.3)",
                      border: `1px solid ${showHedgeFund ? "rgba(59,130,246,0.3)" : "rgba(255,255,255,0.08)"}`
                    }}>
                    🔵 Hedge Fund ({alphaArenaAgents.filter(a => a.group === "hedge_fund").length})
                  </button>
                  <button
                  onClick={() => setShowCollision((s) => !s)}
                  className="text-[10px] px-2 py-1 rounded cursor-pointer transition-colors"
                  style={{
                    background: showCollision ? "rgba(244,114,182,0.15)" : "rgba(255,255,255,0.05)",
                    color: showCollision ? "#f472b6" : "rgba(255,255,255,0.4)",
                    border: `1px solid ${showCollision ? "rgba(244,114,182,0.3)" : "rgba(255,255,255,0.08)"}`
                  }}>
                    ⚛️ Collision Engine
                  </button>
                  <div className="flex items-center gap-1 ml-2" style={{ borderLeft: "1px solid rgba(255,255,255,0.08)", paddingLeft: 8 }}>
                    <span className="text-[10px]" style={{ color: "rgba(255,255,255,0.3)" }}>Show:</span>
                    {[{ label: "Top 20", value: 20 }, { label: "Top 50", value: 50 }, { label: "All", value: -1 }].map(opt => (
                      <button
                        key={opt.value}
                        onClick={() => setLodCount(opt.value)}
                        className="text-[10px] px-1.5 py-0.5 rounded cursor-pointer transition-colors"
                        style={{
                          background: lodCount === opt.value ? "rgba(167,139,250,0.2)" : "rgba(255,255,255,0.04)",
                          color: lodCount === opt.value ? "#a78bfa" : "rgba(255,255,255,0.3)",
                          border: `1px solid ${lodCount === opt.value ? "rgba(167,139,250,0.4)" : "rgba(255,255,255,0.08)"}`
                        }}
                      >{opt.label}</button>
                    ))}
                  </div>
                </div>
                {selectedAgent &&
              <AgentDetail agent={selectedAgent} connections={selectedConns} agents={agents} onClose={() => setSelected(null)} onSelect={handleSelect} />
              }
                <CollisionEngine show={showCollision} onClose={() => setShowCollision(false)} />
                {/* Minimap */}
                <div className="absolute top-3 left-3 z-10 rounded-lg overflow-hidden" style={{
                width: 120, height: 120,
                background: "rgba(5,5,15,0.85)",
                border: "1px solid rgba(99,102,241,0.2)",
                boxShadow: "0 0 16px rgba(99,102,241,0.08)"
              }}>
                  <div className="text-[8px] uppercase tracking-widest px-2 pt-1.5" style={{ color: "rgba(255,255,255,0.25)" }}>Minimap</div>
                  <svg width="120" height="104" viewBox="-12 -12 24 24" style={{ display: "block" }}>
                    {(() => {
                    const total = agents.length;
                    const GROUP_COLORS_MAP: Record<string, string> = { zhihuiti: "#eab308", hedge_fund: "#3b82f6" };
                    return agents.map((a, i) => {
                      const phi = Math.acos(1 - 2 * (i + 0.5) / total);
                      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
                      const r = 3 + (i / total) * 6;
                      const cx = Math.sin(phi) * Math.cos(theta) * r;
                      const cy = Math.sin(phi) * Math.sin(theta) * r;
                      const isSelected = a.id === selected;
                      const dotColor = a.group ? GROUP_COLORS_MAP[a.group] : REALM_COLORS[a.realm];
                      return (
                        <g key={a.id}>
                            {isSelected &&
                          <circle cx={cx} cy={cy} r={1.2} fill="none"
                          stroke={dotColor} strokeWidth={0.1} opacity={0.5}>
                                <animate attributeName="r" values="0.8;1.4;0.8" dur="1.5s" repeatCount="indefinite" />
                              </circle>
                          }
                            <circle cx={cx} cy={cy}
                            r={isSelected ? 0.5 : 0.35}
                            fill={a.alive ? dotColor : "#555"}
                            opacity={a.alive ? 0.9 : 0.4}
                            style={{ cursor: "pointer" }}
                            onClick={() => handleSelect(a.id)} />
                          </g>);
                    });
                  })()}
                  </svg>
                </div>
              </ResizableWidget>

              {/* Bottom charts — hidden in fullscreen */}
              {!graphFullscreen &&
            <ResizableWidget defaultHeight={176} minHeight={80} maxHeight={500}>
            <div className="flex gap-4 px-4 pb-3 h-full" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
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
                      {[...agents].filter((a) => a.alive).sort((a, b) => b.avg_score - a.avg_score).slice(0, 6).map((a, i) =>
                  <div key={a.id} className="flex items-center gap-2 text-xs">
                          <span className="w-4 text-right font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>{i + 1}</span>
                          <span className="w-2 h-2 rounded-full" style={{ background: REALM_COLORS[a.realm] }} />
                          <span className="flex-1 text-white truncate">{a.role}</span>
                          <span className="font-mono" style={{ color: a.avg_score >= 0.8 ? "#22c55e" : "#eab308" }}>
                            {a.avg_score.toFixed(2)}
                          </span>
                        </div>
                  )}
                    </div>
                  </div>
                </div>
            </ResizableWidget>
            }

              {/* Cross-Project Status */}
              {!graphFullscreen &&
              <div className="px-4 py-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>🌐 Cross-Project</div>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { name: "AlphaArena", icon: "⚔️", alive: alphaArenaAgents.length > 0, agents: alphaArenaAgents.filter(a => a.alive).length, tasks: alphaArenaAgents.reduce((s, a) => s + a.tasks, 0), score: alphaArenaAgents.length > 0 ? (alphaArenaAgents.reduce((s, a) => s + a.avg_score, 0) / alphaArenaAgents.length).toFixed(2) : "—", color: "#a855f7", offline: alphaArenaAgents.length === 0 },
                    { name: "CriticAI", icon: "🧠", alive: false, agents: 0, tasks: 0, score: "—", color: "#3b82f6", offline: true },
                    { name: "HeartAI", icon: "❤️", alive: !!(data as any)?.heartai?.online, agents: (data as any)?.heartai?.total || 0, tasks: 0, score: (data as any)?.heartai?.agents?.length > 0 ? ((data as any).heartai.agents.reduce((s: number, a: any) => s + (a.avg_score || 0), 0) / (data as any).heartai.agents.length).toFixed(2) : "—", color: "#ef4444", offline: !(data as any)?.heartai?.online },
                    { name: "zhihuiti", icon: "🧬", alive: live, agents: coreAgents.filter(a => a.alive).length, tasks: mem.total_tasks || 0, score: (ins.avg_score || 0).toFixed(2), color: "#eab308", offline: !live },
                  ].map((proj) => (
                    <div key={proj.name} className="p-2.5 rounded-lg" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: proj.alive ? "#22c55e" : "#ef4444", boxShadow: `0 0 6px ${proj.alive ? "#22c55e" : "#ef4444"}` }} />
                        <span className="text-[11px] font-medium text-white truncate">{proj.icon} {proj.name}</span>
                      </div>
                      {proj.offline ? (
                        <div className="text-[10px] font-mono py-1 text-center" style={{ color: "rgba(255,255,255,0.2)" }}>OFFLINE</div>
                      ) : (
                        [
                          ["Agents", proj.agents, proj.color],
                          ["Tasks", proj.tasks, "#fff"],
                          ["Score", proj.score, parseFloat(String(proj.score)) >= 0.8 ? "#22c55e" : "#eab308"],
                        ].map(([label, value, c]) => (
                          <div key={String(label)} className="flex justify-between text-[10px] py-0.5">
                            <span style={{ color: "rgba(255,255,255,0.4)" }}>{label as string}</span>
                            <span className="font-mono" style={{ color: c as string }}>{value as string | number}</span>
                          </div>
                        ))
                      )}
                    </div>
                  ))}
                </div>
              </div>
              }

              {/* AlphaArena Leaderboard — hidden in fullscreen */}
              {!graphFullscreen && agents.length > 0 &&
            <ResizableWidget defaultHeight={220} minHeight={80} maxHeight={600}>
            <div className="px-4 pb-4" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                  <div className="pt-3 pb-2 flex items-center gap-2">
                    <span style={{ fontSize: 14 }}>🏟️</span>
                    <span className="text-xs uppercase tracking-widest font-semibold" style={{ color: "#a78bfa" }}>AlphaArena Leaderboard</span>
                  </div>
                  <LeaderboardTable agents={agents} handleSelect={handleSelect} REALM_COLORS={REALM_COLORS} />
                </div>
            </ResizableWidget>
            }
            </div>;

          return graphFullscreen ? createPortal(graphContent, document.body) : graphContent;
        })()}

        {/* Right — Results Panel or Live Task Feed */}
        {selectedJobId ?
        <ResultsPanel jobId={selectedJobId} result={jobResult} loading={jobResultLoading} onClose={() => setSelectedJobId(null)} /> :

        <TaskFeed events={events} onSelectAgent={handleSelect} />
        }
      </div>
    </div>);

}