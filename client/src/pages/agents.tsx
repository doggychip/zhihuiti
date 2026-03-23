import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "wouter";
import { apiRequest } from "@/lib/queryClient";
import { agentTypeBadgeClass, agentTypeLabel, statusDotClass, formatReturn, pnlColor } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Bot, Plus, Play, Pause, ChevronRight } from "lucide-react";
import { useState } from "react";

const AGENT_TYPES = ["trading", "analytics", "social"] as const;

export default function AgentsPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", type: "trading", strategyId: "" });
  const [error, setError] = useState("");

  const { data: agents, isLoading } = useQuery<any[]>({
    queryKey: ["/api/agents"],
  });

  const { data: strategies } = useQuery<any[]>({
    queryKey: ["/api/strategies"],
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/agents", {
        name: form.name,
        description: form.description,
        type: form.type,
        strategyId: form.strategyId || undefined,
      });
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/agents"] });
      setCreateOpen(false);
      setForm({ name: "", description: "", type: "trading", strategyId: "" });
      setError("");
    },
    onError: (err: any) => {
      setError(err.message ?? "Failed to create agent");
    },
  });

  const startMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiRequest("POST", `/api/agents/${id}/start`);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/agents"] }),
  });

  const pauseMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiRequest("POST", `/api/agents/${id}/pause`);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/agents"] }),
  });

  return (
    <div className="p-6 lg:p-10 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agents</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage and monitor your AI agents</p>
        </div>
        <Button
          onClick={() => setCreateOpen(true)}
          className="bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Create Agent
        </Button>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : !agents || agents.length === 0 ? (
        <div className="rounded-lg border border-card-border bg-card/50 p-12 text-center">
          <Bot className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <h3 className="font-semibold mb-1">No agents yet</h3>
          <p className="text-sm text-muted-foreground mb-4">Create your first agent to get started.</p>
          <Button
            onClick={() => setCreateOpen(true)}
            className="bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
          >
            <Plus className="w-4 h-4 mr-1.5" />
            Create Agent
          </Button>
        </div>
      ) : (
        <div className="rounded-lg border border-card-border bg-card/50 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-card-border text-muted-foreground text-xs">
                <th className="text-left py-3 px-4 font-medium">Status</th>
                <th className="text-left py-3 px-4 font-medium">Name</th>
                <th className="text-left py-3 px-4 font-medium hidden md:table-cell">Type</th>
                <th className="text-left py-3 px-4 font-medium hidden lg:table-cell">Strategy</th>
                <th className="text-right py-3 px-4 font-medium hidden lg:table-cell">Trades</th>
                <th className="text-right py-3 px-4 font-medium hidden md:table-cell">P&amp;L</th>
                <th className="text-right py-3 px-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent: any) => (
                <tr
                  key={agent.id}
                  className="border-b border-card-border/50 hover:bg-accent/30 transition-colors"
                >
                  <td className="py-3 px-4">
                    <span className={`inline-block w-2 h-2 rounded-full ${statusDotClass(agent.status)}`} />
                  </td>
                  <td className="py-3 px-4">
                    <Link href={`/agents/${agent.id}`}>
                      <div className="flex items-center gap-1 cursor-pointer group">
                        <span className="font-medium group-hover:text-cyan-400 transition-colors">
                          {agent.name}
                        </span>
                        <ChevronRight className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </Link>
                    {agent.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-48">{agent.description}</p>
                    )}
                  </td>
                  <td className="py-3 px-4 hidden md:table-cell">
                    <Badge variant="outline" className={`text-[10px] font-medium ${agentTypeBadgeClass(agent.type)}`}>
                      {agentTypeLabel(agent.type)}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-xs text-muted-foreground hidden lg:table-cell">
                    {agent.strategyId ? (
                      <span className="text-foreground/70">Assigned</span>
                    ) : (
                      <span className="italic">None</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-xs text-muted-foreground hidden lg:table-cell">
                    {agent.latestMetrics?.tradeCount ?? 0}
                  </td>
                  <td className={`py-3 px-4 text-right font-mono text-xs hidden md:table-cell ${pnlColor(agent.latestMetrics?.totalReturn ?? 0)}`}>
                    {agent.latestMetrics ? formatReturn(agent.latestMetrics.totalReturn ?? 0) : "—"}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex justify-end gap-1.5">
                      {agent.status === "active" ? (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 px-2 text-xs border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
                          onClick={() => pauseMutation.mutate(agent.id)}
                          disabled={pauseMutation.isPending}
                        >
                          <Pause className="w-3 h-3 mr-1" />
                          Pause
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 px-2 text-xs border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                          onClick={() => startMutation.mutate(agent.id)}
                          disabled={startMutation.isPending}
                        >
                          <Play className="w-3 h-3 mr-1" />
                          Start
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Agent Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="bg-card border-card-border max-w-md">
          <DialogHeader>
            <DialogTitle>Create Agent</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            {error && (
              <div className="px-3 py-2 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                {error}
              </div>
            )}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="My Trading Bot"
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Brief description..."
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Type *</label>
              <select
                value={form.type}
                onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              >
                {AGENT_TYPES.map(t => (
                  <option key={t} value={t}>{agentTypeLabel(t)}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Strategy</label>
              <select
                value={form.strategyId}
                onChange={e => setForm(f => ({ ...f, strategyId: e.target.value }))}
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="">— None —</option>
                {(strategies ?? []).map((s: any) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => { setCreateOpen(false); setError(""); }}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
                onClick={() => createMutation.mutate()}
                disabled={!form.name || createMutation.isPending}
              >
                {createMutation.isPending ? "Creating..." : "Create Agent"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
