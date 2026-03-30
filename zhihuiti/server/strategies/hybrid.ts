import { sma, rsi, volatility, priceChange } from "../core/indicators";
import type { Signal, PriceMap } from "../core/strategyEngine";

/** Combined momentum + RSI filter */
export function momentumPlusRsi(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const smaPeriod = params.smaPeriod ?? 20;
  const rsiPeriod = params.rsiPeriod ?? 14;
  const rsiOversold = params.rsiOversold ?? 40;
  const rsiOverbought = params.rsiOverbought ?? 60;
  const quantity = params.quantity ?? 0.01;

  if (prices.length < Math.max(smaPeriod, rsiPeriod) + 1) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const current = prices[prices.length - 1];
  const smaCurrent = sma(prices, smaPeriod);
  const smaPrev = sma(prices.slice(0, -1), smaPeriod);
  const rsiValue = rsi(prices, rsiPeriod);

  // Buy: price crosses above SMA AND RSI not overbought
  if (current > smaCurrent && prices[prices.length - 2] <= smaPrev && rsiValue < rsiOverbought) {
    return {
      action: "buy",
      pair,
      quantity,
      reason: `momentum buy confirmed by RSI ${rsiValue.toFixed(1)}`,
    };
  }
  // Sell: price crosses below SMA AND RSI not oversold
  if (current < smaCurrent && prices[prices.length - 2] >= smaPrev && rsiValue > rsiOversold) {
    return {
      action: "sell",
      pair,
      quantity,
      reason: `momentum sell confirmed by RSI ${rsiValue.toFixed(1)}`,
    };
  }
  return { action: "hold", pair, quantity: 0, reason: "no confirmed signal" };
}

/** Volatility-adjusted position sizing */
export function adaptiveSizing(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const period = params.period ?? 10;
  const baseQuantity = params.baseQuantity ?? 0.01;
  const targetVol = params.targetVol ?? 0.01;

  if (prices.length < period + 1) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const vol = volatility(prices, period);
  const change = priceChange(prices, period);

  // Scale quantity inversely with volatility
  const volRatio = vol > 0 ? targetVol / vol : 1;
  const scaledQty = Math.max(0.001, Math.min(baseQuantity * volRatio, baseQuantity * 2));

  if (change > 0.005) {
    return {
      action: "buy",
      pair,
      quantity: scaledQty,
      reason: `adaptive buy vol=${vol.toFixed(4)} qty=${scaledQty.toFixed(4)}`,
    };
  }
  if (change < -0.005) {
    return {
      action: "sell",
      pair,
      quantity: scaledQty,
      reason: `adaptive sell vol=${vol.toFixed(4)} qty=${scaledQty.toFixed(4)}`,
    };
  }
  return { action: "hold", pair, quantity: 0, reason: "no signal" };
}

/** Fibonacci retracement levels */
export function fibonacciLevels(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const lookback = params.lookback ?? 20;
  const quantity = params.quantity ?? 0.01;

  if (prices.length < lookback) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const window = prices.slice(-lookback);
  const high = Math.max(...window);
  const low = Math.min(...window);
  const range = high - low;
  const current = prices[prices.length - 1];

  // Fibonacci levels
  const fib382 = high - range * 0.382;
  const fib618 = high - range * 0.618;

  if (current <= fib618 + range * 0.02) {
    return {
      action: "buy",
      pair,
      quantity,
      reason: `near 61.8% fib support: ${current.toFixed(2)} vs ${fib618.toFixed(2)}`,
    };
  }
  if (current >= fib382 - range * 0.02) {
    return {
      action: "sell",
      pair,
      quantity,
      reason: `near 38.2% fib resistance: ${current.toFixed(2)} vs ${fib382.toFixed(2)}`,
    };
  }
  return { action: "hold", pair, quantity: 0, reason: "no fib level hit" };
}
