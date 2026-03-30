import { randomUUID } from "crypto";
import { eq } from "drizzle-orm";
import { db } from "../db";
import { zhAgents, agentProductBindings } from "@shared/schema";
import type { ZhAgent, InsertAgent } from "@shared/schema";
import { emit } from "./eventBus";

export async function getAllAgents(): Promise<ZhAgent[]> {
  return db.select().from(zhAgents).orderBy(zhAgents.createdAt);
}

export async function getAgent(id: string): Promise<ZhAgent | undefined> {
  const rows = await db.select().from(zhAgents).where(eq(zhAgents.id, id));
  return rows[0];
}

export async function createAgent(data: InsertAgent): Promise<ZhAgent> {
  const id = randomUUID();
  const now = new Date();
  const [agent] = await db
    .insert(zhAgents)
    .values({ ...data, id, createdAt: now, updatedAt: now })
    .returning();
  emit("agent.created", agent);
  return agent;
}

export async function updateAgent(
  id: string,
  updates: Partial<ZhAgent>,
): Promise<ZhAgent | undefined> {
  const [updated] = await db
    .update(zhAgents)
    .set({ ...updates, updatedAt: new Date() })
    .where(eq(zhAgents.id, id))
    .returning();
  return updated;
}

export async function deleteAgent(id: string): Promise<void> {
  await db.delete(zhAgents).where(eq(zhAgents.id, id));
}

export async function startAgent(id: string): Promise<ZhAgent | undefined> {
  const agent = await updateAgent(id, { status: "active" });
  if (agent) emit("agent.started", agent);
  return agent;
}

export async function pauseAgent(id: string): Promise<ZhAgent | undefined> {
  const agent = await updateAgent(id, { status: "paused" });
  if (agent) emit("agent.paused", agent);
  return agent;
}

export async function stopAgent(id: string): Promise<ZhAgent | undefined> {
  const agent = await updateAgent(id, { status: "stopped" });
  if (agent) emit("agent.stopped", agent);
  return agent;
}

export async function getAgentsByProduct(productId: string): Promise<ZhAgent[]> {
  const bindings = await db
    .select()
    .from(agentProductBindings)
    .where(eq(agentProductBindings.productId, productId));

  if (bindings.length === 0) return [];

  const agentIds = bindings.map((b) => b.agentId);
  const agents = await db.select().from(zhAgents);
  return agents.filter((a) => agentIds.includes(a.id));
}
