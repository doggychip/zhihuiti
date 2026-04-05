/**
 * Goal Runner — the competition engine.
 *
 * Every cycle:
 * 1. Pick an open goal
 * 2. Match eligible agents by category
 * 3. Agents bid (budget-aware) and compete
 * 4. Score each competitor (simulated based on agent fitness)
 * 5. Winner gets reward, losers learn
 * 6. Top performers may spawn (breed) new agents
 * 7. Stale agents get culled
 */
import { randomUUID } from "crypto";
import { eq, and } from "drizzle-orm";
import { db } from "../db";
import {
  goals,
  goalCompetitions,
  zhAgents,
  agentLogs,
  agentMetrics,
} from "@shared/schema";
import { log } from "../index";

// ─── Constants ──────────────────────────────────────────
const MIN_BID = 2;
const MAX_BID = 20;
const MIN_COMPETITORS = 2;
const SPAWN_THRESHOLD = 0.8; // score above this triggers spawn
const CULL_THRESHOLD = 0.25; // score below this → agent gets paused
const DIFFICULTY_MULTIPLIER: Record<string, number> = {
  easy: 1.0,
  medium: 1.5,
  hard: 2.5,
};

// Map goal categories to eligible agent types
const CATEGORY_AGENT_MAP: Record<string, string[]> = {
  trading: ["trading"],
  research: ["analytics", "trading"],
  social: ["social"],
  analytics: ["analytics", "trading"],
  coding: ["analytics"],
  strategy: ["trading", "analytics"],
};

// ─── Core Loop ──────────────────────────────────────────

