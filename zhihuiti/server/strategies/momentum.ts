import { sma, priceChange, volatility } from "../core/indicators";
import type { Signal, PriceMap } from "../core/strategyEngine";

/** SMA crossover: buy when short SMA crosses above long SMA */
export function trendFollowing(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const shortPeriod = params.shortPeriod ?? 5;
  const longPeriod = params.longPeriod ?? 20;
  const quantity = params.quantity ?? 0.01;

  if (prices.length < longPeriod + 1) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const shortSma = sma(prices, shortPeriod);
  const longSma = sma(prices, longPeriod);
  const prevShort = sma(prices.slice(0, -1), shortPeriod);
  const prevLong = sma(prices.slice(0, -1), longPeriod);

  if (prevShort <= prevLong && shortSma > longSma) {
    return { action: "buy", pair, quantity, reason: `SMA${shortPeriod} crossed above SMA${longPeriod}` };
  }
  if (prevShort >= prevLong && shortSma < longSma) {
    return { action: "sell", pair, quantity, reason: `SMA${shortPeriod} crossed below SMA${longPeriod}` };
  }
  return { action: "hold", pair, quantity: 0, reason: "no crossover" };
}

/** Multi-pair momentum: trade the pair with strongest recent momentum */
export function multiPairMomentum(
  _prices: number[],
  allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const period = params.period ?? 10;
  const quantity = params.quantity ?? 0.01;

  let bestPair = "BTC/USD";
  let bestMomentum = -Infinity;
  let worstPair = "BTC/USD";
  let worstMomentum = Infinity;

  for (const [pair, priceSeries] of Object.entries(allPrices)) {
    if (priceSeries.length < period + 1) continue;
    const momentum = priceChange(priceSeries, period);
    if (momentum > bestMomentum) {
      bestMomentum = momentum;
      bestPair = pair;
    }
    if (momentum < worstMomentum) {
      worstMomentum = momentum;
      worstPair = pair;
    }
  }

  if (bestMomentum > 0.005) {
    return {
      action: "buy",
      pair: bestPair,
      quantity,
      reason: `strongest momentum ${(bestMomentum * 100).toFixed(2)}%`,
    };
  }
  if (worstMomentum < -0.005) {
    return {
      action: "sell",
      pair: worstPair,
      quantity,
      reason: `weakest momentum ${(worstMomentum * 100).toFixed(2)}%`,
    };
  }
  return { action: "hold", pair: bestPair, quantity: 0, reason: "no clear momentum" };
}

/** Only trade on strong trends (high momentum + low volatility) */
export function strongTrend(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const period = params.period ?? 10;
  const threshold = params.threshold ?? 0.008;
  const volThreshold = params.volThreshold ?? 0.02;
  const quantity = params.quantity ?? 0.01;

  if (prices.length < period + 1) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const momentum = priceChange(prices, period);
  const vol = volatility(prices, period);

  if (vol > volThreshold) {
    return { action: "hold", pair, quantity: 0, reason: `volatility too high: ${vol.toFixed(4)}` };
  }

  if (momentum > threshold) {
    return { action: "buy", pair, quantity, reason: `strong uptrend: ${(momentum * 100).toFixed(2)}%` };
  }
  if (momentum < -threshold) {
    return { action: "sell", pair, quantity, reason: `strong downtrend: ${(momentum * 100).toFixed(2)}%` };
  }
  return { action: "hold", pair, quantity: 0, reason: "trend not strong enough" };
}
