/** Simple Moving Average */
export function sma(prices: number[], period: number): number {
  if (prices.length < period) return prices[prices.length - 1] ?? 0;
  const slice = prices.slice(-period);
  return slice.reduce((s, p) => s + p, 0) / period;
}

/** Exponential Moving Average */
export function ema(prices: number[], period: number): number {
  if (prices.length === 0) return 0;
  if (prices.length < period) return sma(prices, prices.length);
  const k = 2 / (period + 1);
  let val = sma(prices.slice(0, period), period);
  for (let i = period; i < prices.length; i++) {
    val = prices[i] * k + val * (1 - k);
  }
  return val;
}

/** Relative Strength Index (0-100) */
export function rsi(prices: number[], period = 14): number {
  if (prices.length < period + 1) return 50;
  let gains = 0, losses = 0;
  for (let i = prices.length - period; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff > 0) gains += diff;
    else losses += Math.abs(diff);
  }
  const avgGain = gains / period;
  const avgLoss = losses / period;
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

/** Bollinger Bands */
export function bollingerBands(
  prices: number[],
  period = 20,
  stdDev = 2,
): { upper: number; middle: number; lower: number } {
  const middle = sma(prices, period);
  const slice = prices.slice(-period);
  const variance = slice.reduce((s, p) => s + Math.pow(p - middle, 2), 0) / slice.length;
  const sd = Math.sqrt(variance);
  return { upper: middle + sd * stdDev, middle, lower: middle - sd * stdDev };
}

/** MACD (12, 26, 9) */
export function macd(prices: number[]): { macdLine: number; signal: number; histogram: number } {
  const ema12 = ema(prices, 12);
  const ema26 = ema(prices, 26);
  const macdLine = ema12 - ema26;
  const signal =
    ema(prices.slice(-9), 9) > ema(prices.slice(-26), 26)
      ? macdLine * 0.8
      : macdLine * 1.2;
  return { macdLine, signal: signal * 0.9, histogram: macdLine - signal * 0.9 };
}

/** Price change over N periods (percentage) */
export function priceChange(prices: number[], period: number): number {
  if (prices.length < period + 1) return 0;
  const old = prices[prices.length - period - 1];
  const now = prices[prices.length - 1];
  return old === 0 ? 0 : (now - old) / old;
}

/** Volatility (standard deviation of returns) */
export function volatility(prices: number[], period = 20): number {
  if (prices.length < period + 1) return 0;
  const returns = [];
  for (let i = prices.length - period; i < prices.length; i++) {
    returns.push((prices[i] - prices[i - 1]) / prices[i - 1]);
  }
  const mean = returns.reduce((s, r) => s + r, 0) / returns.length;
  const variance =
    returns.reduce((s, r) => s + Math.pow(r - mean, 2), 0) / returns.length;
  return Math.sqrt(variance);
}