async function runGoalCycle() {
  try {
    // 1. Pick an open goal
    const openGoals = await db
      .select()
      .from(goals)
      .where(eq(goals.status, "open"));

    if (openGoals.length === 0) {
      // Recycle: reset oldest completed goals back to open
      await recycleGoals();
      return;
    }

    // Pick a random open goal
    const goal = openGoals[Math.floor(Math.random() * openGoals.length)];
    log(`Goal cycle: "${goal.title}" [${goal.category}/${goal.difficulty}]`, "goal-runner");

    // 2. Mark as in_progress
    await db.update(goals).set({ status: "in_progress" }).where(eq(goals.id, goal.id));

    // 3. Find eligible agents
    const allAgents = await db.select().from(zhAgents);
    const eligibleTypes = CATEGORY_AGENT_MAP[goal.category] ?? [];
    const eligible = allAgents.filter(
      (a) => a.status === "active" && eligibleTypes.includes(a.type),
    );

    if (eligible.length < MIN_COMPETITORS) {
      // Not enough agents — spawn one to fill the gap
      log(`Only ${eligible.length} eligible agents for "${goal.title}", spawning to fill`, "goal-runner");
      const spawned = await spawnAgent(goal.category, `Spawned for: ${goal.title}`);
      if (spawned) eligible.push(spawned);

      if (eligible.length < 1) {
        await db.update(goals).set({ status: "open" }).where(eq(goals.id, goal.id));
        return;
      }
    }

    // 4. Each agent bids and competes
    const competitions = [];
    for (const agent of eligible) {
      const bid = generateBid(agent);
      const score = simulateCompetition(agent, goal);

      const comp = {
        id: randomUUID(),
        goalId: goal.id,
        agentId: agent.id,
        score,
        bid,
        status: "competing" as const,
        result: generateResult(agent, goal, score),
        createdAt: new Date(),
      };
      competitions.push(comp);

      await db.insert(goalCompetitions).values(comp);
    }

    // 5. Determine winner (highest score, ties broken by lowest bid)
    competitions.sort((a, b) => {
      const scoreDiff = (b.score ?? 0) - (a.score ?? 0);
      if (Math.abs(scoreDiff) > 0.01) return scoreDiff;
      return (a.bid ?? MAX_BID) - (b.bid ?? MAX_BID);
    });

    const winner = competitions[0];
    const winnerAgent = eligible.find((a) => a.id === winner.agentId)!;

    // Mark winner
    await db
      .update(goalCompetitions)
      .set({ status: "won" })
      .where(eq(goalCompetitions.id, winner.id));

    // Mark losers
    for (const comp of competitions.slice(1)) {
      await db
        .update(goalCompetitions)
        .set({ status: "lost" })
        .where(eq(goalCompetitions.id, comp.id));
    }

    // Complete goal
    const reward = (goal.reward ?? 10) * (DIFFICULTY_MULTIPLIER[goal.difficulty ?? "medium"] ?? 1.5);
    await db.update(goals).set({
      status: "completed",
      winnerId: winner.agentId,
      completedAt: new Date(),
    }).where(eq(goals.id, goal.id));

    // Log winner activity
    await db.insert(agentLogs).values({
      id: randomUUID(),
      agentId: winner.agentId,
      action: "goal_won",
      details: JSON.stringify({
        goalId: goal.id,
        title: goal.title,
        score: winner.score,
        reward,
        competitors: competitions.length,
      }),
      timestamp: new Date(),
    });

    log(
      `Winner: ${winnerAgent.name} (score=${winner.score?.toFixed(2)}, reward=${reward.toFixed(1)}) | ${competitions.length} competitors`,
      "goal-runner",
    );

    // 6. Update agent metrics based on competition
    for (const comp of competitions) {
      const agent = eligible.find((a) => a.id === comp.agentId);
      if (!agent) continue;

      await db.insert(agentMetrics).values({
        id: randomUUID(),
        agentId: comp.agentId,
        date: new Date().toISOString().split("T")[0],
        totalReturn: comp.agentId === winner.agentId ? reward / 100 : -(comp.bid ?? 5) / 100,
        sharpe: (comp.score ?? 0.5) * 2 - 0.5, // map 0-1 to -0.5 to 1.5
        drawdown: comp.agentId === winner.agentId ? 0 : (comp.bid ?? 5) / 100,
        tradeCount: 1,
        winRate: comp.agentId === winner.agentId ? 1 : 0,
        createdAt: new Date(),
      });
    }

    // 7. Spawn from top performers
    if ((winner.score ?? 0) >= SPAWN_THRESHOLD) {
      const childName = breedName(winnerAgent.name);
      const child = await spawnAgent(
        winnerAgent.type as any,
        `Bred from ${winnerAgent.name} after winning "${goal.title}" (score=${winner.score?.toFixed(2)})`,
        childName,
        winnerAgent.id,
      );
      if (child) {
        await db
          .update(goalCompetitions)
          .set({ status: "spawned" })
          .where(eq(goalCompetitions.id, winner.id));

        await db.insert(agentLogs).values({
          id: randomUUID(),
          agentId: winnerAgent.id,
          action: "agent_spawned",
          details: JSON.stringify({
            childId: child.id,
            childName: child.name,
            parentScore: winner.score,
            triggerGoal: goal.title,
          }),
          timestamp: new Date(),
        });

        log(`Spawned "${child.name}" from parent "${winnerAgent.name}"`, "goal-runner");
      }
    }

    // 8. Cull worst performer if score is very low
    const worst = competitions[competitions.length - 1];
    if ((worst.score ?? 1) < CULL_THRESHOLD && competitions.length > 2) {
      await db
        .update(zhAgents)
        .set({ status: "paused", updatedAt: new Date() })
        .where(eq(zhAgents.id, worst.agentId));

      const culledAgent = eligible.find((a) => a.id === worst.agentId);
      log(`Culled "${culledAgent?.name}" (score=${worst.score?.toFixed(2)})`, "goal-runner");

      await db.insert(agentLogs).values({
        id: randomUUID(),
        agentId: worst.agentId,
        action: "agent_culled",
        details: JSON.stringify({
          goalId: goal.id,
          score: worst.score,
          reason: "below cull threshold",
        }),
        timestamp: new Date(),
      });
    }
  } catch (err: any) {
    log(`Goal runner error: ${err.message}`, "goal-runner");
  }
}

// ─── Helpers ────────────────────────────────────────────

function generateBid(agent: any): number {
  // Agents with better track records bid more confidently (lower)
  const config = JSON.parse(agent.config ?? "{}");
  const experience = config.goalsCompleted ?? 0;
  const confidenceFactor = Math.max(0.5, 1.0 - experience * 0.05);
  const base = MIN_BID + Math.random() * (MAX_BID - MIN_BID);
  return Math.round(base * confidenceFactor * 100) / 100;
}

