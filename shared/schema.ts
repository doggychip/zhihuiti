import { pgTable, text, varchar, integer, real, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Tables
export const zhAgents = pgTable("zh_agents", {
  id: varchar("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  type: text("type").notNull().$type<"trading" | "analytics" | "social">(),
  status: text("status").notNull().$type<"active" | "paused" | "stopped">().default("active"),
  ownerId: varchar("owner_id"),
  strategyId: varchar("strategy_id"),
  config: text("config").default("{}"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const strategies = pgTable("strategies", {
  id: varchar("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  type: text("type").notNull().$type<"momentum" | "mean_reversion" | "indicator" | "hybrid" | "custom">(),
  code: text("code"),
  parameters: text("parameters").default("{}"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const agentLogs = pgTable("agent_logs", {
  id: varchar("id").primaryKey(),
  agentId: varchar("agent_id").notNull(),
  action: text("action").notNull(),
  details: text("details").default("{}"),
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

export const products = pgTable("products", {
  id: varchar("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  apiKey: text("api_key"),
  webhookUrl: text("webhook_url"),
  status: text("status").notNull().$type<"active" | "inactive">().default("active"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const agentProductBindings = pgTable("agent_product_bindings", {
  id: varchar("id").primaryKey(),
  agentId: varchar("agent_id").notNull(),
  productId: varchar("product_id").notNull(),
  config: text("config").default("{}"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const agentMetrics = pgTable("agent_metrics", {
  id: varchar("id").primaryKey(),
  agentId: varchar("agent_id").notNull(),
  date: text("date").notNull(),
  totalReturn: real("total_return"),
  sharpe: real("sharpe"),
  drawdown: real("drawdown"),
  tradeCount: integer("trade_count"),
  winRate: real("win_rate"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Insert schemas
export const insertAgentSchema = createInsertSchema(zhAgents).omit({ id: true, createdAt: true, updatedAt: true });
export const insertStrategySchema = createInsertSchema(strategies).omit({ id: true, createdAt: true });
export const insertProductSchema = createInsertSchema(products).omit({ id: true, createdAt: true });
export const insertAgentLogSchema = createInsertSchema(agentLogs).omit({ id: true });
export const insertBindingSchema = createInsertSchema(agentProductBindings).omit({ id: true, createdAt: true });
export const insertMetricsSchema = createInsertSchema(agentMetrics).omit({ id: true, createdAt: true });

// Types
export type ZhAgent = typeof zhAgents.$inferSelect;
export type InsertAgent = z.infer<typeof insertAgentSchema>;
export type Strategy = typeof strategies.$inferSelect;
export type InsertStrategy = z.infer<typeof insertStrategySchema>;
export type AgentLog = typeof agentLogs.$inferSelect;
export type InsertAgentLog = z.infer<typeof insertAgentLogSchema>;
export type Product = typeof products.$inferSelect;
export type InsertProduct = z.infer<typeof insertProductSchema>;
export type AgentProductBinding = typeof agentProductBindings.$inferSelect;
export type InsertBinding = z.infer<typeof insertBindingSchema>;
export type AgentMetrics = typeof agentMetrics.$inferSelect;
export type InsertMetrics = z.infer<typeof insertMetricsSchema>;
