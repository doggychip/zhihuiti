import { useQuery } from "@tanstack/react-query";
import { formatReturn, formatCurrency, pnlColor, agentTypeBadgeClass, agentTypeLabel } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DollarSign, TrendingUp, TrendingDown, Activity } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

export default function AnalyticsPage() {
  const { data: analytics, isLoading: analyticsLoading } = useQuery<any>({
    queryKey: ["/api/analytics"],
  });

  const { data: agents, isLoading: agentsLoading } = useQuery<any[]>({
    queryKey: ["/api/agents"],
  });

  const isLoading = analyticsLoading || agentsLoading;

  // Agents with metrics for comparison chart
  const agentsWithMetrics = (agents ?? [])
    .filter((a: any) => a.latestMetrics != null)
    .sort((a: any, b: any) => (b.latestMetrics?.totalReturn ?? 0) - (a.latestMetrics?.totalReturn ?? 0))
    .slice(0, 10);

  const chartData = agentsWithMetrics.map((a: any) => ({
    name: a.name.length > 14 ? a.name.slice(0, 14) + "…" : a.name,
    return: parseFloat(((a.latestMetrics?.totalReturn ?? 0) * 100).toFixed(2)),
    type: a.type,
  }));

  // Best / worst agent
  const bestAgent = agentsWithMetrics[0] ?? null;
  const worstAgent = agentsWithMetrics[agentsWithMetrics.length - 1] ?? null;

  // Avg sharpe
  const sharpeValues = (agents ?? [])
    .filter((a: any) => a.latestMetrics?.sharpe != null)
    .map((a: any) => a.latestMetrics.sharpe as number);
  const avgSharpe = sharpeValues.length > 0
    ? sharpeValues.reduce((s, v) => s + v, 0) / sharpeValues.length
    : null;

  const statCards = [
    {
      label: "Total P&L",
      value: analyticsLoading ? null : formatCurrency(analytics?.totalPnl ?? 0),
      icon: DollarSign,
      color: pnlColor(analytics?.totalPnl ?? 0),
      mono: true,
    },
    {
      label: "Best Agent",
      value: agentsLoading ? null : (bestAgent?.name ?? "—"),
      icon: TrendingUp,
      color: "text-emerald-400",
      mono: false,
    },
    {
      label: "Worst Agent",
      value: agentsLoading ? null : (worstAgent?.name ?? "—"),
      icon: TrendingDown,
      color: "text-red-400",
      mono: false,
    },
    {
      label: "Avg Sharpe",
      value: agentsLoading ? null : (avgSharpe != null ? avgSharpe.toFixed(2) : "—"),
      icon: Activity,
      color: "text-amber-400",
      mono: true,
    },
  ];

  return (
    <div className="p-6 lg:p-10 max-w-7xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Platform-wide performance overview</p>
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
                <Skeleton className="h-6 w-24" />
              ) : (
                <div className={`text-lg font-semibold ${stat.mono ? "font-mono" : ""} ${stat.color}`}>
                  {stat.value}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Agent Performance Comparison */}
      <Card className="bg-card/50 border-card-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Agent Performance Comparison (Top 10)</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : chartData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
              No agent metrics available yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 16, right: 24, top: 4, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={v => `${v}%`}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={100}
                  tick={{ fontSize: 11, fill: "hsl(var(--foreground))" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "6px",
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "hsl(var(--muted-foreground))" }}
                  formatter={(v: any) => [`${(v as number).toFixed(2)}%`, "Return"]}
                />
                <Bar dataKey="return" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.return >= 0 ? "#10b981" : "#ef4444"}
                      opacity={0.85}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Agent Breakdown Table */}
      {!isLoading && agentsWithMetrics.length > 0 && (
        <Card className="bg-card/50 border-card-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Agent Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-card-border text-muted-foreground text-xs">
                  <th className="text-left py-2.5 px-4 font-medium">Agent</th>
                  <th className="text-left py-2.5 px-4 font-medium hidden md:table-cell">Type</th>
                  <th className="text-right py-2.5 px-4 font-medium">Return</th>
                  <th className="text-right py-2.5 px-4 font-medium hidden lg:table-cell">Sharpe</th>
                  <th className="text-right py-2.5 px-4 font-medium hidden lg:table-cell">Win Rate</th>
                  <th className="text-right py-2.5 px-4 font-medium">Trades</th>
                </tr>
              </thead>
              <tbody>
                {agentsWithMetrics.map((agent: any) => (
                  <tr key={agent.id} className="border-b border-card-border/50 hover:bg-accent/30 transition-colors">
                    <td className="py-2.5 px-4">
                      <span className="font-medium">{agent.name}</span>
                    </td>
                    <td className="py-2.5 px-4 hidden md:table-cell">
                      <Badge variant="outline" className={`text-[10px] ${agentTypeBadgeClass(agent.type)}`}>
                        {agentTypeLabel(agent.type)}
                      </Badge>
                    </td>
                    <td className={`py-2.5 px-4 text-right font-mono text-xs ${pnlColor(agent.latestMetrics.totalReturn ?? 0)}`}>
                      {formatReturn(agent.latestMetrics.totalReturn ?? 0)}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-xs text-muted-foreground hidden lg:table-cell">
                      {agent.latestMetrics.sharpe != null ? agent.latestMetrics.sharpe.toFixed(2) : "—"}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-xs text-muted-foreground hidden lg:table-cell">
                      {agent.latestMetrics.winRate != null ? `${(agent.latestMetrics.winRate * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-xs text-muted-foreground">
                      {agent.latestMetrics.tradeCount ?? 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
