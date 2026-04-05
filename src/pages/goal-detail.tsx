import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Trophy, Swords, Target, Sparkles } from "lucide-react";
import { formatRelativeTime } from "@/lib/format";

const statusBadge: Record<string, string> = {
  competing: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  won: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  lost: "text-red-400 border-red-500/30 bg-red-500/10",
  spawned: "text-pink-400 border-pink-500/30 bg-pink-500/10",
};

export default function GoalDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: goal, isLoading } = useQuery<any>({
    queryKey: [`/api/goals/${params.id}`],
    enabled: !!params.id,
  });

  if (isLoading) {
    return (
      <div className="p-6 lg:p-10 max-w-4xl space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!goal) {
    return (
      <div className="p-6 lg:p-10 max-w-4xl">
        <p className="text-muted-foreground">Goal not found.</p>
      </div>
    );
  }

  const competitions = goal.competitions ?? [];
  const winner = competitions.find((c: any) => c.status === "won" || c.status === "spawned");

  return (
    <div className="p-6 lg:p-10 max-w-4xl space-y-6">
      {/* Back */}
      <Link href="/goals">
        <button className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> All Goals
        </button>
      </Link>

      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-5 h-5 text-amber-400" />
          <h1 className="text-xl font-bold">{goal.title}</h1>
        </div>
        <div className="flex items-center gap-2 mb-3">
          <Badge variant="outline" className="text-xs">{goal.category}</Badge>
          <Badge variant="outline" className="text-xs">{goal.difficulty}</Badge>
          <span className="text-xs font-mono text-amber-400">{goal.reward}tk reward</span>
          <span className="text-xs text-muted-foreground capitalize">{goal.status}</span>
        </div>
        {goal.description && (
          <p className="text-sm text-muted-foreground">{goal.description}</p>
        )}
      </div>

      {/* Winner Card */}
      {winner && (
        <Card className="bg-emerald-500/5 border-emerald-500/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <Trophy className="w-4 h-4 text-emerald-400" />
              <span className="text-sm font-semibold text-emerald-400">Winner</span>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Link href={`/agents/${winner.agentId}`}>
                  <span className="font-medium hover:text-cyan-400 transition-colors cursor-pointer">
                    {winner.agentName}
                  </span>
                </Link>
                <span className="text-xs text-muted-foreground ml-2">({winner.agentType})</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="font-mono text-emerald-400">score: {winner.score?.toFixed(2)}</span>
                <span className="font-mono text-muted-foreground">bid: {winner.bid?.toFixed(1)}tk</span>
                {winner.status === "spawned" && (
                  <Badge variant="outline" className="text-[10px] text-pink-400 border-pink-500/30 bg-pink-500/10">
                    <Sparkles className="w-3 h-3 mr-1" /> Spawned Child
                  </Badge>
                )}
              </div>
            </div>
            {winner.result && (
              <p className="text-xs text-muted-foreground mt-2">{winner.result}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Competition Table */}
      {competitions.length > 0 ? (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Swords className="w-4 h-4 text-amber-400" />
            <h2 className="text-base font-semibold">Competition ({competitions.length} agents)</h2>
          </div>
          <div className="rounded-lg border border-card-border bg-card/50 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-card-border text-muted-foreground text-xs">
                  <th className="text-left py-2.5 px-4 font-medium">#</th>
                  <th className="text-left py-2.5 px-4 font-medium">Agent</th>
                  <th className="text-left py-2.5 px-4 font-medium">Type</th>
                  <th className="text-right py-2.5 px-4 font-medium">Score</th>
                  <th className="text-right py-2.5 px-4 font-medium">Bid</th>
                  <th className="text-right py-2.5 px-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {competitions.map((comp: any, i: number) => (
                  <tr key={comp.id} className="border-b border-card-border/50 hover:bg-accent/30 transition-colors">
                    <td className="py-2.5 px-4 text-xs text-muted-foreground">{i + 1}</td>
                    <td className="py-2.5 px-4">
                      <Link href={`/agents/${comp.agentId}`}>
                        <span className="font-medium hover:text-cyan-400 transition-colors cursor-pointer">
                          {comp.agentName}
                        </span>
                      </Link>
                    </td>
                    <td className="py-2.5 px-4 text-xs text-muted-foreground capitalize">{comp.agentType}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-xs">
                      <span className={comp.score >= 0.7 ? "text-emerald-400" : comp.score >= 0.4 ? "text-amber-400" : "text-red-400"}>
                        {comp.score?.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-xs text-muted-foreground">
                      {comp.bid?.toFixed(1)}tk
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <Badge variant="outline" className={`text-[10px] font-medium ${statusBadge[comp.status] ?? ""}`}>
                        {comp.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-card-border bg-card/50 p-8 text-center">
          <Swords className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No competition results yet. Waiting for goal runner cycle.</p>
        </div>
      )}
    </div>
  );
}
