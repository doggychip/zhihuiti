import type { Express } from "express";
import { createServer, type Server } from "http";
import { randomUUID } from "crypto";
import { eq, desc } from "drizzle-orm";
import { db } from "./db";
import {
  zhAgents,
  strategies,
  agentLogs,
  products,
  agentProductBindings,
  agentMetrics,
} from "@shared/schema";
import {
  getAllAgents,
  getAgent,
  createAgent,
  updateAgent,
  deleteAgent,
  startAgent,
  pauseAgent,
  getAgentsByProduct,
} from "./core/agentRegistry";
import { getAllProducts, getProduct, createProduct } from "./products/registry";
import { getCurrentPrices } from "./core/dataProvider";
import { getPriceHistory } from "./core/priceHistory";

export async function registerRoutes(app: Express): Promise<Server> {
  const httpServer = createServer(app);

  // === AGENTS ===

  app.get("/api/agents", async (_req, res) => {
    try {
      const agents = await getAllAgents();
      // Attach latest metrics
      const result = await Promise.all(
        agents.map(async (agent) => {
          const metrics = await db
            .select()
            .from(agentMetrics)
            .where(eq(agentMetrics.agentId, agent.id))
            .orderBy(desc(agentMetrics.createdAt))
            .limit(1);
          return { ...agent, latestMetrics: metrics[0] ?? null };
        }),
      );
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/agents", async (req, res) => {
    try {
      const { name, description, type, strategyId, ownerId, config } = req.body;
      if (!name || !type) {
        return res.status(400).json({ error: "name and type are required" });
      }
      const agent = await createAgent({
        name,
        description,
        type,
        strategyId,
        ownerId,
        config: config ?? "{}",
        status: "active",
      });
      res.status(201).json(agent);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/agents/:id", async (req, res) => {
    try {
      const agent = await getAgent(req.params.id);
      if (!agent) return res.status(404).json({ error: "Agent not found" });

      // Fetch strategy
      let strategy = null;
      if (agent.strategyId) {
        const rows = await db
          .select()
          .from(strategies)
          .where(eq(strategies.id, agent.strategyId));
        strategy = rows[0] ?? null;
      }

      // Fetch recent logs
      const logs = await db
        .select()
        .from(agentLogs)
        .where(eq(agentLogs.agentId, agent.id))
        .orderBy(desc(agentLogs.timestamp))
        .limit(20);

      // Fetch metrics
      const metrics = await db
        .select()
        .from(agentMetrics)
        .where(eq(agentMetrics.agentId, agent.id))
        .orderBy(desc(agentMetrics.createdAt))
        .limit(30);

      res.json({ ...agent, strategy, recentLogs: logs, metrics });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.put("/api/agents/:id", async (req, res) => {
    try {
      const updated = await updateAgent(req.params.id, req.body);
      if (!updated) return res.status(404).json({ error: "Agent not found" });
      res.json(updated);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/agents/:id/start", async (req, res) => {
    try {
      const agent = await startAgent(req.params.id);
      if (!agent) return res.status(404).json({ error: "Agent not found" });
      res.json(agent);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/agents/:id/pause", async (req, res) => {
    try {
      const agent = await pauseAgent(req.params.id);
      if (!agent) return res.status(404).json({ error: "Agent not found" });
      res.json(agent);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/agents/:id/logs", async (req, res) => {
    try {
      const limit = parseInt(req.query.limit as string) || 50;
      const logs = await db
        .select()
        .from(agentLogs)
        .where(eq(agentLogs.agentId, req.params.id))
        .orderBy(desc(agentLogs.timestamp))
        .limit(limit);
      res.json(logs);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/agents/:id/bind", async (req, res) => {
    try {
      const { productId, config } = req.body;
      if (!productId) return res.status(400).json({ error: "productId is required" });

      const agent = await getAgent(req.params.id);
      if (!agent) return res.status(404).json({ error: "Agent not found" });

      const product = await getProduct(productId);
      if (!product) return res.status(404).json({ error: "Product not found" });

      const [binding] = await db
        .insert(agentProductBindings)
        .values({
          id: randomUUID(),
          agentId: agent.id,
          productId,
          config: config ?? "{}",
          createdAt: new Date(),
        })
        .returning();
      res.status(201).json(binding);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // === STRATEGIES ===

  app.get("/api/strategies", async (_req, res) => {
    try {
      const all = await db.select().from(strategies).orderBy(strategies.createdAt);
      res.json(all);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/strategies", async (req, res) => {
    try {
      const { name, description, type, parameters, code } = req.body;
      if (!name || !type) {
        return res.status(400).json({ error: "name and type are required" });
      }
      const [strategy] = await db
        .insert(strategies)
        .values({
          id: randomUUID(),
          name,
          description,
          type,
          code,
          parameters: parameters ?? "{}",
          createdAt: new Date(),
        })
        .returning();
      res.status(201).json(strategy);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/strategies/:id", async (req, res) => {
    try {
      const rows = await db
        .select()
        .from(strategies)
        .where(eq(strategies.id, req.params.id));
      if (rows.length === 0) return res.status(404).json({ error: "Strategy not found" });
      res.json(rows[0]);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // === PRODUCTS ===

  app.get("/api/products", async (_req, res) => {
    try {
      const all = await getAllProducts();
      res.json(all);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/products", async (req, res) => {
    try {
      const { name, description, webhookUrl, apiKey } = req.body;
      if (!name) return res.status(400).json({ error: "name is required" });
      const product = await createProduct({
        name,
        description,
        webhookUrl,
        apiKey: apiKey ?? randomUUID(),
        status: "active",
      });
      res.status(201).json(product);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/products/:id", async (req, res) => {
    try {
      const product = await getProduct(req.params.id);
      if (!product) return res.status(404).json({ error: "Product not found" });

      const boundAgents = await getAgentsByProduct(product.id);
      res.json({ ...product, boundAgents });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // === DATA ===

  app.get("/api/data/prices", (_req, res) => {
    try {
      const { prices, isLive } = getCurrentPrices();
      res.json({ prices, isLive });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/data/history/:pair", (req, res) => {
    try {
      const pair = decodeURIComponent(req.params.pair);
      const history = getPriceHistory(pair);
      res.json({ pair, prices: history });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/analytics", async (_req, res) => {
    try {
      const allAgents = await getAllAgents();
      const totalAgents = allAgents.length;
      const activeAgents = allAgents.filter((a) => a.status === "active").length;

      // Count total trade logs
      const tradeLogs = await db
        .select()
        .from(agentLogs)
        .where(eq(agentLogs.action, "trade_executed"));
      const totalTrades = tradeLogs.length;

      // Sum total P&L from metrics
      const allMetrics = await db.select().from(agentMetrics);
      const totalPnl = allMetrics.reduce((sum, m) => sum + (m.totalReturn ?? 0), 0);

      res.json({
        totalAgents,
        activeAgents,
        totalTrades,
        totalPnl,
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  return httpServer;
}
