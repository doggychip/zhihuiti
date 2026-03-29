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

/**
 * Proxy a request to the zhihuiti Python API server.
 *
 * Set ZHIHUITI_API_URL env var to the base URL of the zhihuiti API server.
 * Example: ZHIHUITI_API_URL=https://your-zhihuiti.fly.dev
 *
 * Falls back to http://localhost:8377 for local development.
 */
const ZHIHUITI_API = (process.env.ZHIHUITI_API_URL || "http://localhost:8377").replace(/\/$/, "");

async function oracleProxy(path: string, options?: { method?: string; body?: any }): Promise<any> {
  const url = `${ZHIHUITI_API}${path}`;
  const method = options?.method || "GET";
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  const fetchOptions: RequestInit = { method, headers };
  if (options?.body) {
    fetchOptions.body = JSON.stringify(options.body);
  }

  const resp = await fetch(url, fetchOptions);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`zhihuiti API ${resp.status}: ${text.slice(0, 200)}`);
  }
  return resp.json();
}

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

  // === ORACLE ===
  // Proxied to zhihuiti Python API server (ZHIHUITI_API_URL env var)

  app.get("/api/oracle/scan", async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.timeframe) qs.set("timeframe", req.query.timeframe as string);
      if (req.query.pairs) qs.set("pairs", req.query.pairs as string);
      const result = await oracleProxy(`/api/oracle/scan?${qs}`);
      res.json(result);
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  app.get("/api/oracle/crypto/:instrument", async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.timeframe) qs.set("timeframe", req.query.timeframe as string);
      if (req.query.book) qs.set("book", req.query.book as string);
      const result = await oracleProxy(`/api/oracle/crypto/${req.params.instrument}?${qs}`);
      res.json(result);
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  app.get("/api/oracle/domains", async (_req, res) => {
    try {
      res.json(await oracleProxy("/api/oracle/domains"));
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  app.get("/api/oracle/theories/stats", async (_req, res) => {
    try {
      res.json(await oracleProxy("/api/oracle/theories/stats"));
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  app.get("/api/oracle/theories/search", async (req, res) => {
    try {
      const q = req.query.q as string;
      if (!q) return res.status(400).json({ error: "query parameter 'q' is required" });
      const limit = req.query.limit || "10";
      res.json(await oracleProxy(`/api/oracle/theories/search?q=${encodeURIComponent(q)}&limit=${limit}`));
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  app.post("/api/oracle/diagnose", async (req, res) => {
    try {
      const { values, domain, label } = req.body;
      if (!values || !Array.isArray(values) || values.length < 5) {
        return res.status(400).json({ error: "need at least 5 data points in 'values'" });
      }
      const result = await oracleProxy("/api/oracle/diagnose", {
        method: "POST",
        body: { values, domain: domain || "scientific", label: label || "time series" },
      });
      res.json(result);
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  app.get("/api/oracle/summary", async (_req, res) => {
    try {
      res.json(await oracleProxy("/api/oracle/summary"));
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  app.get("/api/oracle/transitions", async (req, res) => {
    try {
      const qs = new URLSearchParams();
      if (req.query.instrument) qs.set("instrument", req.query.instrument as string);
      if (req.query.limit) qs.set("limit", req.query.limit as string);
      res.json(await oracleProxy(`/api/oracle/transitions?${qs}`));
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  app.get("/api/oracle/history/:instrument", async (req, res) => {
    try {
      const limit = req.query.limit || "50";
      res.json(await oracleProxy(`/api/oracle/history/${req.params.instrument}?limit=${limit}`));
    } catch (err: any) {
      res.status(502).json({ error: `Oracle unavailable: ${err.message}` });
    }
  });

  return httpServer;
}
