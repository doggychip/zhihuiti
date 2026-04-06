import { rsi, macd, sma } from "../core/indicators";
import type { Signal, PriceMap } from "../core/strategyEngine";

/** RSI overbought/oversold strategy */
export function rsiStrategy(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const period = params.period ?? 14;
  const oversold = params.oversold ?? 30;
  const overbought = params.overbought ?? 70;
  const quantity = params.quantity ?? 0.01;

  if (prices.length < period + 1) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const rsiValue = rsi(prices, period);

  if (rsiValue <= oversold) {
    return {
      action: "buy",
      pair,
      quantity,
      reason: `RSI oversold: ${rsiValue.toFixed(1)}`,
    };
  }
  if (rsiValue >= overbought) {
    return {
      action: "sell",
      pair,
      quantity,
      reason: `RSI overbought: ${rsiValue.toFixed(1)}`,
    };
  }
  return { action: "hold", pair, quantity: 0, reason: `RSI neutral: ${rsiValue.toFixed(1)}` };
}

/** MACD histogram crossover */
export function macdCross(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const quantity = params.quantity ?? 0.01;

  if (prices.length < 27) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data for MACD" };
  }

  const current = macd(prices);
  const prev = macd(prices.slice(0, -1));

  if (prev.histogram <= 0 && current.histogram > 0) {
    return {
      action: "buy",
      pair,
      quantity,
      reason: `MACD histogram turned positive: ${current.histogram.toFixed(4)}`,
    };
  }
  if (prev.histogram >= 0 && current.histogram < 0) {
    return {
      action: "sell",
      pair,
      quantity,
      reason: `MACD histogram turned negative: ${current.histogram.toFixed(4)}`,
    };
  }
  return { action: "hold", pair, quantity: 0, reason: "no MACD crossover" };
}

/** Ichimoku-simple: SMA cross proxy (9/26 period SMAs) */
export function ichimokuSimple(
  prices: number[],
  _allPrices: PriceMap,
  params: Record<string, any>,
): Signal {
  const pair = params.pair ?? "BTC/USD";
  const conversionPeriod = params.conversionPeriod ?? 9;
  const basePeriod = params.basePeriod ?? 26;
  const quantity = params.quantity ?? 0.01;

  if (prices.length < basePeriod + 1) {
    return { action: "hold", pair, quantity: 0, reason: "insufficient data" };
  }

  const conversion = sma(prices, conversionPeriod);
  const base = sma(prices, basePeriod);
  const prevConversion = sma(prices.slice(0, -1), conversionPeriod);
  const prevBase = sma(prices.slice(0, -1), basePeriod);

  if (prevConversion <= prevBase && conversion > base) {
    return {
      action: "buy",
      pair,
      quantity,
      reason: `Ichimoku conversion crossed above base`,
    };
  }
  if (prevConversion >= prevBase && conversion < base) {
    return {
      action: "sell",
      pair,
      quantity,
      reason: `Ichimoku conversion crossed below base`,
    };
  }
  return { action: "hold", pair, quantity: 0, reason: "no Ichimoku crossover" };
}
