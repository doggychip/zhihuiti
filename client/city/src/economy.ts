/**
 * Autonomous agent economy — building, earning, competition, circuit breaker.
 *
 * Runs as a tick-based simulation layered on top of the visual city.
 */

import type { CityAgent } from "./agent";
import type { WorldMap } from "./worldgen";
import { TileType } from "./worldgen";
import { TILE } from "./sprites";

// ── Building types ──

export type BuildingType = "house" | "market" | "farm" | "tower" | "park";

export interface PlacedBuilding {
  type: BuildingType;
  tx: number;         // tile x
  ty: number;         // tile y
  ownerId: string;    // agent who built it
  buildTime: number;  // performance.now() when placed
  isCommunityProject?: boolean;
}

export interface StakingInfo {
  lockedBudget: number;
  lockUntil: number;
  multiplier: number;
}

export interface CommunityFund {
  id: string;
  type: BuildingType;
  tx: number;
  ty: number;
  goal: number;
  current: number;
  contributors: string[];
}

export const BUILDING_COST: Record<BuildingType, number> = {
  house: 20,
  market: 30,
  farm: 25,
  tower: 50,
  park: 15,
};

export const BUILDING_EMOJI: Record<BuildingType, string> = {
  house: "🏠",
  market: "🏪",
  farm: "🌾",
  tower: "🗼",
  park: "🌳",
};

// ── Role → preferred building ──

const ROLE_PREFERRED: Record<string, BuildingType> = {
  researcher: "tower",
  analyst: "tower",
  coder: "house",
  trader: "market",
  strategist: "park",
  coordinator: "house",
  auditor: "tower",
  causal_reasoner: "park",
  mutualist: "park",
  darwinian: "tower",
  hybrid: "market",
  custom: "house",
};

export function preferredBuilding(role: string): BuildingType {
  return ROLE_PREFERRED[role] ?? "house";
}

// ── Economy state ──

export interface AgentStats {
  buildingsBuilt: number;
  totalEarned: number;
  timesDormant: number;
}

/** Pending build intent — used for competition resolution. */
interface BuildIntent {
  agentId: string;
  tx: number;
  ty: number;
  type: BuildingType;
  budget: number;
}

export class CityEconomy {
  buildings: PlacedBuilding[] = [];
  agentStats = new Map<string, AgentStats>();

  /** Set of "tx,ty" keys where buildings exist. */
  private _occupied = new Set<string>();

  /** Pending build intents for this tick (resolved together for competition). */
  private _intents: BuildIntent[] = [];

  /** Tiles blocked by worldgen decorations or paths. */
  private _blocked = new Set<string>();

  // Triple Evolution: Finance & Lineage
  staking = new Map<string, StakingInfo>();
  funds: CommunityFund[] = [];
  futures = new Map<string, { tx: number, ty: number, bid: number, agentId: string }>();

  private world: WorldMap | null = null;

  setWorld(w: WorldMap) {
    this.world = w;
    this._blocked.clear();

    // Mark water, path, and decoration tiles as blocked
    for (let r = 0; r < w.rows; r++) {
      for (let c = 0; c < w.cols; c++) {
        const t = w.tiles[r][c];
        if (t === TileType.WATER || t === TileType.PATH) {
          this._blocked.add(`${c},${r}`);
        }
      }
    }
    for (const d of w.decorations) {
      // Block a 2x2 area for trees, 5x4 for houses, 1x1 for small items
      const size = d.type === "house" ? [5, 4] :
                   (d.type === "tree_green" || d.type === "tree_pink") ? [2, 2] :
                   [1, 1];
      for (let dy = 0; dy < size[1]; dy++) {
        for (let dx = 0; dx < size[0]; dx++) {
          this._blocked.add(`${d.tx + dx},${d.ty + dy}`);
        }
      }
    }
  }

  private ensureStats(id: string): AgentStats {
    if (!this.agentStats.has(id)) {
      this.agentStats.set(id, { buildingsBuilt: 0, totalEarned: 0, timesDormant: 0 });
    }
    return this.agentStats.get(id)!;
  }

  /** Find a buildable road-adjacent grass tile. Prefers nearby. */
  findBuildSite(agent: CityAgent): { tx: number; ty: number } | null {
    if (!this.world) return null;

    // Use the pre-computed road-adjacent grass list
    const candidates = this.world.roadAdjacentGrass.filter(
      s => this.isBuildable(s.tx, s.ty)
    );
    if (candidates.length === 0) return null;

    // Pick one of the 8 nearest to the agent
    const ax = Math.floor(agent.x / TILE);
    const ay = Math.floor(agent.y / TILE);
    candidates.sort((a, b) => {
      const da = Math.abs(a.tx - ax) + Math.abs(a.ty - ay);
      const db = Math.abs(b.tx - ax) + Math.abs(b.ty - ay);
      return da - db;
    });
    const pool = candidates.slice(0, 8);
    return pool[Math.floor(Math.random() * pool.length)];
  }

