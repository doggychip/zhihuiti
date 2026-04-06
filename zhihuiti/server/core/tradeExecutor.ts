import { randomUUID } from "crypto";
import { db } from "../db";
import { agentLogs } from "@shared/schema";
import { log } from "../index";
import { emit } from "./eventBus";

export interface TradeResult {
  success: boolean;
  orderId?: string;
  error?: string;
  details?: any;
}

export async function executeTrade(
  agentId: string,
  pair: string,
  side: "buy" | "sell",
  quantity: number,
  productApiKey: string,
  productUrl: string,
): Promise<TradeResult> {
  let result: TradeResult;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    const res = await fetch(`${productUrl}/api/trades`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": productApiKey,
      },
      body: JSON.stringify({ agentId, pair, side, quantity }),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    const body = await res.json().catch(() => ({}));

    if (res.ok) {
      result = { success: true, orderId: body.id ?? body.orderId, details: body };
      emit("agent.trade", { agentId, pair, side, quantity, result });
      log(`Trade executed: agent=${agentId} ${side} ${quantity} ${pair}`, "trade-executor");
    } else {
      result = { success: false, error: body.error ?? `HTTP ${res.status}`, details: body };
      log(`Trade failed: agent=${agentId} ${res.status} ${result.error}`, "trade-executor");
    }
  } catch (err: any) {
    result = { success: false, error: err.message };
    log(`Trade error: agent=${agentId} ${err.message}`, "trade-executor");
  }

  // Log to agentLogs
  await db.insert(agentLogs).values({
    id: randomUUID(),
    agentId,
    action: result.success ? "trade_executed" : "trade_failed",
    details: JSON.stringify({ pair, side, quantity, result }),
    timestamp: new Date(),
  }).catch((err) => {
    log(`Failed to write agent log: ${err.message}`, "trade-executor");
  });

  return result;
}
