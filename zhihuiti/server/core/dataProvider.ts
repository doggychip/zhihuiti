import { log } from "../index";

// CoinGecko ID to pair mapping
const COINGECKO_ID_MAP: Record<string, string> = {
  bitcoin: "BTC/USD",
  ethereum: "ETH/USD",
  binancecoin: "BNB/USD",
  solana: "SOL/USD",
  ripple: "XRP/USD",
  cardano: "ADA/USD",
  dogecoin: "DOGE/USD",
  "avalanche-2": "AVAX/USD",
  polkadot: "DOT/USD",
  chainlink: "LINK/USD",
};

const COINGECKO_IDS = Object.keys(COINGECKO_ID_MAP).join(",");
const COINGECKO_URL = `https://api.coingecko.com/api/v3/simple/price?ids=${COINGECKO_IDS}&vs_currencies=usd&include_24hr_change=true`;

// CoinCap ID to pair mapping (backup source)
const COINCAP_ID_MAP: Record<string, string> = {
  bitcoin: "BTC/USD",
  ethereum: "ETH/USD",
  "binance-coin": "BNB/USD",
  solana: "SOL/USD",
  ripple: "XRP/USD",
  cardano: "ADA/USD",
  dogecoin: "DOGE/USD",
  "avalanche-2": "AVAX/USD",
  polkadot: "DOT/USD",
  chainlink: "LINK/USD",
};

const COINCAP_IDS = Object.keys(COINCAP_ID_MAP).join(",");
const COINCAP_URL = `https://api.coincap.io/v2/assets?ids=${COINCAP_IDS}`;

// Fallback simulated prices
const basePrices: Record<string, number> = {
  "BTC/USD": 87420,
  "ETH/USD": 3180,
  "BNB/USD": 625,
  "SOL/USD": 148,
  "XRP/USD": 2.45,
  "ADA/USD": 0.72,
  "DOGE/USD": 0.165,
  "AVAX/USD": 38.5,
  "DOT/USD": 7.82,
  "LINK/USD": 16.4,
};

export interface PriceData {
  pair: string;
  price: number;
  change24h: number;
}

interface PriceCache {
  prices: PriceData[];
  timestamp: number;
  isLive: boolean;
}

let cache: PriceCache = {
  prices: [],
  timestamp: 0,
  isLive: false,
};

// Simulated prices state
let simulatedPrices: Record<string, number> = { ...basePrices };
let lastSimUpdate = 0;

function getSimulatedPrices(): PriceData[] {
  const now = Date.now();
  if (now - lastSimUpdate > 5000) {
    lastSimUpdate = now;
    for (const pair of Object.keys(simulatedPrices)) {
      const change = (Math.random() - 0.5) * 0.004; // +/-0.2%
      simulatedPrices[pair] =
        Math.round(simulatedPrices[pair] * (1 + change) * 100) / 100;
    }
  }
  return Object.entries(simulatedPrices).map(([pair, price]) => {
    const base = basePrices[pair];
    const change24h = ((price - base) / base) * 100;
    return { pair, price, change24h: Math.round(change24h * 100) / 100 };
  });
}

// Initialize simulated prices with slight variations
for (const pair of Object.keys(simulatedPrices)) {
  const change = (Math.random() - 0.5) * 0.01;
  simulatedPrices[pair] =
    Math.round(basePrices[pair] * (1 + change) * 100) / 100;
}

async function fetchCoinGeckoPrices(): Promise<PriceData[] | null> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    const res = await fetch(COINGECKO_URL, { signal: controller.signal });
    clearTimeout(timeout);

    if (!res.ok) {
      log(`CoinGecko API returned ${res.status}`, "data-provider");
      return null;
    }

    const data = await res.json();
    const prices: PriceData[] = [];

    for (const [geckoId, pair] of Object.entries(COINGECKO_ID_MAP)) {
      const entry = data[geckoId];
      if (entry && typeof entry.usd === "number") {
        prices.push({
          pair,
          price: entry.usd,
          change24h: Math.round((entry.usd_24h_change ?? 0) * 100) / 100,
        });
      }
    }

    if (prices.length === 0) return null;
    return prices;
  } catch (err: any) {
    if (err.name !== "AbortError") {
      log(`CoinGecko fetch error: ${err.message}`, "data-provider");
    }
    return null;
  }
}

async function fetchCoinCapPrices(): Promise<PriceData[] | null> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    const res = await fetch(COINCAP_URL, { signal: controller.signal });
    clearTimeout(timeout);

    if (!res.ok) {
      log(`CoinCap API returned ${res.status}`, "data-provider");
      return null;
    }

    const data = await res.json();
    const assets: any[] = data?.data;
    if (!Array.isArray(assets) || assets.length === 0) return null;

    const prices: PriceData[] = [];

    for (const asset of assets) {
      const pair = COINCAP_ID_MAP[asset.id];
      if (pair && asset.priceUsd != null) {
        prices.push({
          pair,
          price: parseFloat(asset.priceUsd),
          change24h: Math.round(parseFloat(asset.changePercent24Hr ?? "0") * 100) / 100,
        });
      }
    }

    if (prices.length === 0) return null;
    return prices;
  } catch (err: any) {
    if (err.name !== "AbortError") {
      log(`CoinCap fetch error: ${err.message}`, "data-provider");
    }
    return null;
  }
}

async function refreshPrices() {
  let livePrices = await fetchCoinGeckoPrices();
  let source = "CoinGecko";
  if (!livePrices) {
    log("CoinGecko failed, trying CoinCap...", "prices");
    livePrices = await fetchCoinCapPrices();
    source = "CoinCap";
  }
  if (livePrices) {
    cache = {
      prices: livePrices,
      timestamp: Date.now(),
      isLive: true,
    };
    log(`Fetched live prices for ${livePrices.length} pairs from ${source}`, "data-provider");
  } else {
    cache = {
      prices: getSimulatedPrices(),
      timestamp: Date.now(),
      isLive: false,
    };
  }
}

let intervalHandle: ReturnType<typeof setInterval> | null = null;

export function startDataProvider(intervalMs = 30000) {
  refreshPrices();
  intervalHandle = setInterval(refreshPrices, intervalMs);
  log("Data provider started (30s refresh)", "data-provider");
}

export function getCurrentPrices(): { prices: PriceData[]; isLive: boolean } {
  if (cache.prices.length === 0) {
    return { prices: getSimulatedPrices(), isLive: false };
  }
  if (!cache.isLive) {
    return { prices: getSimulatedPrices(), isLive: false };
  }
  return { prices: cache.prices, isLive: cache.isLive };
}

export function getPriceForPair(pair: string): number | undefined {
  const { prices } = getCurrentPrices();
  return prices.find((p) => p.pair === pair)?.price;
}
