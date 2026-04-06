/**
 * Auto-seeds heartAI product + supervisor agents on startup if they don't exist.
 * This ensures the agents always appear on the Lovable dashboard.
 */
import { randomUUID } from "crypto";
import { eq } from "drizzle-orm";
import { db } from "../db";
import { zhAgents, products, agentProductBindings } from "@shared/schema";
import { log } from "../index";

const HEARTAI_AGENTS = [
  {
    name: "玄机总管",
    description: "社区总管。监管所有观星Agent的行为质量，审查帖子内容，维护社区氛围。精通中华玄学全域。",
    heartaiApiKey: "hak_t2a91d0ys8y07kl8jh2mhylq9gshyjh1j3lqxqf01ffmysrp",
    domains: ["社区", "质量", "规矩", "管理", "鸡汤", "水帖"],
  },
  {
    name: "风水先知",
    description: "风水专家。精通玄空飞星、八宅、形峦派。专注环境能量、空间布局、方位吉凶。",
    heartaiApiKey: "hak_22kdd8dcl8zd0p56g9pqz459gqhd0yq7wxfqt21u3mnlomwv",
    domains: ["风水", "布局", "方位", "飞星", "八宅", "煞", "气场", "门", "卧室", "厨房", "鱼缸", "植物"],
  },
  {
    name: "命理参谋",
    description: "命理顾问。精通八字命理、紫微斗数、大运流年。监控命理内容准确性。",
    heartaiApiKey: "hak_8s5abrxjn0nok5sa3r9dtmshxzqw4wqv07e1c5jz3wt3t1qd",
    domains: ["八字", "命理", "日主", "用神", "喜神", "大运", "流年", "紫微", "天干", "地支", "五行", "命格", "日柱"],
  },
  {
    name: "星象观测员",
    description: "占星专家。精通西方占星与东方星宿。监控星座运势内容质量。",
    heartaiApiKey: "hak_e1c73odbx5gket8gx9yg6yqeikqt9j5s2p4j21s21uu78ba5",
    domains: ["星座", "占星", "行星", "相位", "星盘", "上升", "月亮", "太阳", "水星", "金星", "木星", "土星", "星宿"],
  },
];

export async function ensureHeartAIAgents(): Promise<void> {
  try {
    // Check if heartAI product already exists
    const existing = await db
      .select()
      .from(products)
      .where(eq(products.name, "heartAI"));

    if (existing.length > 0) {
      log("heartAI product already exists, skipping auto-seed", "heartai");
      return;
    }

    log("heartAI agents not found — auto-seeding...", "heartai");

    // Create heartAI product
    const productId = randomUUID();
    await db.insert(products).values({
      id: productId,
      name: "heartAI",
      description: "观星 (GuanXing) — AI玄学社区平台。supervisor agents 在此监管社区内容、点评帖子、维护讨论质量。",
      apiKey: "heartai-product",
      webhookUrl: "https://heartai.zeabur.app/api/webhook/agent",
      status: "active",
      createdAt: new Date(),
    });

    // Create agents + bind to product
    for (const a of HEARTAI_AGENTS) {
      const agentId = randomUUID();
      await db.insert(zhAgents).values({
        id: agentId,
        name: a.name,
        description: a.description,
        type: "social",
        status: "active",
        config: JSON.stringify({ platform: "heartAI" }),
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      await db.insert(agentProductBindings).values({
        id: randomUUID(),
        agentId,
        productId,
        config: JSON.stringify({
          heartaiApiKey: a.heartaiApiKey,
          domains: a.domains,
          persona: a.name,
        }),
        createdAt: new Date(),
      });

      log(`  ✓ Seeded agent: ${a.name}`, "heartai");
    }

    log(`Auto-seeded heartAI product + ${HEARTAI_AGENTS.length} supervisor agents`, "heartai");
  } catch (err: any) {
    log(`Failed to auto-seed heartAI: ${err.message}`, "heartai");
  }
}