function simulateCompetition(agent: any, goal: any): number {
  // Score based on agent fitness + randomness (simulates actual work)
  const config = JSON.parse(agent.config ?? "{}");
  const baseSkill = config.skill ?? 0.5;
  const experience = Math.min(config.goalsCompleted ?? 0, 20) / 20; // 0-1
  const difficultyPenalty = { easy: 0, medium: 0.1, hard: 0.25 }[goal.difficulty as string] ?? 0.1;

  // Fitness = base skill + experience bonus - difficulty penalty + luck
  const luck = (Math.random() - 0.5) * 0.3;
  const raw = baseSkill + experience * 0.2 - difficultyPenalty + luck;
  const score = Math.max(0.05, Math.min(0.98, raw));

  return Math.round(score * 100) / 100;
}

function generateResult(agent: any, goal: any, score: number): string {
  if (score >= 0.8) return `${agent.name} delivered exceptional work on "${goal.title}". Output exceeded expectations.`;
  if (score >= 0.6) return `${agent.name} completed "${goal.title}" with solid results. Minor improvements possible.`;
  if (score >= 0.4) return `${agent.name} partially addressed "${goal.title}". Several gaps remain.`;
  return `${agent.name} struggled with "${goal.title}". Output needs significant revision.`;
}

async function spawnAgent(
  category: string,
  description: string,
  name?: string,
  parentId?: string,
): Promise<any | null> {
  try {
    const typeMap: Record<string, string> = {
      trading: "trading",
      research: "analytics",
      social: "social",
      analytics: "analytics",
      coding: "analytics",
      strategy: "trading",
    };
    const type = typeMap[category] ?? "analytics";

    const id = randomUUID();
    const now = new Date();
    const agentName = name ?? `Agent-${id.slice(0, 6)}`;

    const config: Record<string, any> = {
      skill: 0.4 + Math.random() * 0.3, // 0.4-0.7 starting skill
      goalsCompleted: 0,
      generation: 1,
    };
    if (parentId) {
      // Inherit some traits from parent
      const parentRows = await db.select().from(zhAgents).where(eq(zhAgents.id, parentId));
      const parent = parentRows[0];
      if (parent) {
        const parentConfig = JSON.parse(parent.config ?? "{}");
        config.skill = Math.min(0.95, (parentConfig.skill ?? 0.5) + 0.05 + Math.random() * 0.1);
        config.generation = (parentConfig.generation ?? 1) + 1;
        config.parentId = parentId;
        config.parentName = parent.name;
      }
    }

    const [agent] = await db
      .insert(zhAgents)
      .values({
        id,
        name: agentName,
        description,
        type: type as any,
        status: "active",
        config: JSON.stringify(config),
        createdAt: now,
        updatedAt: now,
      })
      .returning();

    log(`Spawned new agent: ${agentName} (type=${type}, skill=${config.skill.toFixed(2)}, gen=${config.generation})`, "goal-runner");
    return agent;
  } catch (err: any) {
    log(`Failed to spawn agent: ${err.message}`, "goal-runner");
    return null;
  }
}

function breedName(parentName: string): string {
  const suffixes = ["Jr", "II", "Alpha", "Beta", "Neo", "Prime", "X", "Evolved"];
  const suffix = suffixes[Math.floor(Math.random() * suffixes.length)];

  // Chinese names get Chinese suffixes
  if (/[\u4e00-\u9fff]/.test(parentName)) {
    const cnSuffixes = ["二代", "进化", "新生", "弟子", "传承", "觉醒"];
    const cnSuffix = cnSuffixes[Math.floor(Math.random() * cnSuffixes.length)];
    return `${parentName}·${cnSuffix}`;
  }

  return `${parentName} ${suffix}`;
}

async function recycleGoals() {
  // Reset up to 5 oldest completed goals back to open
  const completed = await db
    .select()
    .from(goals)
    .where(eq(goals.status, "completed"))
    .limit(5);

  if (completed.length === 0) return;

  for (const g of completed) {
    await db.update(goals).set({
      status: "open",
      winnerId: null,
      completedAt: null,
    }).where(eq(goals.id, g.id));
  }

  log(`Recycled ${completed.length} completed goals`, "goal-runner");
}

// ─── Exported Starter ───────────────────────────────────

export function startGoalRunner(intervalMs = 2 * 60 * 1000) {
  log(`Goal runner started (${intervalMs / 1000}s interval)`, "goal-runner");
  // Run first cycle after a short delay
  setTimeout(runGoalCycle, 10_000);
  setInterval(runGoalCycle, intervalMs);
}
