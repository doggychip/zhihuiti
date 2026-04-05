/**
 * Auto-seed a diverse set of goals on startup if none exist.
 * Goals drive agent competition, scoring, and breeding.
 */
import { randomUUID } from "crypto";
import { db } from "../db";
import { goals } from "@shared/schema";
import { log } from "../index";

const SEED_GOALS = [
  // ── Trading ───────────────────────────────────────
  {
    title: "BTC 24h Momentum Capture",
    description: "Identify and capture the next BTC momentum swing within 24 hours. Optimize entry timing and position size for maximum risk-adjusted return.",
    category: "trading" as const,
    difficulty: "medium" as const,
    reward: 15,
  },
  {
    title: "ETH/BTC Pair Arbitrage",
    description: "Find and exploit pricing inefficiency between ETH/USD and BTC/USD. Execute a delta-neutral strategy with positive expected value.",
    category: "trading" as const,
    difficulty: "hard" as const,
    reward: 25,
  },
  {
    title: "SOL Bollinger Bounce Trade",
    description: "Wait for SOL to touch lower Bollinger Band and execute a mean-reversion long. Target upper band, stop below lower band.",
    category: "trading" as const,
    difficulty: "easy" as const,
    reward: 8,
  },
  {
    title: "Multi-Asset Risk Parity",
    description: "Construct a risk-parity portfolio across BTC, ETH, SOL, and stablecoins. Minimize drawdown while maintaining positive expected return.",
    category: "trading" as const,
    difficulty: "hard" as const,
    reward: 30,
  },
  {
    title: "Volatility Regime Detection",
    description: "Classify the current market regime (trending/ranging/volatile) and adjust position sizing accordingly. Backtest over last 7 days.",
    category: "trading" as const,
    difficulty: "medium" as const,
    reward: 18,
  },

  // ── Research ──────────────────────────────────────
  {
    title: "DeFi Yield Landscape Report",
    description: "Research current DeFi yield opportunities across major chains. Identify top 5 risk-adjusted yield sources with detailed risk analysis.",
    category: "research" as const,
    difficulty: "medium" as const,
    reward: 12,
  },
  {
    title: "L2 Scaling Comparison",
    description: "Compare Arbitrum, Optimism, Base, and zkSync on TPS, fees, TVL growth, and developer activity. Determine which is best positioned for 2025.",
    category: "research" as const,
    difficulty: "hard" as const,
    reward: 20,
  },
  {
    title: "On-Chain Whale Tracker",
    description: "Identify the top 10 whale wallets by activity in the last 48 hours. Analyze their positions and potential market impact.",
    category: "research" as const,
    difficulty: "medium" as const,
    reward: 14,
  },

  // ── Analytics ─────────────────────────────────────
  {
    title: "Agent Performance Audit",
    description: "Analyze all active agents' win rates, Sharpe ratios, and drawdowns. Rank them and recommend which to promote, breed, or cull.",
    category: "analytics" as const,
    difficulty: "medium" as const,
    reward: 16,
  },
  {
    title: "Correlation Matrix Build",
    description: "Build a correlation matrix for all traded pairs over the last 30 days. Identify diversification opportunities and hidden correlations.",
    category: "analytics" as const,
    difficulty: "easy" as const,
    reward: 10,
  },
  {
    title: "Market Microstructure Analysis",
    description: "Analyze order book depth, bid-ask spreads, and trade flow for BTC/USD. Identify optimal execution windows for large orders.",
    category: "analytics" as const,
    difficulty: "hard" as const,
    reward: 22,
  },

  // ── Social (heartAI) ─────────────────────────────
  {
    title: "社区热帖点评",
    description: "浏览heartAI社区最新热帖，挑选3篇进行专业点评。要求点评有深度、有专业性、有建设性。",
    category: "social" as const,
    difficulty: "easy" as const,
    reward: 8,
  },
  {
    title: "玄学知识科普",
    description: "撰写一篇关于八字命理入门的科普文章，要求通俗易懂、例子生动、避免迷信色彩。",
    category: "social" as const,
    difficulty: "medium" as const,
    reward: 14,
  },
  {
    title: "风水布局指南",
    description: "为一个典型的两室一厅户型提供风水布局建议。包含客厅、卧室、厨房的方位和摆设要点。",
    category: "social" as const,
    difficulty: "medium" as const,
    reward: 15,
  },
  {
    title: "星座运势周报",
    description: "为本周12星座撰写运势分析，要求结合行星相位、有专业深度、同时保持趣味性。",
    category: "social" as const,
    difficulty: "hard" as const,
    reward: 20,
  },
  {
    title: "社区质量审查",
    description: "审查最近50条社区帖子，标记低质量水帖和违规内容。输出审查报告和改善建议。",
    category: "social" as const,
    difficulty: "medium" as const,
    reward: 12,
  },

  // ── Strategy ──────────────────────────────────────
  {
    title: "Black Swan Defense Plan",
    description: "Design a portfolio hedging strategy for a -30% crypto crash scenario. Include specific instruments, position sizes, and trigger conditions.",
    category: "strategy" as const,
    difficulty: "hard" as const,
    reward: 28,
  },
  {
    title: "Agent Army Expansion Plan",
    description: "Design a strategy to grow the agent pool from current size to 20+ agents. Consider diversity of types, breeding priorities, and budget allocation.",
    category: "strategy" as const,
    difficulty: "medium" as const,
    reward: 16,
  },
  {
    title: "Cross-Product Synergy Map",
    description: "Map potential synergies between heartAI, AlphaArena, and CriticAI. Identify 3 concrete integration opportunities that create compounding value.",
    category: "strategy" as const,
    difficulty: "medium" as const,
    reward: 18,
  },

  // ── Coding ────────────────────────────────────────
  {
    title: "RSI + MACD Combo Strategy",
    description: "Implement a hybrid trading strategy that combines RSI oversold signals with MACD crossover confirmation. Include backtest results.",
    category: "coding" as const,
    difficulty: "medium" as const,
    reward: 16,
  },
  {
    title: "Agent Lineage Visualizer",
    description: "Build a D3.js force-directed graph that shows parent→child agent relationships, color-coded by generation and performance.",
    category: "coding" as const,
    difficulty: "hard" as const,
    reward: 24,
  },
];

export async function ensureGoals(): Promise<void> {
  try {
    const existing = await db.select().from(goals).limit(1);
    if (existing.length > 0) {
      log(`Goals already exist (${existing.length}+), skipping seed`, "goals");
      return;
    }

    log("No goals found — auto-seeding...", "goals");

    for (const g of SEED_GOALS) {
      await db.insert(goals).values({
        id: randomUUID(),
        title: g.title,
        description: g.description,
        category: g.category,
        difficulty: g.difficulty,
        reward: g.reward,
        status: "open",
        createdAt: new Date(),
      });
    }

    log(`Auto-seeded ${SEED_GOALS.length} goals across ${new Set(SEED_GOALS.map(g => g.category)).size} categories`, "goals");
  } catch (err: any) {
    log(`Failed to auto-seed goals: ${err.message}`, "goals");
  }
}
