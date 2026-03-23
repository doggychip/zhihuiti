import { log } from "../index";

export const ALPHA_ARENA_CONFIG = {
  name: "AlphaArena",
  description: "AI paper trading competition platform",
  defaultWebhookUrl: "https://alphaarena.app",
};

export async function sendTrade(
  apiKey: string,
  agentId: string,
  pair: string,
  side: "buy" | "sell",
  quantity: number,
  baseUrl = ALPHA_ARENA_CONFIG.defaultWebhookUrl,
): Promise<{ success: boolean; data?: any; error?: string }> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    const res = await fetch(`${baseUrl}/api/trades`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({ agentId, pair, side, quantity }),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      log(`AlphaArena trade sent: agent=${agentId} ${side} ${quantity} ${pair}`, "alpha-arena");
      return { success: true, data };
    }
    return { success: false, error: data.error ?? `HTTP ${res.status}` };
  } catch (err: any) {
    log(`AlphaArena trade error: ${err.message}`, "alpha-arena");
    return { success: false, error: err.message };
  }
}

export async function getLeaderboard(
  baseUrl = ALPHA_ARENA_CONFIG.defaultWebhookUrl,
): Promise<any[]> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    const res = await fetch(`${baseUrl}/api/leaderboard`, {
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : data.entries ?? [];
  } catch (err: any) {
    log(`AlphaArena leaderboard error: ${err.message}`, "alpha-arena");
    return [];
  }
}
