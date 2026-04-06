import { randomUUID } from "crypto";
import { eq } from "drizzle-orm";
import { db } from "../db";
import { strategies, agentProductBindings, products, agentLogs } from "@shared/schema";
import { getAllAgents } from "../core/agentRegistry";
import { executeStrategy } from "../core/strategyEngine";
import { executeTrade } from "../core/tradeExecutor";
import { getAllPairHistories } from "../core/priceHistory";
import { log } from "../index";

let agentRoundRobinIndex = 0;

async function runAgentBatch() {
  try {
    const allAgents = await getAllAgents();
    const activeAgents = allAgents.filter((a) => a.status === "active");

    if (activeAgents.length === 0) return;

    // Pick up to 3 agents round-robin
    const batchSize = Math.min(3, activeAgents.length);
    const batch = [];
    for (let i = 0; i < batchSize; i++) {
      batch.push(activeAgents[agentRoundRobinIndex % activeAgents.length]);
      agentRoundRobinIndex++;
    }

    const allPriceHistories = getAllPairHistories();
    const priceData: Record<string, number[]> = {};
    for (const [pair, prices] of allPriceHistories) {
      priceData[pair] = prices;
    }

    for (const agent of batch) {
      try {
        // Get strategy
        if (!agent.strategyId) {
          log(`Agent ${agent.id} has no strategy, skipping`, "agent-runner");
          continue;
        }

        const stratRows = await db
          .select()
          .from(strategies)
          .where(eq(strategies.id, agent.strategyId));
        const strategy = stratRows[0];
        if (!strategy) {
          log(`Strategy ${agent.strategyId} not found for agent ${agent.id}`, "agent-runner");
          continue;
        }

        // Execute strategy
        const signal = await executeStrategy(agent, strategy, priceData);

        // Log strategy execution
        await db.insert(agentLogs).values({
          id: randomUUID(),
          agentId: agent.id,
          action: "strategy_executed",
          details: JSON.stringify({ strategyId: strategy.id, signal }),
          timestamp: new Date(),
        });

        if (signal.action === "hold") {
          log(`Agent ${agent.id} signal: hold (${signal.reason})`, "agent-runner");
          continue;
        }

        // Get product bindings
        const bindings = await db
          .select()
          .from(agentProductBindings)
          .where(eq(agentProductBindings.agentId, agent.id));

        if (bindings.length === 0) {
          log(`Agent ${agent.id} has no product bindings, skipping trade`, "agent-runner");
          continue;
        }

        // Execute trade on each bound product
        for (const binding of bindings) {
          const productRows = await db
            .select()
            .from(products)
            .where(eq(products.id, binding.productId));
          const product = productRows[0];
          if (!product || product.status !== "active") continue;

          const apiKey = product.apiKey ?? "";
          const webhookUrl = product.webhookUrl ?? "";
          if (!apiKey || !webhookUrl) continue;

          await executeTrade(
            agent.id,
            signal.pair,
            signal.action,
            signal.quantity,
            apiKey,
            webhookUrl,
          );
        }
      } catch (err: any) {
        log(`Error running agent ${agent.id}: ${err.message}`, "agent-runner");
      }
    }
  } catch (err: any) {
    log(`Agent runner batch error: ${err.message}`, "agent-runner");
  }
}

export function startAgentRunner(intervalMs = 30000) {
  log(`Agent runner started (${intervalMs / 1000}s interval)`, "agent-runner");
  setInterval(runAgentBatch, intervalMs);
}
