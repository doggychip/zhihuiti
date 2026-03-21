import { randomUUID } from "crypto";
import { db } from "./db";
import { zhAgents, strategies, products } from "@shared/schema";
import { log } from "./index";

async function seed() {
  log("Seeding database...", "seed");

  // Seed strategies
  const strategyData = [
    {
      id: randomUUID(),
      name: "Trend Following",
      description: "SMA crossover momentum strategy",
      type: "momentum" as const,
      parameters: JSON.stringify({ shortPeriod: 5, longPeriod: 20, quantity: 0.01, pair: "BTC/USD" }),
      createdAt: new Date(),
    },
    {
      id: randomUUID(),
      name: "Bollinger Bounce",
      description: "Mean reversion using Bollinger Bands",
      type: "mean_reversion" as const,
      parameters: JSON.stringify({ period: 20, stdDev: 2, quantity: 0.01, pair: "ETH/USD" }),
      createdAt: new Date(),
    },
    {
      id: randomUUID(),
      name: "RSI Oscillator",
      description: "RSI overbought/oversold strategy",
      type: "indicator" as const,
      parameters: JSON.stringify({ period: 14, oversold: 30, overbought: 70, quantity: 0.01, pair: "SOL/USD" }),
      createdAt: new Date(),
    },
    {
      id: randomUUID(),
      name: "Momentum + RSI",
      description: "Combined momentum and RSI filter",
      type: "hybrid" as const,
      parameters: JSON.stringify({ smaPeriod: 20, rsiPeriod: 14, quantity: 0.01, pair: "BTC/USD" }),
      createdAt: new Date(),
    },
  ];

  for (const s of strategyData) {
    await db.insert(strategies).values(s).onConflictDoNothing();
  }

  log(`Seeded ${strategyData.length} strategies`, "seed");

  // Seed a demo product
  const demoProduct = {
    id: randomUUID(),
    name: "AlphaArena",
    description: "AlphaArena paper trading competition",
    apiKey: randomUUID(),
    webhookUrl: "https://alphaarena.app",
    status: "active" as const,
    createdAt: new Date(),
  };
  await db.insert(products).values(demoProduct).onConflictDoNothing();
  log("Seeded demo product", "seed");

  // Seed demo agents
  const agentData = [
    {
      id: randomUUID(),
      name: "TrendBot Alpha",
      description: "Trend following agent on BTC",
      type: "trading" as const,
      status: "active" as const,
      strategyId: strategyData[0].id,
      config: JSON.stringify({ pair: "BTC/USD" }),
      createdAt: new Date(),
      updatedAt: new Date(),
    },
    {
      id: randomUUID(),
      name: "ReversionBot",
      description: "Mean reversion on ETH",
      type: "trading" as const,
      status: "active" as const,
      strategyId: strategyData[1].id,
      config: JSON.stringify({ pair: "ETH/USD" }),
      createdAt: new Date(),
      updatedAt: new Date(),
    },
    {
      id: randomUUID(),
      name: "RSI Trader",
      description: "RSI-based SOL trader",
      type: "trading" as const,
      status: "paused" as const,
      strategyId: strategyData[2].id,
      config: JSON.stringify({ pair: "SOL/USD" }),
      createdAt: new Date(),
      updatedAt: new Date(),
    },
  ];

  for (const a of agentData) {
    await db.insert(zhAgents).values(a).onConflictDoNothing();
  }

  log(`Seeded ${agentData.length} agents`, "seed");
  log("Seed complete!", "seed");
  process.exit(0);
}

seed().catch((err) => {
  console.error(err);
  process.exit(1);
});
