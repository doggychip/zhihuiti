import express, { type Request, Response, NextFunction } from "express";
import cors from "cors";
import { registerRoutes } from "./routes";
import { serveStatic } from "./static";
import { createServer } from "http";

const app = express();
const httpServer = createServer(app);

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

export function log(message: string, source = "express") {
  const formattedTime = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  console.log(`${formattedTime} [${source}] ${message}`);
}

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }
      log(logLine);
    }
  });

  next();
});

(async () => {
  // Register all strategies
  const { registerAllStrategies } = await import("./strategies/index");
  registerAllStrategies();

  await registerRoutes(app);

  app.use((err: any, _req: Request, res: Response, next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";
    console.error("Internal Server Error:", err);
    if (res.headersSent) return next(err);
    return res.status(status).json({ message });
  });

  // Serve client in production, vite in dev
  if (process.env.NODE_ENV === "production") {
    serveStatic(app);
  } else {
    const { setupVite } = await import("./vite");
    await setupVite(httpServer, app);
  }

  // Start background jobs when DATABASE_URL is set
  if (process.env.DATABASE_URL) {
    const { startDataProvider } = await import("./core/dataProvider");
    const { startPriceHistory } = await import("./core/priceHistory");
    const { startAgentRunner } = await import("./jobs/agentRunner");
    const { startHealthCheck } = await import("./jobs/healthCheck");
    const { startAnalytics } = await import("./jobs/analytics");

    startDataProvider(30000);
    startPriceHistory(30000);
    startHealthCheck(60000);
    startAnalytics(5 * 60 * 1000);

    // Start agent runner after 60s to let price history build up
    setTimeout(() => startAgentRunner(30000), 60000);

    // Start heartAI community runner (10-minute interval)
    const { startHeartAIRunner } = await import("./jobs/heartaiRunner");
    startHeartAIRunner(10 * 60 * 1000);
  } else {
    // In dev without DB, still start price data for /api/data/prices
    const { startDataProvider } = await import("./core/dataProvider");
    const { startPriceHistory } = await import("./core/priceHistory");
    startDataProvider(30000);
    startPriceHistory(30000);
  }

  const port = parseInt(process.env.PORT || "5000", 10);
  httpServer.listen(
    {
      port,
      host: "0.0.0.0",
      reusePort: true,
    },
    () => {
      log(`serving on port ${port}`);
    },
  );
})();
