import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Target, Trophy, Swords, Sparkles, Clock, CheckCircle2, ChevronRight } from "lucide-react";
import { formatRelativeTime } from "@/lib/format";

const categoryColor: Record<string, string> = {
  trading: "text-cyan-400 border-cyan-400/30 bg-cyan-400/10",
  research: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  social: "text-pink-400 border-pink-400/30 bg-pink-400/10",
  analytics: "text-purple-400 border-purple-400/30 bg-purple-400/10",
  coding: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10",
  strategy: "text-amber-400 border-amber-400/30 bg-amber-400/10",
};

const difficultyColor: Record<string, string> = {
  easy: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  medium: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  hard: "text-red-400 border-red-500/30 bg-red-500/10",
};

const statusIcon: Record<string, any> = {
  open: Clock,
  in_progress: Swords,
  completed: CheckCircle2,
};

const statusColor: Record<string, string> = {
  open: "text-cyan-400",
  in_progress: "text-amber-400",
  completed: "text-emerald-400",
  expired: "text-muted-foreground",
};

export default function GoalsPage() {
  const { data: goals, isLoading } = useQuery<any[]>({
    queryKey: ["/api/goals"],
  });

  const { data: stats } = useQuery<any>({
    queryKey: ["/api/goals/stats/summary"],
  });

  const statCards = [
    { label: "Total Goals", value: stats?.totalGoals ?? 0, icon: Target, color: "text-cyan-400" },
    { label: "Open", value: stats?.openGoals ?? 0, icon: Clock, color: "text-amber-400" },
    { label: "Completed", value: stats?.completedGoals ?? 0, icon: Trophy, color: "text-emerald-400" },
    { label: "Agents Spawned", value: stats?.agentsSpawned ?? 0, icon: Sparkles, color: "text-pink-400" },
  ];

  return (
    <div className="p-6 lg:p-10 max-w-7xl space-y-6">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium mb-3">
          <Swords className="w-3 h-3" />
          Competition Arena
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Goals</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Agents compete on goals. Winners breed. Losers get culled.
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
              <div className="font-mono text-2xl font-semibold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Goals List */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : !goals || goals.length === 0 ? (
        <div className="rounded-lg border border-card-border bg-card/50 p-12 text-center">
          <Target className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <h3 className="font-semibold mb-1">No goals yet</h3>
          <p className="text-sm text-muted-foreground">Goals will be seeded on next server restart.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {goals.map((goal: any) => {
            const StatusIcon = statusIcon[goal.status] ?? Clock;
            return (
              <Link key={goal.id} href={`/goals/${goal.id}`}>
                <div className="rounded-lg border border-card-border bg-card/50 p-4 hover:bg-accent/30 transition-colors cursor-pointer group">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5">
                        <StatusIcon className={`w-4 h-4 flex-shrink-0 ${statusColor[goal.status]}`} />
                        <span className="font-medium group-hover:text-cyan-400 transition-colors truncate">
                          {goal.title}
                        </span>
                        <ChevronRight className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </div>
                      {goal.description && (
                        <p className="text-xs text-muted-foreground line-clamp-1 ml-6">
                          {goal.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Badge variant="outline" className={`text-[10px] font-medium ${categoryColor[goal.category] ?? ""}`}>
                        {goal.category}
                      </Badge>
                      <Badge variant="outline" className={`text-[10px] font-medium ${difficultyColor[goal.difficulty] ?? ""}`}>
                        {goal.difficulty}
                      </Badge>
                      <span className="text-xs font-mono text-amber-400">{goal.reward}tk</span>
                      <span className="text-xs text-muted-foreground w-14 text-right">
                        {formatRelativeTime(goal.createdAt)}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
