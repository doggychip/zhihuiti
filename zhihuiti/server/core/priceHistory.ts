import { getCurrentPrices } from "./dataProvider";
import { log } from "../index";

const MAX_HISTORY = 100;
const history: Map<string, number[]> = new Map();

export function getPriceHistory(pair: string): number[] {
  return history.get(pair) ?? [];
}

export function getAllPairHistories(): Map<string, number[]> {
  return history;
}

function samplePrices() {
  const { prices } = getCurrentPrices();
  for (const p of prices) {
    if (!history.has(p.pair)) history.set(p.pair, []);
    const arr = history.get(p.pair)!;
    arr.push(p.price);
    if (arr.length > MAX_HISTORY) arr.shift();
  }
}

export function startPriceHistory(intervalMs = 30000) {
  samplePrices(); // Initial sample
  setInterval(samplePrices, intervalMs);
  log("Price history buffer started (30s sampling)", "price-history");
}
