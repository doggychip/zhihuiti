import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Settings, Key, Database, Info, Copy, RefreshCw, Eye, EyeOff } from "lucide-react";

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

function generateApiKey(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let key = "zh_";
  for (let i = 0; i < 40; i++) {
    key += chars[Math.floor(Math.random() * chars.length)];
  }
  return key;
}

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("zh_api_key") ?? generateApiKey());
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    copyToClipboard(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleRegenerate() {
    const newKey = generateApiKey();
    setApiKey(newKey);
    localStorage.setItem("zh_api_key", newKey);
  }

  const platformInfo = [
    { label: "Version", value: "1.0.0" },
    { label: "Environment", value: import.meta.env.MODE ?? "production" },
    { label: "API Base", value: window.location.origin },
    { label: "Uptime", value: "—" },
  ];

  const dataSourceSettings = [
    { label: "Price Feed", value: "Simulated (configurable)", status: "active" },
    { label: "AlphaArena Integration", value: "Webhook", status: "pending" },
    { label: "Database", value: "PostgreSQL", status: "active" },
  ];

  return (
    <div className="p-6 lg:p-10 max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Platform configuration and preferences</p>
      </div>

      {/* Platform Info */}
      <Card className="bg-card/50 border-card-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Info className="w-4 h-4 text-cyan-400" />
            Platform Information
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {platformInfo.map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between px-6 py-3">
                <span className="text-sm text-muted-foreground">{label}</span>
                <span className="text-sm font-mono font-medium">{value}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* API Key */}
      <Card className="bg-card/50 border-card-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Key className="w-4 h-4 text-amber-400" />
            API Key
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Use this key to authenticate API requests. Keep it secret.
          </p>
          <div className="flex items-center gap-2">
            <div className="flex-1 font-mono text-sm bg-background border border-input rounded-md px-3 py-2 text-foreground/80 overflow-hidden">
              {showKey ? apiKey : "zh_" + "•".repeat(40)}
            </div>
            <button
              onClick={() => setShowKey(v => !v)}
              className="p-2 rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              title={showKey ? "Hide key" : "Show key"}
            >
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
            <button
              onClick={handleCopy}
              className="p-2 rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              title="Copy to clipboard"
            >
              {copied
                ? <span className="text-xs text-emerald-400 px-0.5">✓</span>
                : <Copy className="w-4 h-4" />
              }
            </button>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={handleRegenerate}
            >
              <RefreshCw className="w-3 h-3 mr-1.5" />
              Regenerate Key
            </Button>
            <p className="text-xs text-muted-foreground">Stored locally in browser only</p>
          </div>
        </CardContent>
      </Card>

      {/* Data Sources */}
      <Card className="bg-card/50 border-card-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Database className="w-4 h-4 text-purple-400" />
            Data Sources
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {dataSourceSettings.map(({ label, value, status }) => (
              <div key={label} className="flex items-center justify-between px-6 py-3">
                <div>
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{value}</p>
                </div>
                <Badge
                  variant="outline"
                  className={`text-[10px] ${status === "active"
                    ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/20"
                    : "bg-amber-500/15 text-amber-400 border-amber-500/20"
                  }`}
                >
                  {status}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card className="bg-card/50 border-card-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Settings className="w-4 h-4 text-muted-foreground" />
            Preferences
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {[
              { label: "Agent auto-start on creation", value: "Disabled" },
              { label: "Log retention", value: "Last 1000 entries" },
              { label: "Price refresh interval", value: "10 seconds" },
              { label: "Default agent type", value: "Trading" },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between px-6 py-3">
                <span className="text-sm text-muted-foreground">{label}</span>
                <span className="text-sm font-medium text-foreground/80">{value}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
