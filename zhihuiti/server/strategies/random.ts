import type { Signal, PriceMap } from "../core/strategyEngine";

/** Random walk: random buy/sell/hold for testing */
export function randomWalk(
  _prices: number[],
  allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pairs = Object.keys(allPrices);
  const pair = params.pair ?? (pairs.length > 0 ? pairs[Math.floor(Math.random() * pairs.length)] : "BTC/USD");
  const quantity = params.quantity ?? 0.01;
  const holdBias = params.holdBias ?? 0.6; // 60% chance of hold

  const roll = Math.random();
  if (roll < holdBias) {
    return { action: "hold", pair, quantity: 0, reason: "random hold" };
  }
  if (roll < holdBias + (1 - holdBias) / 2) {
    return { action: "buy", pair, quantity, reason: "random buy" };
  }
  return { action: "sell", pair, quantity, reason: "random sell" };
}
