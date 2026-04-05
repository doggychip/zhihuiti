import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Bot, Coins, FlaskConical, Zap, Landmark, Dna, Shield, ShieldAlert,
  Activity, ArrowRight, TrendingUp, Eye,
} from "lucide-react";
import { formatCurrency, formatRelativeTime, statusDotClass } from "@/lib/format";

function num(v: any, d = 0): string {
  if (v == null || isNaN(v)) return "0";
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: d });
}

function StatRow({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`font-mono text-xs font-medium ${color ?? "text-foreground"}`}>{value}</span>
    </div>
  );
}

function SectionCard({ title, icon: Icon, iconColor, children }: {
  title: string; icon: any; iconColor: string; children: React.ReactNode;
}) {
  return (
    <Card className="bg-card/50 border-card-border">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Icon className={`w-4 h-4 ${iconColor}`} />
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <div className="space-y-0.5">{children}</div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  // Core system data from Python dashboard
  const { data: zh, isLoading } = useQuery<any>({
    queryKey: ["/api/zhihuiti"],
    refetchInterval: 10000,
  });

  // Price data
  const { data: pricesData } = useQuery<any>({
    queryKey: ["/api/data/prices"],
    refetchInterval: 10000,
  });

  const prices: any[] = pricesData?.prices ?? [];
  const isLive: boolean = pricesData?.isLive ?? false;

  const econ = zh?.economy ?? {};
  const realms = zh?.realms ?? {};
  const agents: any[] = zh?.agents ?? [];
  const bloodline = zh?.bloodline ?? {};
  const inspection = zh?.inspection ?? {};
  const cb = zh?.circuit_breaker ?? {};
  const behavior = zh?.behavior ?? {};
  const goalHistory: any[] = zh?.goal_history ?? [];

  const totalAgents = agents.length;
  const activeAgents = agents.filter((a: any) => a.alive !== false && a.life_state !== "bankrupt").length;

  const realmOrder = [
    { key: "research", label: "研发界 Research", icon: FlaskConical, color: "text-blue-400" },
    { key: "execution", label: "执行界 Execution", icon: Zap, color: "text-yellow-400" },
    { key: "central", label: "中枢界 Central", icon: Landmark, color: "text-purple-400" },
  ];

  return (
    <div className="grid-pattern min-h-screen">
      <div className="p-6 lg:p-10 max-w-7xl space-y-6">
        {/* Header */}
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            Auto-refresh: 10s
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold tracking-tight">
            <span className="text-cyan-400">智慧体</span> zhihuiti Dashboard
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Autonomous multi-agent orchestration system
          </p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-48 w-full" />
            ))}
          </div>
        ) : (
          <>
            {/* Row 1: Economy + 3 Realms */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <SectionCard title="Economy" icon={Coins} iconColor="text-amber-400">
                <StatRow label="Money Supply" value={num(econ.money_supply, 2)} />
                <StatRow label="Minted" value={`+${num(econ.total_minted, 2)}`} color="text-emerald-400" />
                <StatRow label="Burned" value={`-${num(econ.total_burned, 2)}`} color="text-red-400" />
                <StatRow label="Treasury" value={num(econ.treasury_balance, 2)} color="text-cyan-400" />
                <StatRow label="Taxes Collected" value={num(econ.total_taxes_collected, 2)} />
                <StatRow label="Rewards Paid" value={num(econ.total_rewards_paid, 2)} />
                <StatRow label="Tax Rate" value={econ.tax_rate ?? "15%"} />
                <StatRow label="Transactions" value={num(econ.transactions)} />
              </SectionCard>

              {realmOrder.map(({ key, label, icon, color }) => {
                const r = realms[key] ?? {};
                return (
                  <SectionCard key={key} title={label} icon={icon} iconColor={color}>
                    <StatRow label="Active" value={num(r.agents_active)} color="text-emerald-400" />
                    <StatRow label="Frozen" value={num(r.agents_frozen)} color="text-amber-400" />
                    <StatRow label="Bankrupt" value={num(r.agents_bankrupt)} color="text-red-400" />
                    <StatRow label="Tasks Done" value={num(r.tasks_completed)} />
                    <StatRow label="Tasks Failed" value={num(r.tasks_failed)} color="text-red-400" />
                    <StatRow label="Avg Score" value={num(r.avg_score, 3)} />
                    <StatRow
                      label="Budget"
                      value={`${num(r.budget_remaining, 1)} / ${num(r.budget_allocated, 1)}`}
                      color={r.budget_remaining < 0 ? "text-red-400" : "text-foreground"}
                    />
                  </SectionCard>
                );
              })}
            </div>

            {/* Row 2: Agents, Bloodline, Inspection, Circuit Breaker */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <SectionCard title={`Agents (${totalAgents})`} icon={Bot} iconColor="text-cyan-400">
                <div className="max-h-52 overflow-y-auto -mx-1 px-1">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-muted-foreground">
                        <th className="text-left font-medium pb-1">ID</th>
                        <th className="text-left font-medium pb-1">Role</th>
                        <th className="text-left font-medium pb-1">State</th>
                        <th className="text-right font-medium pb-1">Budget</th>
                      </tr>
                    </thead>
                    <tbody>
                      {agents.slice(0, 12).map((a: any) => (
                        <tr key={a.id} className="border-t border-card-border/30">
                          <td className="py-0.5 font-mono text-muted-foreground">{a.id?.slice(0, 8)}</td>
                          <td className="py-0.5">{a.role}</td>
                          <td className="py-0.5">
                            <span className={a.life_state === "active" ? "text-emerald-400" : a.life_state === "bankrupt" ? "text-red-400" : "text-amber-400"}>
                              {a.life_state ?? "active"}
                            </span>
                          </td>
                          <td className="py-0.5 text-right font-mono">{num(a.budget, 1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {totalAgents > 12 && (
                    <p className="text-[10px] text-muted-foreground text-center mt-1">
                      +{totalAgents - 12} more agents
                    </p>
                  )}
                </div>
              </SectionCard>

              <SectionCard title="Bloodline" icon={Dna} iconColor="text-pink-400">
                <StatRow label="Total Genes" value={num(bloodline.total_genes)} />
                <StatRow label="Alive Genes" value={num(bloodline.alive_genes)} color="text-emerald-400" />
                <StatRow label="Max Generation" value={num(bloodline.max_generation)} />
                <StatRow label="Avg Score" value={num(bloodline.avg_score, 2)} />
              </SectionCard>

              <SectionCard title="3-Layer Inspection" icon={Eye} iconColor="text-amber-400">
                <StatRow label="Total Inspections" value={num(inspection.total_inspections)} />
                <StatRow label="Accepted" value={num(inspection.accepted)} color="text-emerald-400" />
                <StatRow label="Rejected" value={num(inspection.rejected)} color="text-red-400" />
                <StatRow
                  label="Acceptance Rate"
                  value={`${((inspection.acceptance_rate ?? 0) * 100).toFixed(1)}%`}
                />
                <StatRow label="Avg Score" value={num(inspection.avg_score, 3)} />
              </SectionCard>

              <SectionCard title="Circuit Breaker" icon={ShieldAlert} iconColor="text-red-400">
                <StatRow label="Total Trips" value={num(cb.total_trips)} />
                <StatRow label="Emergencies" value={num(cb.emergencies)} color="text-red-400" />
                <StatRow label="Halts" value={num(cb.halts)} color="text-amber-400" />
                <StatRow label="Warnings" value={num(cb.warnings)} />
                <StatRow label="Overridden" value={num(cb.overridden)} />
                <StatRow label="Active Laws" value={num(cb.laws_active)} />
              </SectionCard>
            </div>

            {/* Row 3: Price Ticker */}
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

            {/* Row 4: Recent Goal History */}
            {goalHistory.length > 0 && (
              <section>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyan-400" />
                    <h2 className="text-base font-semibold">Recent Goal History</h2>
                  </div>
                  <Link href="/goals">
                    <button className="text-sm text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium">
                      All Goals <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </Link>
                </div>
                <div className="rounded-lg border border-card-border bg-card/50 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-card-border text-muted-foreground text-xs">
                        <th className="text-left py-2.5 px-4 font-medium">Goal</th>
                        <th className="text-right py-2.5 px-4 font-medium">Tasks</th>
                        <th className="text-right py-2.5 px-4 font-medium hidden md:table-cell">Avg Score</th>
                        <th className="text-right py-2.5 px-4 font-medium hidden lg:table-cell">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {goalHistory.slice(0, 8).map((g: any, i: number) => (
                        <tr key={i} className="border-b border-card-border/50 hover:bg-accent/30 transition-colors">
                          <td className="py-2.5 px-4 max-w-xs truncate">{g.goal ?? g.description ?? "—"}</td>
                          <td className="py-2.5 px-4 text-right font-mono text-xs">{g.tasks ?? "—"}</td>
                          <td className="py-2.5 px-4 text-right font-mono text-xs hidden md:table-cell">
                            {g.avg_score != null ? Number(g.avg_score).toFixed(3) : "—"}
                          </td>
                          <td className="py-2.5 px-4 text-right text-xs text-muted-foreground hidden lg:table-cell">
                            {g.timestamp ? formatRelativeTime(g.timestamp) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
