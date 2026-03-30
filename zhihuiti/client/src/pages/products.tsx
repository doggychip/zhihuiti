import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { statusBadgeClass } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Package, Plus, Link2, ExternalLink } from "lucide-react";
import { useState } from "react";

export default function ProductsPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", webhookUrl: "" });
  const [formError, setFormError] = useState("");

  const { data: products, isLoading } = useQuery<any[]>({
    queryKey: ["/api/products"],
  });

  const { data: agents } = useQuery<any[]>({
    queryKey: ["/api/agents"],
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/products", {
        name: form.name,
        description: form.description,
        webhookUrl: form.webhookUrl || undefined,
      });
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/products"] });
      setCreateOpen(false);
      setForm({ name: "", description: "", webhookUrl: "" });
      setFormError("");
    },
    onError: (err: any) => setFormError(err.message ?? "Failed to register product"),
  });

  // Count bound agents per product
  function boundAgentCount(productId: string): number {
    if (!agents) return 0;
    // agents don't directly have binding info, but if product detail had it we'd use it
    return 0;
  }

  // Sort: AlphaArena first, then the rest
  const sortedProducts = [...(products ?? [])].sort((a: any, b: any) => {
    if (a.name.toLowerCase().includes("alphaarena") || a.name.toLowerCase().includes("alpha arena")) return -1;
    if (b.name.toLowerCase().includes("alphaarena") || b.name.toLowerCase().includes("alpha arena")) return 1;
    return 0;
  });

  return (
    <div className="p-6 lg:p-10 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Products</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Connected products and integrations</p>
        </div>
        <Button
          onClick={() => setCreateOpen(true)}
          className="bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Register Product
        </Button>
      </div>

      {/* Products List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : !sortedProducts || sortedProducts.length === 0 ? (
        <div className="rounded-lg border border-card-border bg-card/50 p-12 text-center">
          <Package className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <h3 className="font-semibold mb-1">No products registered</h3>
          <p className="text-sm text-muted-foreground mb-4">Register a product to connect agents to external platforms.</p>
          <Button
            onClick={() => setCreateOpen(true)}
            className="bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-semibold"
          >
            <Plus className="w-4 h-4 mr-1.5" />
            Register Product
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {sortedProducts.map((product: any) => {
            const isAlphaArena = product.name.toLowerCase().includes("alphaarena") || product.name.toLowerCase().includes("alpha arena");
            return (
              <Card key={product.id} className={`bg-card/50 border-card-border ${isAlphaArena ? "ring-1 ring-cyan-500/20" : ""}`}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold">{product.name}</h3>
                        {isAlphaArena && (
                          <Badge variant="outline" className="text-[10px] bg-cyan-500/15 text-cyan-400 border-cyan-500/20">
                            Featured
                          </Badge>
                        )}
                        <Badge variant="outline" className={`text-[10px] ${statusBadgeClass(product.status)}`}>
                          {product.status}
                        </Badge>
                      </div>
                      {product.description && (
                        <p className="text-sm text-muted-foreground mb-2">{product.description}</p>
                      )}
                      {product.webhookUrl && (
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <ExternalLink className="w-3 h-3" />
                          <a
                            href={product.webhookUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-cyan-400 transition-colors truncate max-w-80"
                          >
                            {product.webhookUrl}
                          </a>
                        </div>
                      )}
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Link2 className="w-3 h-3" />
                        <span>{boundAgentCount(product.id)} agents bound</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Register Product Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="bg-card border-card-border max-w-md">
          <DialogHeader>
            <DialogTitle>Register Product</DialogTitle>
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
                placeholder="AlphaArena"
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Product description..."
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Webhook URL</label>
              <input
                type="url"
                value={form.webhookUrl}
                onChange={e => setForm(f => ({ ...f, webhookUrl: e.target.value }))}
                placeholder="https://example.com/webhook"
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
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
                {createMutation.isPending ? "Registering..." : "Register"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
