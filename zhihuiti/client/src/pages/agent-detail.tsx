import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "wouter";
import { apiRequest } from "@/lib/queryClient";
import {
  agentTypeBadgeClass, agentTypeLabel, statusBadgeClass, statusDotClass,
  formatReturn, formatDateTime, pnlColor,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Play, Pause, Square, Link2, FileText, TrendingUp, Hash, BarChart3 } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useState } from "react";

export default function AgentDetailPage() {
  const params = useParams<{ id: string }>();
  const agentId = params.id;
  const qc = useQueryClient();

  const [bindOpen, setBindOpen] = useState(false);
  const [bindProductId, setBindProductId] = useState("");
  const [bindError, setBindError] = useState("");

  const { data: agentData, isLoading } = useQuery<any>({
    queryKey: ["/api/agents", agentId],
  });

  const { data: logs, isLoading: logsLoading } = useQuery<any[]>({
    queryKey: ["/api/agents", agentId, "logs"],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/agents/${agentId}/logs?limit=20`);
      return res.json();
    },
  });

  const { data: products } = useQuery<any[]>({
    queryKey: ["/api/products"],
  });

  const startMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", `/api/agents/${agentId}/start`);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/agents", agentId] }),
  });

  const pauseMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", `/api/agents/${agentId}/pause`);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/agents", agentId] }),
  });

  const stopMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("PUT", `/api/agents/${agentId}`, { status: "stopped" });
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/agents", agentId] }),
  });

  const bindMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", `/api/agents/${agentId}/bind`, { productId: bindProductId });
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/agents", agentId] });
      setBindOpen(false);
      setBindProductId("");
      setBindError("");
    },
    onError: (err: any) => setBindError(err.message ?? "Failed to bind"),
  });

  if (isLoading) {
    return (
      <div className="p-6 lg:p-10 max-w-7xl space-y-6">
        <Skeleton className="h-24 w-full" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
        <Skeleton className="h-56 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!agentData) {
    return <div className="p-10 text-center text-muted-foreground">Agent not found</div>;
  }

  const { strategy, recentLogs, metrics } = agentData;
  const agent = agentData as any;

  // Latest metrics
  const latestMetrics = metrics?.[0] ?? null;

  // Chart data: totalReturn over time from metrics
  const chartData = (metrics ?? []).slice().reverse().map((m: any, i: number) => ({
    t: m.date ?? i,
    return: (m.totalReturn ?? 0) * 100,
  }));

  const infoCards = [
    {
      label: "Strategy",
      value: strategy?.name ?? "None",
      icon: FileText,
      color: "text-cyan-400",
    },
    {
      label: "Trades",
      value: latestMetrics?.tradeCount ?? 0,
      icon: Hash,
      color: "text-purple-400",
    },
    {
      label: "Total Return",
      value: latestMetrics ? formatReturn(latestMetrics.totalReturn ?? 0) : "—",
      icon: TrendingUp,
      color: pnlColor(latestMetrics?.totalReturn ?? 0),
      mono: true,
    },
    {
      label: "Sharpe Ratio",
      value: latestMetrics?.sharpe != null ? latestMetrics.sharpe.toFixed(2) : "—",
      icon: BarChart3,
      color: "text-amber-400",
      mono: true,
    },
  ];

  return (
    <div className="p-6 lg:p-10 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight">{agent.name}</h1>
            <Badge variant="outline" className={`text-xs ${agentTypeBadgeClass(agent.type)}`}>
              {agentTypeLabel(agent.type)}
            </Badge>
            <Badge variant="outline" className={`text-xs ${statusBadgeClass(agent.status)}`}>
              <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${statusDotClass(agent.status)}`} />
              {agent.status}
            </Badge>
          </div>
          {agent.description && (
            <p className="text-sm text-muted-foreground">{agent.description}</p>
          )}
        </div>
        <div className="flex gap-2 flex-shrink-0">
          {agent.status !== "active" && (
            <Button
              size="sm"
              className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
              variant="outline"
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
            >
              <Play className="w-3.5 h-3.5 mr-1" />
              Start
            </Button>
          )}
          {agent.status === "active" && (
            <Button
              size="sm"
              variant="outline"
              className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
            >
              <Pause className="w-3.5 h-3.5 mr-1" />
              Pause
            </Button>
          )}
          {agent.status !== "stopped" && (
            <Button
              size="sm"
              variant="outline"
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
            >
              <Square className="w-3.5 h-3.5 mr-1" />
              Stop
            </Button>
          )}
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {infoCards.map((card, i) => (
          <Card key={i} className="bg-card/50 border-card-border">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-1.5">
                <card.icon className={`w-3.5 h-3.5 ${card.color}`} />
                <span className="text-xs text-muted-foreground">{card.label}</span>
              </div>
              <div className={`text-lg font-semibold ${card.mono ? "font-mono" : ""} ${card.color === "text-cyan-400" ? "" : card.color}`}>
                {card.value}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Performance Chart */}
      {chartData.length > 1 && (
        <Card className="bg-card/50 border-card-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Return Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="t"
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={v => `${v.toFixed(1)}%`}
                />
                <Tooltip
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "6px", fontSize: 12 }}
                  labelStyle={{ color: "hsl(var(--muted-foreground))" }}
                  formatter={(v: any) => [`${(v as number).toFixed(2)}%`, "Return"]}
                />
                <Line
                  type="monotone"
                  dataKey="return"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Execution Logs */}
        <Card className="bg-card/50 border-card-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FileText className="w-4 h-4 text-muted-foreground" />
              Execution Logs
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {logsLoading ? (
              <div className="p-4 space-y-2">
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-8" />)}
              </div>
            ) : !logs || logs.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">No logs yet</div>
            ) : (
              <div className="overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-card-border text-muted-foreground">
                      <th className="text-left py-2 px-4 font-medium">Action</th>
                      <th className="text-left py-2 px-4 font-medium">Details</th>
                      <th className="text-right py-2 px-4 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(logs ?? []).map((log: any) => (
                      <tr key={log.id} className="border-b border-card-border/50">
                        <td className="py-2 px-4 font-mono text-cyan-400/80">{log.action}</td>
                        <td className="py-2 px-4 text-muted-foreground max-w-32 truncate">{log.details}</td>
                        <td className="py-2 px-4 text-right text-muted-foreground">
                          {formatDateTime(log.timestamp)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Product Bindings */}
        <Card className="bg-card/50 border-card-border">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Link2 className="w-4 h-4 text-muted-foreground" />
                Product Bindings
              </CardTitle>
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2 text-xs border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10"
                onClick={() => setBindOpen(true)}
              >
                Bind Product
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {!products || products.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">No products available</div>
            ) : (
              <div className="space-y-2">
                {products.map((p: any) => (
                  <div key={p.id} className="flex items-center justify-between px-3 py-2.5 rounded-md bg-background border border-border">
                    <div>
                      <p className="text-sm font-medium">{p.name}</p>
                      {p.description && <p className="text-xs text-muted-foreground mt-0.5">{p.description}</p>}
                    </div>
                    <Badge variant="outline" className={`text-[10px] ${p.status === "active" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/20" : "bg-muted text-muted-foreground"}`}>
                      {p.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bind Product Dialog */}
      <Dialog open={bindOpen} onOpenChange={setBindOpen}>
        <DialogContent className="bg-card border-card-border max-w-sm">
          <DialogHeader>
            <DialogTitle>Bind to Product</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            {bindError && (
              <div className="px-3 py-2 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                {bindError}
              </div>
            )}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Product</label>
              <select
                value={bindProductId}
                onChange={e => setBindProductId(e.target.value)}
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="">— Select product —</option>
                {(products ?? []).map((p: any) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => { setBindOpen(false); setBindError(""); }}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
                onClick={() => bindMutation.mutate()}
                disabled={!bindProductId || bindMutation.isPending}
              >
                {bindMutation.isPending ? "Binding..." : "Bind"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
