import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { formatCurrency, formatReturn, pnlColor, agentTypeBadgeClass, agentTypeLabel, statusDotClass, formatRelativeTime } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Bot, BarChart3, Activity, Package, ArrowRight, TrendingUp } from "lucide-react";

export default function DashboardPage() {
  const { data: analytics, isLoading: analyticsLoading } = useQuery<any>({
    queryKey: ["/api/analytics"],
  });

  const { data: agents, isLoading: agentsLoading } = useQuery<any[]>({
    queryKey: ["/api/agents"],
  });

  const { data: products, isLoading: productsLoading } = useQuery<any[]>({
    queryKey: ["/api/products"],
  });

  const { data: pricesData } = useQuery<any>({
    queryKey: ["/api/data/prices"],
    refetchInterval: 10000,
  });

  const prices: any[] = pricesData?.prices ?? [];
  const isLive: boolean = pricesData?.isLive ?? false;

  const statCards = [
    {
      label: "Total Agents",
      value: analyticsLoading ? null : (analytics?.totalAgents ?? 0),
      icon: Bot,
      color: "text-cyan-400",
    },
    {
      label: "Active Agents",
      value: analyticsLoading ? null : (analytics?.activeAgents ?? 0),
      icon: Activity,
      color: "text-emerald-400",
    },
    {
      label: "Total Trades",
      value: analyticsLoading ? null : (analytics?.totalTrades ?? 0),
      icon: BarChart3,
      color: "text-purple-400",
    },
    {
      label: "Products",
      value: productsLoading ? null : (products?.length ?? 0),
      icon: Package,
      color: "text-amber-400",
    },
  ];

  return (
    <div className="grid-pattern min-h-screen">
      <div className="p-6 lg:p-10 max-w-7xl space-y-6">
        {/* Header */}
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            AI Agent Platform
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold tracking-tight">
            Big Brain <span className="text-cyan-400">Dashboard</span>
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Monitor and manage your AI agents across all connected products.
          </p>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {statCards.map((stat, i) => (
            <Card key={i} className="bg-card/50 border-card-border">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <stat.icon className={`w-4 h-4 ${stat.color}`} />
                  <span className="text-xs text-muted-foreground">{stat.label}</span>
                </div>
                {stat.value === null ? (
                  <Skeleton className="h-7 w-16" />
                ) : (
                  <div className="font-mono text-2xl font-semibold">{stat.value}</div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Price Ticker */}
        {prices.length > 0 && (
          <section>
            <div className="flex items-center gap-3 mb-2">
              <span
                className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  isLive
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${isLive ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
                {isLive ? "LIVE PRICES" : "SIMULATED"}
              </span>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {prices.map((p: any) => (
                <div key={p.pair} className="flex-shrink-0 flex items-center gap-3 px-3 py-2 rounded-lg bg-card/50 border border-card-border">
                  <span className="text-xs font-medium text-foreground">{p.pair.replace("/USD", "")}</span>
                  <span className="font-mono text-xs text-foreground">{formatCurrency(p.price)}</span>
                  <span className={`font-mono text-xs ${p.change24h >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {p.change24h >= 0 ? "+" : ""}{p.change24h.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recent Agent Activity */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <h2 className="text-base font-semibold">Recent Agent Activity</h2>
            </div>
            <Link href="/agents">
              <button className="text-sm text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium">
                All Agents <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </Link>
          </div>

          {agentsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : !agents || agents.length === 0 ? (
            <div className="rounded-lg border border-card-border bg-card/50 p-8 text-center">
              <Bot className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No agents yet.</p>
              <Link href="/agents">
                <button className="mt-3 text-xs text-cyan-400 hover:text-cyan-300 font-medium">
                  Create your first agent →
                </button>
              </Link>
            </div>
          ) : (
            <div className="rounded-lg border border-card-border bg-card/50 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-card-border text-muted-foreground text-xs">
                    <th className="text-left py-2.5 px-4 font-medium">Agent</th>
                    <th className="text-left py-2.5 px-4 font-medium hidden md:table-cell">Type</th>
                    <th className="text-left py-2.5 px-4 font-medium">Status</th>
                    <th className="text-right py-2.5 px-4 font-medium hidden lg:table-cell">Return</th>
                    <th className="text-right py-2.5 px-4 font-medium hidden lg:table-cell">Trades</th>
                    <th className="text-right py-2.5 px-4 font-medium">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {(agents ?? []).slice(0, 8).map((agent: any) => (
                    <tr
                      key={agent.id}
                      className="border-b border-card-border/50 hover:bg-accent/30 transition-colors"
                    >
                      <td className="py-2.5 px-4">
                        <Link href={`/agents/${agent.id}`}>
                          <span className="font-medium hover:text-cyan-400 transition-colors cursor-pointer">
                            {agent.name}
                          </span>
                        </Link>
                      </td>
                      <td className="py-2.5 px-4 hidden md:table-cell">
                        <Badge variant="outline" className={`text-[10px] font-medium ${agentTypeBadgeClass(agent.type)}`}>
                          {agentTypeLabel(agent.type)}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className={`w-1.5 h-1.5 rounded-full ${statusDotClass(agent.status)}`} />
                          <span className="text-xs capitalize text-muted-foreground">{agent.status}</span>
                        </div>
                      </td>
                      <td className={`py-2.5 px-4 text-right font-mono text-xs hidden lg:table-cell ${pnlColor(agent.latestMetrics?.totalReturn ?? 0)}`}>
                        {agent.latestMetrics ? formatReturn(agent.latestMetrics.totalReturn ?? 0) : "—"}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-xs hidden lg:table-cell text-muted-foreground">
                        {agent.latestMetrics?.tradeCount ?? 0}
                      </td>
                      <td className="py-2.5 px-4 text-right text-xs text-muted-foreground">
                        {formatRelativeTime(agent.updatedAt)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
