const BASE = import.meta.env.VITE_API_URL ?? "https://agentscity.zeabur.app";

export interface AgentData {
  id: string;
  role: string;
  budget: number;
  depth: number;
  avg_score: number;
  alive: number;
  created_at: string;
}

export interface StatsData {
  agents: { total: number; alive: number };
  tasks: { total: number; completed: number; failed: number };
  transactions: number;
  roles: { role: string; count: number; alive: number; avg_score: number }[];
}

export async function fetchAgents(): Promise<AgentData[]> {
  const r = await fetch(`${BASE}/api/agents`);
  const d = await r.json();
  
  // 🧪 Mock: Inject evolutionary roles for testing
  const evoRoles = ["mutualist", "darwinian", "hybrid", "critic", "cold_logic", "warm_soul"];
  return d.agents.map((a: AgentData) => {
    if (a.role === "custom" || (a.role === "strategist" && Math.random() > 0.5)) {
      const idx = Math.floor(Math.random() * evoRoles.length);
      return { ...a, role: evoRoles[idx] };
    }
    return a;
  });
}

export async function fetchStats(): Promise<StatsData> {
  const r = await fetch(`${BASE}/api/stats`);
  return r.json();
}
