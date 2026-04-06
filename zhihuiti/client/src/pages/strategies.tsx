import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { strategyTypeBadgeClass } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Lightbulb, Plus, ChevronDown, ChevronUp, Settings2 } from "lucide-react";
import { useState } from "react";

const STRATEGY_TYPES = ["momentum", "mean_reversion", "indicator", "hybrid", "custom"] as const;

function strategyTypeLabel(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function countParams(parameters: string | null | undefined): number {
  if (!parameters) return 0;
  try {
    const obj = JSON.parse(parameters);
    return Object.keys(obj).length;
  } catch {
    return 0;
  }
}

export default function StrategiesPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    type: "momentum",
    parameters: "{}",
  });
  const [formError, setFormError] = useState("");

  const { data: strategies, isLoading } = useQuery<any[]>({
    queryKey: ["/api/strategies"],
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      // Validate JSON
      try { JSON.parse(form.parameters); } catch {
        throw new Error("Parameters must be valid JSON");
      }
      const res = await apiRequest("POST", "/api/strategies", {
        name: form.name,
        description: form.description,
        type: form.type,
        parameters: form.parameters,
      });
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/strategies"] });
      setCreateOpen(false);
      setForm({ name: "", description: "", type: "momentum", parameters: "{}" });
      setFormError("");
    },
    onError: (err: any) => setFormError(err.message ?? "Failed to create strategy"),
  });

  return (
    <div className="p-6 lg:p-10 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Strategies</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Strategy library for your agents</p>
        </div>
        <Button
          onClick={() => setCreateOpen(true)}
          className="bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Create Strategy
        </Button>
      </div>

      {/* Strategy Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : !strategies || strategies.length === 0 ? (
        <div className="rounded-lg border border-card-border bg-card/50 p-12 text-center">
          <Lightbulb className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <h3 className="font-semibold mb-1">No strategies yet</h3>
          <p className="text-sm text-muted-foreground mb-4">Create your first strategy to assign to agents.</p>
          <Button
            onClick={() => setCreateOpen(true)}
            className="bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
          >
            <Plus className="w-4 h-4 mr-1.5" />
            Create Strategy
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {strategies.map((s: any) => {
            const expanded = expandedId === s.id;
            const paramCount = countParams(s.parameters);
            return (
              <Card
                key={s.id}
                className="bg-card/50 border-card-border cursor-pointer hover:bg-accent/20 transition-colors"
                onClick={() => setExpandedId(expanded ? null : s.id)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-sm leading-tight">{s.name}</h3>
                    <Badge variant="outline" className={`text-[10px] font-medium ml-2 flex-shrink-0 ${strategyTypeBadgeClass(s.type)}`}>
                      {strategyTypeLabel(s.type)}
                    </Badge>
                  </div>
                  {s.description && (
                    <p className="text-xs text-muted-foreground mb-3 leading-relaxed">{s.description}</p>
                  )}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Settings2 className="w-3 h-3" />
                      <span>{paramCount} param{paramCount !== 1 ? "s" : ""}</span>
                    </div>
                    <button className="text-muted-foreground hover:text-foreground transition-colors">
                      {expanded
                        ? <ChevronUp className="w-3.5 h-3.5" />
                        : <ChevronDown className="w-3.5 h-3.5" />
                      }
                    </button>
                  </div>
                  {expanded && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <p className="text-xs font-medium text-muted-foreground mb-1.5">Parameters</p>
                      <pre className="text-xs bg-background rounded-md p-2 overflow-auto max-h-32 text-foreground/80 border border-border">
                        {(() => {
                          try {
                            return JSON.stringify(JSON.parse(s.parameters ?? "{}"), null, 2);
                          } catch {
                            return s.parameters ?? "{}";
                          }
                        })()}
                      </pre>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Strategy Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="bg-card border-card-border max-w-md">
          <DialogHeader>
            <DialogTitle>Create Strategy</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            {formError && (
              <div className="px-3 py-2 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                {formError}
              </div>
            )}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Trend Following"
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Brief description of the strategy..."
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
                {STRATEGY_TYPES.map(t => (
                  <option key={t} value={t}>{strategyTypeLabel(t)}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Parameters (JSON)</label>
              <textarea
                value={form.parameters}
                onChange={e => setForm(f => ({ ...f, parameters: e.target.value }))}
                placeholder='{"period": 14, "threshold": 0.05}'
                rows={4}
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
              />
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => { setCreateOpen(false); setFormError(""); }}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
                onClick={() => createMutation.mutate()}
                disabled={!form.name || createMutation.isPending}
              >
                {createMutation.isPending ? "Creating..." : "Create Strategy"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
