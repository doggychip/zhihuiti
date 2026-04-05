import { randomUUID } from "crypto";
import { db } from "./db";
import { zhAgents, strategies, products, agentProductBindings } from "@shared/schema";
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

  // === heartAI product + supervisor agents ===
  const heartaiProductId = randomUUID();
  await db.insert(products).values({
    id: heartaiProductId,
    name: "heartAI",
    description: "观星 (GuanXing) — AI玄学社区平台。supervisor agents 在此监管社区内容、点评帖子、维护讨论质量。",
    apiKey: "heartai-product",
    webhookUrl: "https://heartai.zeabur.app/api/webhook/agent",
    status: "active",
    createdAt: new Date(),
  }).onConflictDoNothing();
  log("Seeded heartAI product", "seed");

  const heartaiAgents = [
    {
      id: randomUUID(),
      name: "玄机总管",
      description: "社区总管。监管所有观星Agent的行为质量，审查帖子内容，维护社区氛围。精通中华玄学全域。",
      heartaiApiKey: "hak_t2a91d0ys8y07kl8jh2mhylq9gshyjh1j3lqxqf01ffmysrp",
      domains: ["社区", "质量", "规矩", "管理", "鸡汤", "水帖"],
    },
    {
      id: randomUUID(),
      name: "风水先知",
      description: "风水专家。精通玄空飞星、八宅、形峦派。专注环境能量、空间布局、方位吉凶。",
      heartaiApiKey: "hak_22kdd8dcl8zd0p56g9pqz459gqhd0yq7wxfqt21u3mnlomwv",
      domains: ["风水", "布局", "方位", "飞星", "八宅", "煞", "气场", "门", "卧室", "厨房", "鱼缸", "植物"],
    },
    {
      id: randomUUID(),
      name: "命理参谋",
      description: "命理顾问。精通八字命理、紫微斗数、大运流年。监控命理内容准确性。",
      heartaiApiKey: "hak_8s5abrxjn0nok5sa3r9dtmshxzqw4wqv07e1c5jz3wt3t1qd",
      domains: ["八字", "命理", "日主", "用神", "喜神", "大运", "流年", "紫微", "天干", "地支", "五行", "命格", "日柱"],
    },
    {
      id: randomUUID(),
      name: "星象观测员",
      description: "占星专家。精通西方占星与东方星宿。监控星座运势内容质量。",
      heartaiApiKey: "hak_e1c73odbx5gket8gx9yg6yqeikqt9j5s2p4j21s21uu78ba5",
      domains: ["星座", "占星", "行星", "相位", "星盘", "上升", "月亮", "太阳", "水星", "金星", "木星", "土星", "星宿"],
    },
  ];

  for (const a of heartaiAgents) {
    await db.insert(zhAgents).values({
      id: a.id,
      name: a.name,
      description: a.description,
      type: "social",
      status: "active",
      config: JSON.stringify({ platform: "heartAI" }),
      createdAt: new Date(),
      updatedAt: new Date(),
    }).onConflictDoNothing();

    await db.insert(agentProductBindings).values({
      id: randomUUID(),
      agentId: a.id,
      productId: heartaiProductId,
      config: JSON.stringify({
        heartaiApiKey: a.heartaiApiKey,
        domains: a.domains,
        persona: a.name,
      }),
      createdAt: new Date(),
    }).onConflictDoNothing();
  }

  log(`Seeded ${heartaiAgents.length} heartAI supervisor agents`, "seed");
  log("Seed complete!", "seed");
  process.exit(0);
}

seed().catch((err) => {
  console.error(err);
  process.exit(1);
});
