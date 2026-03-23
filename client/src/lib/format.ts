export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatReturn(value: number): string {
  const pct = (value * 100).toFixed(2);
  return value >= 0 ? `+${pct}%` : `${pct}%`;
}

export function pnlColor(value: number): string {
  if (value > 0) return "text-emerald-400";
  if (value < 0) return "text-red-400";
  return "text-muted-foreground";
}

export function agentTypeBadgeClass(type: string): string {
  switch (type) {
    case "trading":
      return "text-cyan-400 border-cyan-400/30 bg-cyan-400/10";
    case "analytics":
      return "text-purple-400 border-purple-400/30 bg-purple-400/10";
    case "social":
      return "text-pink-400 border-pink-400/30 bg-pink-400/10";
    default:
      return "text-muted-foreground border-muted bg-muted/10";
  }
}

export function agentTypeLabel(type: string): string {
  switch (type) {
    case "trading":
      return "Trading";
    case "analytics":
      return "Analytics";
    case "social":
      return "Social";
    default:
      return type;
  }
}

export function statusDotClass(status: string): string {
  switch (status) {
    case "active":
      return "bg-emerald-400";
    case "paused":
      return "bg-amber-400";
    case "stopped":
      return "bg-red-400";
    default:
      return "bg-gray-400";
  }
}

export function statusBadgeClass(status: string): string {
  switch (status) {
    case "active":
      return "bg-emerald-500/15 text-emerald-400 border-emerald-500/20";
    case "paused":
      return "bg-amber-500/15 text-amber-400 border-amber-500/20";
    case "stopped":
      return "bg-red-500/15 text-red-400 border-red-500/20";
    case "inactive":
      return "bg-gray-500/15 text-gray-400 border-gray-500/20";
    case "pending":
      return "bg-amber-500/15 text-amber-400 border-amber-500/20";
    default:
      return "bg-muted text-muted-foreground";
  }
}

export function strategyTypeBadgeClass(type: string): string {
  switch (type) {
    case "momentum":
      return "text-cyan-400 border-cyan-400/30 bg-cyan-400/10";
    case "mean_reversion":
      return "text-amber-400 border-amber-400/30 bg-amber-400/10";
    case "indicator":
      return "text-purple-400 border-purple-400/30 bg-purple-400/10";
    case "hybrid":
      return "text-pink-400 border-pink-400/30 bg-pink-400/10";
    case "custom":
      return "text-emerald-400 border-emerald-400/30 bg-emerald-400/10";
    default:
      return "text-muted-foreground border-muted bg-muted/10";
  }
}

export function formatRelativeTime(dateStr: string | Date): string {
  const date = typeof dateStr === "string" ? new Date(dateStr) : dateStr;
  const now = Date.now();
  const diff = now - date.getTime();

  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

export function formatDateTime(dateStr: string | Date): string {
  const date = typeof dateStr === "string" ? new Date(dateStr) : dateStr;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}
