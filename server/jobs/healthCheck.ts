import { desc, eq } from "drizzle-orm";
import { db } from "../db";
import { agentLogs } from "@shared/schema";
import { getAllAgents } from "../core/agentRegistry";
import { log } from "../index";

const UNHEALTHY_THRESHOLD_MS = 10 * 60 * 1000; // 10 minutes

async function checkAgentHealth() {
  try {
    const allAgents = await getAllAgents();
    const activeAgents = allAgents.filter((a) => a.status === "active");

    for (const agent of activeAgents) {
      try {
        // Get most recent trade or strategy execution log
        const recentLogs = await db
          .select()
          .from(agentLogs)
          .where(eq(agentLogs.agentId, agent.id))
          .orderBy(desc(agentLogs.timestamp))
          .limit(1);

        if (recentLogs.length === 0) {
          // Agent has never logged anything — might be brand new
          const createdMs = agent.createdAt?.getTime() ?? 0;
          if (Date.now() - createdMs > UNHEALTHY_THRESHOLD_MS) {
            log(`Agent ${agent.id} (${agent.name}) has no logs and is ${Math.round((Date.now() - createdMs) / 60000)}m old`, "health-check");
          }
          continue;
        }

        const lastActivity = recentLogs[0].timestamp?.getTime() ?? 0;
        const idleMs = Date.now() - lastActivity;

        if (idleMs > UNHEALTHY_THRESHOLD_MS) {
          log(
            `Agent ${agent.id} (${agent.name}) is unhealthy: no activity for ${Math.round(idleMs / 60000)}m`,
            "health-check",
          );
        }
      } catch (err: any) {
        log(`Health check error for agent ${agent.id}: ${err.message}`, "health-check");
      }
    }
  } catch (err: any) {
    log(`Health check error: ${err.message}`, "health-check");
  }
}

export function startHealthCheck(intervalMs = 60000) {
  log("Health check started (60s interval)", "health-check");
  setInterval(checkAgentHealth, intervalMs);
}
