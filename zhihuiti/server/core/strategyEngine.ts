import type { ZhAgent, Strategy } from "@shared/schema";
import { emit } from "./eventBus";
import { log } from "../index";

export interface Signal {
  action: "buy" | "sell" | "hold";
  pair: string;
  quantity: number;
  reason: string;
}

export interface PriceMap {
  [pair: string]: number[];
}

type StrategyFn = (prices: number[], allPrices: PriceMap, params: Record<string, any>) => Signal;

const registry: Map<string, StrategyFn> = new Map();

export function registerStrategy(type: string, fn: StrategyFn): void {
  registry.set(type, fn);
}

export async function executeStrategy(
  agent: ZhAgent,
  strategy: Strategy,
  priceData: PriceMap,
): Promise<Signal> {
  const fn = registry.get(strategy.type);
  if (!fn) {
    log(`No executor for strategy type: ${strategy.type}`, "strategy-engine");
    return { action: "hold", pair: "BTC/USD", quantity: 0, reason: "unknown strategy type" };
  }

  let params: Record<string, any> = {};
  try {
    params = JSON.parse(strategy.parameters ?? "{}");
  } catch {
    // use defaults
  }

  // Pick the default pair from agent config or fallback
  let agentConfig: Record<string, any> = {};
  try {
    agentConfig = JSON.parse(agent.config ?? "{}");
  } catch {
    // use defaults
  }

  const defaultPair = agentConfig.pair ?? "BTC/USD";
  const prices = priceData[defaultPair] ?? [];

  try {
    const signal = fn(prices, priceData, params);
    emit("strategy.executed", { agentId: agent.id, strategyId: strategy.id, signal });
    return signal;
  } catch (err: any) {
    log(`Strategy execution error for agent ${agent.id}: ${err.message}`, "strategy-engine");
    emit("agent.error", { agentId: agent.id, error: err.message });
    return { action: "hold", pair: defaultPair, quantity: 0, reason: `error: ${err.message}` };
  }
}
