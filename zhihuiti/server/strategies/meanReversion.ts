import { bollingerBands, priceChange } from "../core/indicators";
import type { Signal, PriceMap } from "../core/strategyEngine";

/** Buy at lower Bollinger Band, sell at upper */
export function bollingerBounce(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const period = params.period ?? 20;
  const stdDev = params.stdDev ?? 2;
  const quantity = params.quantity ?? 0.01;

  if (prices.length < period) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const current = prices[prices.length - 1];
  const { upper, lower, middle } = bollingerBands(prices, period, stdDev);

  if (current <= lower) {
    return {
      action: "buy",
      pair,
      quantity,
      reason: `price at lower BB: ${current.toFixed(2)} <= ${lower.toFixed(2)}`,
    };
  }
  if (current >= upper) {
    return {
      action: "sell",
      pair,
      quantity,
      reason: `price at upper BB: ${current.toFixed(2)} >= ${upper.toFixed(2)}`,
    };
  }
  return {
    action: "hold",
    pair,
    quantity: 0,
    reason: `price in BB range: ${lower.toFixed(2)} - ${upper.toFixed(2)}`,
  };
}

/** Fade recent moves: buy oversold, sell overbought based on short-term change */
export function contrarian(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const period = params.period ?? 5;
  const threshold = params.threshold ?? 0.01;
  const quantity = params.quantity ?? 0.01;

  if (prices.length < period + 1) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const change = priceChange(prices, period);

  if (change < -threshold) {
    return {
      action: "buy",
      pair,
      quantity,
      reason: `contrarian buy after ${(change * 100).toFixed(2)}% drop`,
    };
  }
  if (change > threshold) {
    return {
      action: "sell",
      pair,
      quantity,
      reason: `contrarian sell after ${(change * 100).toFixed(2)}% rise`,
    };
  }
  return { action: "hold", pair, quantity: 0, reason: "move not significant enough" };
}