  private isBuildable(tx: number, ty: number): boolean {
    if (!this.world) return false;
    if (tx < 4 || ty < 4 || tx >= this.world.cols - 4 || ty >= this.world.rows - 4) return false;
    const key = `${tx},${ty}`;
    if (this._blocked.has(key)) return false;
    if (this._occupied.has(key)) return false;
    const tile = this.world.tiles[ty]?.[tx];
    return tile === TileType.GRASS || tile === TileType.GRASS_VAR1 || tile === TileType.GRASS_VAR2;
  }

  submitBuildIntent(agent: CityAgent, tx: number, ty: number, type: BuildingType) {
    let budget = agent.budget;
    // Leveraged budget for Darwinian agents (debt)
    if (agent.role === "darwinian") {
      const leverage = 20; // Darwinian agents can borrow up to 20 budget
      budget += leverage;
      agent.debt += leverage;
    }
    this._intents.push({
      agentId: agent.id,
      tx, ty, type,
      budget,
    });
  }

  /** Agent stakes budget for influence. */
  stakeBudget(agent: CityAgent, amount: number, durationTicks: number) {
    if (agent.budget < amount) return;
    agent.budget -= amount;
    this.staking.set(agent.id, {
      lockedBudget: amount,
      lockUntil: performance.now() + durationTicks * 1000, // mock ticks
      multiplier: 1 + (amount / 100)
    });
  }

  /** Mutualists create/contribute to community funds. */
  contributeToFund(agent: CityAgent, tx: number, ty: number, type: BuildingType, amount: number) {
    let fund = this.funds.find(f => f.tx === tx && f.ty === ty);
    if (!fund) {
      fund = {
        id: `fund_${tx}_${ty}`,
        type, tx, ty,
        goal: BUILDING_COST[type],
        current: 0,
        contributors: []
      };
      this.funds.push(fund);
    }
    const contribution = Math.min(amount, agent.budget);
    agent.budget -= contribution;
    fund.current += contribution;
    if (!fund.contributors.includes(agent.id)) fund.contributors.push(agent.id);

    if (fund.current >= fund.goal) {
      // Build community project
      this.buildings.push({
        type: fund.type,
        tx: fund.tx,
        ty: fund.ty,
        ownerId: "community",
        buildTime: performance.now(),
        isCommunityProject: true
      });
      this._occupied.add(`${fund.tx},${fund.ty}`);
      this.funds = this.funds.filter(f => f.id !== fund!.id);
    }
  }

  /**
   * Resolve all build intents for this tick.
   * Returns array of { winnerId, loserId[] } for competition feedback.
   */
  resolveBuildIntents(agents: CityAgent[]): { built: string[]; rejected: string[] } {
    const byTile = new Map<string, BuildIntent[]>();

    for (const intent of this._intents) {
      const key = `${intent.tx},${intent.ty}`;
      if (!byTile.has(key)) byTile.set(key, []);
      byTile.get(key)!.push(intent);
    }

    const built: string[] = [];
    const rejected: string[] = [];

    const agentMap = new Map(agents.map(a => [a.id, a]));

    for (const [, intents] of byTile) {
      // Sort by budget descending — highest budget wins
      intents.sort((a, b) => b.budget - a.budget);

      const winner = intents[0];
      const agent = agentMap.get(winner.agentId);
      if (!agent) continue;

      const cost = BUILDING_COST[winner.type];
      if (agent.budget < cost) continue;

      // Check tile is still buildable
      if (!this.isBuildable(winner.tx, winner.ty)) continue;

      // Build!
      agent.budget -= cost;
      const building: PlacedBuilding = {
        type: winner.type,
        tx: winner.tx,
        ty: winner.ty,
        ownerId: agent.id,
        buildTime: performance.now(),
      };
      this.buildings.push(building);
      this._occupied.add(`${winner.tx},${winner.ty}`);

      const stats = this.ensureStats(agent.id);
      stats.buildingsBuilt++;
      built.push(agent.id);

      // Losers
      for (let i = 1; i < intents.length; i++) {
        rejected.push(intents[i].agentId);
      }
    }

    this._intents = [];
    return { built, rejected };
  }

  /** Role-specific fitness (average budget of alive agents in that role). */
  roleFitness = new Map<string, number>();

