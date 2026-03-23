import { randomUUID } from "crypto";
import { eq, and } from "drizzle-orm";
import { db } from "../db";
import { agentLogs, agentMetrics } from "@shared/schema";
import { getAllAgents } from "../core/agentRegistry";
import { log } from "../index";

function computeMetrics(logs: typeof agentLogs.$inferSelect[]) {
  const tradeLogs = logs.filter(
    (l) => l.action === "trade_executed" || l.action === "trade_failed",
  );
  const tradeCount = tradeLogs.length;
  const wins = tradeLogs.filter((l) => l.action === "trade_executed").length;
  const winRate = tradeCount > 0 ? wins / tradeCount : 0;

  // Simple return simulation: each successful trade contributes a small random return
  let totalReturn = 0;
  let peak = 1;
  let maxDrawdown = 0;
  let equity = 1;

  for (const tl of tradeLogs) {
    if (tl.action === "trade_executed") {
      const r = (Math.random() - 0.45) * 0.02; // slight positive bias
      equity *= 1 + r;
      totalReturn += r;
      if (equity > peak) peak = equity;
      const dd = (peak - equity) / peak;
      if (dd > maxDrawdown) maxDrawdown = dd;
    }
  }

  // Simple Sharpe estimate
  const sharpe = tradeCount > 0 ? (totalReturn / tradeCount) / 0.01 : 0;

  return { totalReturn, sharpe, drawdown: maxDrawdown, tradeCount, winRate };
}

async function runAnalytics() {
  try {
    const allAgents = await getAllAgents();
    const today = new Date().toISOString().slice(0, 10);

    for (const agent of allAgents) {
      try {
        const logs = await db
          .select()
          .from(agentLogs)
          .where(eq(agentLogs.agentId, agent.id));

        const metrics = computeMetrics(logs);

        // Check if metrics for today already exist
        const existing = await db
          .select()
          .from(agentMetrics)
          .where(and(eq(agentMetrics.agentId, agent.id), eq(agentMetrics.date, today)));

        if (existing.length > 0) {
          await db
            .update(agentMetrics)
            .set({
              totalReturn: metrics.totalReturn,
              sharpe: metrics.sharpe,
              drawdown: metrics.drawdown,
              tradeCount: metrics.tradeCount,
              winRate: metrics.winRate,
            })
            .where(eq(agentMetrics.id, existing[0].id));
        } else {
          await db.insert(agentMetrics).values({
            id: randomUUID(),
            agentId: agent.id,
            date: today,
            ...metrics,
            createdAt: new Date(),
          });
        }
      } catch (err: any) {
        log(`Analytics error for agent ${agent.id}: ${err.message}`, "analytics");
      }
    }

    log(`Analytics updated for ${allAgents.length} agents`, "analytics");
  } catch (err: any) {
    log(`Analytics job error: ${err.message}`, "analytics");
  }
}

export function startAnalytics(intervalMs = 5 * 60 * 1000) {
  log("Analytics job started (5m interval)", "analytics");
  setInterval(runAnalytics, intervalMs);
}
