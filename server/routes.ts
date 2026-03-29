import type { Express } from "express";
import { createServer, type Server } from "http";
import { randomUUID } from "crypto";
import { execFile } from "child_process";
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
 * Run a Python oracle command and return the parsed JSON result.
 * The Python script dispatches based on the `command` argument.
 */
function runPythonOracle(command: string, args: Record<string, any>): Promise<any> {
  return new Promise((resolve, reject) => {
    const script = `
import sys, json
args = json.loads(sys.argv[2])
cmd = sys.argv[1]

if cmd == "scan":
    from zhihuiti.scanner import scan_instruments
    results = scan_instruments(
        instruments=args.get("pairs", "").split(",") if args.get("pairs") else None,
        timeframe=args.get("timeframe", "4h"),
    )
    from zhihuiti.scanner import RegimeHistory
    history = RegimeHistory()
    transitions = history.record_scan(results)
    print(json.dumps({
        "results": [r.to_dict() for r in results],
        "count": len(results),
        "transitions": [t.to_dict() for t in transitions],
    }))

elif cmd == "crypto":
    from zhihuiti.crypto_oracle import diagnose_market
    from zhihuiti.api import _fetch_crypto_candles, _fetch_crypto_book
    candles = _fetch_crypto_candles(args["instrument"], args.get("timeframe", "4h"))
    book = _fetch_crypto_book(args["instrument"]) if args.get("book") else None
    if not candles:
        print(json.dumps({"error": "no candle data"}))
    else:
        diag = diagnose_market(candles, instrument=args["instrument"], book=book)
        print(json.dumps(diag.to_dict()))

elif cmd == "domains":
    from zhihuiti.universal_oracle import DOMAINS
    domains = {}
    for key, profile in DOMAINS.items():
        domains[key] = {"name": profile.name, "description": profile.description,
                        "pattern_count": len(profile.pattern_theories),
                        "regime_count": len(profile.regime_theories)}
    print(json.dumps({"domains": domains}))

elif cmd == "theory_stats":
    from zhihuiti.theory_intelligence import get_graph
    print(json.dumps(get_graph().get_stats()))

elif cmd == "theory_search":
    from zhihuiti.theory_intelligence import get_graph
    results = get_graph().search_theories(args["q"], limit=args.get("limit", 10))
    compact = [{"id": r["id"], "name": r.get("name", ""), "domain": r.get("domain", "")} for r in results]
    print(json.dumps({"results": compact, "count": len(compact)}))

elif cmd == "diagnose":
    from zhihuiti.universal_oracle import diagnose
    result = diagnose(args["values"], domain=args.get("domain", "scientific"), label=args.get("label", "time series"))
    print(json.dumps(result.to_dict()))

elif cmd == "summary":
    from zhihuiti.scanner import RegimeHistory
    history = RegimeHistory()
    summary = history.get_summary()
    print(json.dumps({"instruments": summary, "count": len(summary)}))

elif cmd == "transitions":
    from zhihuiti.scanner import RegimeHistory
    history = RegimeHistory()
    transitions = history.get_transitions(instrument=args.get("instrument") or None, limit=args.get("limit", 20))
    print(json.dumps({"transitions": transitions, "count": len(transitions)}))

elif cmd == "history":
    from zhihuiti.scanner import RegimeHistory
    history = RegimeHistory()
    snapshots = history.get_history(args["instrument"], limit=args.get("limit", 50))
    print(json.dumps({"instrument": args["instrument"], "snapshots": snapshots, "count": len(snapshots)}))
`;

    execFile("python3", ["-c", script, command, JSON.stringify(args)], {
      timeout: 30000,
      maxBuffer: 1024 * 1024,
    }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(stderr || error.message));
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim()));
      } catch {
        reject(new Error(`Invalid JSON from oracle: ${stdout.slice(0, 200)}`));
      }
    });
  });
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
  // These endpoints call the Python oracle via child_process

  app.get("/api/oracle/scan", async (req, res) => {
    try {
      const timeframe = (req.query.timeframe as string) || "4h";
      const pairs = (req.query.pairs as string) || "";
      const result = await runPythonOracle("scan", { timeframe, pairs });
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/oracle/crypto/:instrument", async (req, res) => {
    try {
      const instrument = req.params.instrument;
      const timeframe = (req.query.timeframe as string) || "4h";
      const book = req.query.book === "1" || req.query.book === "true";
      const result = await runPythonOracle("crypto", { instrument, timeframe, book });
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/oracle/domains", async (_req, res) => {
    try {
      const result = await runPythonOracle("domains", {});
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/oracle/theories/stats", async (_req, res) => {
    try {
      const result = await runPythonOracle("theory_stats", {});
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/oracle/theories/search", async (req, res) => {
    try {
      const q = (req.query.q as string) || "";
      const limit = parseInt(req.query.limit as string) || 10;
      if (!q) return res.status(400).json({ error: "query parameter 'q' is required" });
      const result = await runPythonOracle("theory_search", { q, limit });
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/oracle/diagnose", async (req, res) => {
    try {
      const { values, domain, label } = req.body;
      if (!values || !Array.isArray(values) || values.length < 5) {
        return res.status(400).json({ error: "need at least 5 data points in 'values'" });
      }
      const result = await runPythonOracle("diagnose", {
        values, domain: domain || "scientific", label: label || "time series",
      });
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/oracle/summary", async (_req, res) => {
    try {
      const result = await runPythonOracle("summary", {});
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/oracle/transitions", async (req, res) => {
    try {
      const instrument = (req.query.instrument as string) || "";
      const limit = parseInt(req.query.limit as string) || 20;
      const result = await runPythonOracle("transitions", { instrument, limit });
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/oracle/history/:instrument", async (req, res) => {
    try {
      const instrument = req.params.instrument;
      const limit = parseInt(req.query.limit as string) || 50;
      const result = await runPythonOracle("history", { instrument, limit });
      res.json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  return httpServer;
}