  /** Earning tick: agents near buildings earn budget. */
  earnTick(agents: CityAgent[]) {
    // 1. Update Global Fitness Bridge
    const fitnessSum = new Map<string, number>();
    const fitnessCount = new Map<string, number>();
    for (const a of agents) {
      if (!a.alive) continue;
      fitnessSum.set(a.role, (fitnessSum.get(a.role) ?? 0) + a.budget);
      fitnessCount.set(a.role, (fitnessCount.get(a.role) ?? 0) + 1);
    }
    for (const [role, sum] of fitnessSum) {
      this.roleFitness.set(role, sum / (fitnessCount.get(role) || 1));
    }

    // Lineage Tracking & Purge
    const lineages = new Map<string, CityAgent[]>();
    for (const a of agents) {
      if (!a.alive) continue;
      const rootId = a.parentIds.length > 0 ? a.parentIds[0] : a.id;
      if (!lineages.has(rootId)) lineages.set(rootId, []);
      lineages.get(rootId)!.push(a);
    }

    for (const [rootId, members] of lineages) {
      const avgTruth = members.reduce((sum, m) => sum + m.truthfulness, 0) / members.length;
      if (avgTruth < 0.3 && members.length > 3) {
        // Trigger "Bloodline Purge" (诛七族)
        for (const m of members) {
          m.alive = false;
          m.purging = true; // Visual vortex effect handled by renderer
          this.agentStats.delete(m.id);
        }
      }
    }

    // 2. Symmetric Matching & Role Bonuses
    for (const agent of agents) {
      if (agent.dormant || !agent.alive || agent.reflectionState) continue;

      const atx = Math.floor(agent.x / TILE);
      const aty = Math.floor(agent.y / TILE);
      const pref = preferredBuilding(agent.role);

      let earned = 0;
      const nearbyBuildings = this.buildings.filter(b => {
        const dx = Math.abs(b.tx - atx);
        const dy = Math.abs(b.ty - aty);
        return dx <= 3 && dy <= 3;
      });

      const uniqueTypes = new Set(nearbyBuildings.map(b => b.type));
      const othersBuildings = nearbyBuildings.filter(b => b.ownerId !== agent.id);

      // Multiplier from staking
      const multiplier = this.staking.get(agent.id)?.multiplier ?? 1.0;

      // Base earnings
      for (const b of nearbyBuildings) {
        earned += (b.type === pref) ? (3 * multiplier) : (1 * multiplier);
      }

      // Information Entropy Penalty (Novelty Check)
      // Check if last thought was a repeat of any previous thoughts
      if (agent.recentThoughts.length > 1) {
          const lastThought = agent.recentThoughts[agent.recentThoughts.length - 1];
          const isRepeat = agent.recentThoughts.slice(0, -1).some(t => t === lastThought);
          if (isRepeat) {
              earned *= 0.5; // reduced by 50%
          }
      }

      // Symmetric Matching / Role Logic
      if (agent.role === "mutualist") {
        // Collaboration bonus: +2 for every building owned by someone else nearby
        earned += othersBuildings.length * 2;
        // Community fund contribution (mutualist logic)
        if (agent.budget > 10) {
          const site = this.findBuildSite(agent);
          if (site) {
            this.contributeToFund(agent, site.tx, site.ty, "park", 5);
          }
        }
      } else if (agent.role === "darwinian") {
        // Dominance bonus: +5 if they own the most buildings in this 7x7 area
        const myCount = nearbyBuildings.filter(b => b.ownerId === agent.id).length;
        if (myCount > 0 && myCount >= (nearbyBuildings.length - myCount)) {
          earned += 5;
        }
        // Competition tax: -1 for every competing building
        earned -= othersBuildings.length;
        // Darwinian leveraged budget logic (futures bid logic)
        if (agent.budget > 5) {
          const site = this.findBuildSite(agent);
          if (site) {
            this.futures.set(`${site.tx},${site.ty}`, { tx: site.tx, ty: site.ty, bid: agent.budget + agent.debt, agentId: agent.id });
          }
        }
      } else if (agent.role === "hybrid") {
        // Adaptation bonus: scales with diversity of nearby buildings
        earned += uniqueTypes.size * 2;
      }

      // Debt repayment for Darwinian agents
      if (agent.debt > 0) {
        const repay = Math.min(earned * 0.2, agent.debt);
        agent.debt -= repay;
        earned -= repay;
      }

      if (earned > 0) {
        agent.budget += earned;
        const stats = this.ensureStats(agent.id);
        stats.totalEarned += earned;
      }
    }
  }

  /** Get top 5 agents by buildings built (tie-break by totalEarned). */
  getLeaderboard(): { id: string; stats: AgentStats }[] {
    return [...this.agentStats.entries()]
      .map(([id, stats]) => ({ id, stats }))
      .sort((a, b) =>
        b.stats.buildingsBuilt - a.stats.buildingsBuilt ||
        b.stats.totalEarned - a.stats.totalEarned
      )
      .slice(0, 5);
  }

  /** Get building at a specific tile (for rendering). */
  getBuildingAt(tx: number, ty: number): PlacedBuilding | undefined {
    return this.buildings.find(b => b.tx === tx && b.ty === ty);
  }
}
