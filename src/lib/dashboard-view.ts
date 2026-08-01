export interface AgentListRecord {
  id: string;
  role: string;
  realm: string;
  budget: number;
  alive: boolean;
}

export interface AgentListOptions {
  query: string;
  realm: string;
  limit?: number;
}

export function filterAgentList<T extends AgentListRecord>(agents: T[], options: AgentListOptions): T[] {
  const query = options.query.trim().toLowerCase();
  const filtered = agents
    .filter((agent) => options.realm === "all" || agent.realm === options.realm)
    .filter((agent) => {
      if (!query) return true;
      return `${agent.id} ${agent.role} ${agent.realm}`.toLowerCase().includes(query);
    })
    .sort((a, b) => b.budget - a.budget);

  return options.limit === undefined ? filtered : filtered.slice(0, options.limit);
}

export function clampRatio(value: number): number {
  return Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
}

export function formatBudgetStatus(remaining: number, allocated: number): string {
  if (remaining < 0) return `${Math.abs(remaining).toLocaleString()} over budget`;
  return `${remaining.toLocaleString()}/${allocated.toLocaleString()} ◆`;
}

export function formatFreshness(lastUpdatedAt: number | null, now = Date.now()): string {
  if (!lastUpdatedAt) return "not updated";
  const ageSeconds = Math.max(0, Math.floor((now - lastUpdatedAt) / 1000));
  if (ageSeconds < 5) return "updated now";
  if (ageSeconds < 60) return `updated ${ageSeconds}s ago`;
  return `updated ${Math.floor(ageSeconds / 60)}m ago`;
}
