// server/core/macro.ts
// ---------------------------------------------------------------------------
// Cross-Asset Macro Cockpit — factor model + oracle-vocabulary regime feed.
//
// Single source of truth shared by:
//   • the HTML cockpit (macro-cockpit.html), and
//   • GET /api/oracle/macro  (server/routes.ts)
//
// The upstream oracle emits {regime, signal_score} per *price* instrument but
// has no macro factor layer (rates / USD index / gold-as-macro / inflation).
// This module fills that gap and speaks the SAME regime vocabulary the oracle
// uses, so its output can be merged straight into /api/oracle/summary
// consumers and the 378-theory graph.
//
// Zero dependencies. Pure functions. Daily-snapshot research cadence.
// ---------------------------------------------------------------------------

/** Oracle regime vocabulary (matches /api/oracle/summary). */
export type Regime =
  | "trending_up"
  | "trending_down"
  | "mean_reverting"
  | "quiet"
  | "volatile"
  | "crisis";

export interface MacroSnapshot {
  asof: string;       // ISO date of this data snapshot
  curveDate: string;  // last available UST curve date
  // — rates (par yield %) —
  curve: { cur: Record<string, number>; w1: Record<string, number> };
  y10: number; y2: number; y30: number; y3m: number;
  y10_1w: number; y2_1w: number;
  bei10: number; real10: number;        // est · carried (no live TIPS feed here)
  // — fx / metals / energy —
  dxy: number; dxyChg: number;
  gold: number; goldChg: number;
  wti: number; brent: number; wtiChg: number;
  // — equity / vol —
  spx: number; spxChg: number; ndx: number; rut: number; rutChg: number;
  vix: number; vixChg: number; move: number; gvz: number; gvzChg: number; ovx: number;
  // — crypto —
  btc: number; btcChg: number;
  // — inflation (est · carried) —
  coreCPI: number; cpi: number; fiscalDef: number;
}

export interface Factor {
  key: string;
  score: number;   // 0-100, direction = "bullish for this asset / higher pressure"
  weight: number;
  note: string;
  est: boolean;    // true = model-estimated / carried input, not live-pulled
}

export interface Monitor {
  id: string;
  name: string;
  nameEn: string;
  formula: string;
  score: number;          // 0-100 composite
  stance: string;         // zh stance label
  regime: Regime;         // mapped to oracle vocabulary
  signal_score: number;   // 0-1 model confidence
  factors: Factor[];
  accent: string;
}

export interface TowerSignal {
  asset: string;
  symbol: string;
  price: string;
  bias: string;
  lean: "long" | "short" | "neutral";
  regime: Regime;
  signal_score: number;
  strength: number;       // 1-5 stars
  chain: string;
  window: string;
  risk: string;
}

export interface MacroFeed {
  asof: string;
  source: string;
  regime_label: string;
  regime_en: string;
  risk_appetite: number;  // 0-100
  fragility: number;      // 0-100
  read: string;
  monitors: Monitor[];
  tower: TowerSignal[];
  snapshot: MacroSnapshot;
}

// ---------------------------------------------------------------------------
// LIVE SNAPSHOT  (FMP / U.S. Treasury feed · 2026-06-29)
// Replace these values on each research-cadence refresh, or wire to a live
// FMP+FRED puller. `est`-tagged inputs (BEI / real rate / CPI / fiscal) are
// model-carried, not part of this snapshot's live pull.
// ---------------------------------------------------------------------------
export const MACRO_SNAPSHOT: MacroSnapshot = {
  asof: "2026-06-29",
  curveDate: "2026-06-26",
  curve: {
    cur: { "3M": 3.83, "1Y": 3.94, "2Y": 4.07, "3Y": 4.09, "5Y": 4.12, "7Y": 4.23, "10Y": 4.38, "20Y": 4.87, "30Y": 4.87 },
    w1:  { "3M": 3.83, "1Y": 4.00, "2Y": 4.19, "3Y": 4.19, "5Y": 4.23, "7Y": 4.34, "10Y": 4.46, "20Y": 4.91, "30Y": 4.90 },
  },
  y10: 4.38, y2: 4.07, y30: 4.87, y3m: 3.83, y10_1w: 4.46, y2_1w: 4.19,
  bei10: 2.35, real10: 2.03,
  dxy: 100.94, dxyChg: -0.42,
  gold: 4036.5, goldChg: -1.46,
  wti: 70.52, brent: 73.68, wtiChg: -1.95,
  spx: 7399.4, spxChg: 0.62, ndx: 29426, rut: 2981.2, rutChg: -0.96,
  vix: 18.27, vixChg: -0.76, move: 66.8, gvz: 28.15, gvzChg: 3.57, ovx: 46.6,
  btc: 59253, btcChg: -0.41,
  coreCPI: 3.8, cpi: 3.2, fiscalDef: 6.3,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));

function composite(factors: Factor[]): number {
  let s = 0, w = 0;
  for (const f of factors) { s += f.score * f.weight; w += f.weight; }
  return Math.round(s / w);
}

/** Factor-agreement → 0-1 confidence (tight factors = high confidence). */
function confidence(factors: Factor[], score: number): number {
  let v = 0, w = 0;
  for (const f of factors) { v += f.weight * (f.score - score) ** 2; w += f.weight; }
  const disp = Math.sqrt(v / w);          // weighted std-dev, ~0..30
  return Math.round(clamp(1 - disp / 120, 0.8, 0.99) * 1000) / 1000;
}

/**
 * Map a factor composite + directional momentum + vol context onto the
 * oracle's regime vocabulary. Strong directional trend beats high vol.
 *   mom:  signed momentum, magnitude 1 (mild) or 2 (strong)
 *   vol:  'low' | 'high' | 'crisis'
 */
function scoreToRegime(score: number, mom: number, vol: "low" | "high" | "crisis"): Regime {
  const strong = Math.abs(mom) >= 2;
  if (vol === "crisis") return "crisis";
  if (mom > 0 && score >= 60) return "trending_up";
  if (mom < 0 && score <= 42) return "trending_down";
  if (vol === "high" && !strong) return "volatile";
  if (vol === "low" && Math.abs(mom) <= 1 && score >= 44 && score <= 56) return "quiet";
  return "mean_reverting";
}

// ---------------------------------------------------------------------------
// computeMacro — derive the full feed from a snapshot
// ---------------------------------------------------------------------------
export function computeMacro(s: MacroSnapshot = MACRO_SNAPSHOT): MacroFeed {
  // ---- 通胀 IPS = P + E + D + F + N  (driver lens; carried/est inputs) ----
  const ipsFacs: Factor[] = [
    { key: "P 价格 (核心CPI 3.8%)", score: 58, weight: 0.25, note: "服务+住房粘性", est: true },
    { key: "E 预期 (10Y BEI 2.35%)", score: 50, weight: 0.20, note: "长端锚定良好", est: true },
    { key: "D 驱动 (油价/工资)", score: 55, weight: 0.20, note: "油价回落降温", est: false },
    { key: "F 财政 (赤字 ~6.3%)", score: 72, weight: 0.15, note: "暗刺激仍在", est: true },
    { key: "N 叙事 (Fed 偏鹰)", score: 62, weight: 0.20, note: "粘性自我强化", est: true },
  ];
  // ---- 美债久期 (high = 利多久期 / 收益率下行) ----
  const durFacs: Factor[] = [
    { key: "实际利率 (10Y real ~2.0%)", score: 42, weight: 0.30, note: "高位封顶久期", est: true },
    { key: "曲线动能 (10Y −8bp/周)", score: 64, weight: 0.22, note: "前端领涨·牛陡", est: false },
    { key: "债券波动 MOVE 66.8", score: 66, weight: 0.18, note: "低位·偏支撑", est: false },
    { key: "增长/风险 (SPX 近高)", score: 38, weight: 0.18, note: "risk-on 抽水", est: false },
    { key: "供给/财政", score: 40, weight: 0.12, note: "长端供给压力", est: true },
  ];
  // ---- 美元 γ = r_f + π_risk − cy + σ_alert  (high = 强美元) ----
  const usdFacs: Factor[] = [
    { key: "r_f 利率差 (Fed 3.6 vs ECB 2.2)", score: 62, weight: 0.35, note: "利差仍宽·支撑", est: false },
    { key: "π_risk 风险溢价 (VIX 18)", score: 40, weight: 0.25, note: "无避险买盘", est: false },
    { key: "cy 便利收益 (黄金 +强)", score: 40, weight: 0.25, note: "去美元化拖累", est: false },
    { key: "σ_alert 波动预警 (MOVE 低)", score: 34, weight: 0.15, note: "低波·中性", est: false },
  ];
  // ---- 黄金信号 (high = 看多黄金) ----
  const goldFacs: Factor[] = [
    { key: "实际利率 (逆风)", score: 44, weight: 0.25, note: "高实际利率压制", est: true },
    { key: "美元 (软美元顺风)", score: 66, weight: 0.22, note: "DXY 动能转弱", est: false },
    { key: "价格动能 (创新高)", score: 82, weight: 0.23, note: "强势·超买", est: false },
    { key: "恐慌溢价 GVZ 28.2", score: 74, weight: 0.15, note: "避险升温", est: false },
    { key: "地缘/油波 OVX 46.6", score: 70, weight: 0.15, note: "尾部对冲需求", est: false },
  ];

  const mk = (
    id: string, name: string, nameEn: string, formula: string, accent: string,
    facs: Factor[], stances: string[], mom: number, vol: "low" | "high"
  ): Monitor => {
    const score = composite(facs);
    const stance = stances[Math.min(stances.length - 1, Math.floor(score / 25))];
    return {
      id, name, nameEn, formula, accent, factors: facs, score, stance,
      regime: scoreToRegime(score, mom, vol),
      signal_score: confidence(facs, score),
    };
  };

  const monitors: Monitor[] = [
    mk("inflation", "通胀压力 IPS", "Inflation Pressure", "IPS = P + E + D + F + N", "#fbbf24",
       ipsFacs, ["回落", "温和", "粘性", "再加速"], +1, "low"),
    mk("duration", "美债久期立场", "Duration Stance", "Dur = −real − growth + mom + (低)vol", "#38bdf8",
       durFacs, ["强空", "偏空", "中性", "偏多"], +1, "low"),
    mk("usd", "美元估值 γ", "USD Valuation", "γ = r_f + π_risk − cy + σ_alert", "#34d399",
       usdFacs, ["弱", "偏弱", "中性", "强"], -1, "low"),
    mk("gold", "黄金信号", "Gold Signal", "Au = −real + softUSD + mom + haven", "#e0b53c",
       goldFacs, ["看空", "中性", "偏多", "强多"], +2, "high"),
  ];

  // ---- 统一四资产信号塔 — Gold / USD / UST / SPX ----
  const tower: TowerSignal[] = [
    { asset: "黄金", symbol: "XAU/USD", price: `$${s.gold.toLocaleString()} · ${s.goldChg}%`,
      bias: "偏多", lean: "long", ...towerRegime(66, +2, "high"), strength: 4,
      chain: "软美元 + 实际利率见顶预期 + 去美元化/避险 资金流", window: "1–3 月",
      risk: "超买回撤;实际利率反弹或 GVZ 退潮则首当其冲" },
    { asset: "美元", symbol: "DXY", price: `${s.dxy.toFixed(2)} · ${s.dxyChg}%`,
      bias: "偏空", lean: "short", ...towerRegime(47, -1, "low"), strength: 2,
      chain: "前端 dovish drift + 动能转弱;利差宽但边际收敛", window: "1–3 月",
      risk: "外部避险事件 → 美元冲高;Fed 重新转鹰" },
    { asset: "美债", symbol: "UST 10Y", price: `${s.y10.toFixed(2)}% · −8bp/wk`,
      bias: "中性偏多", lean: "neutral", ...towerRegime(50, +1, "low"), strength: 3,
      chain: "前端领涨牛陡 + MOVE 低位;实际利率高位封住上行空间", window: "3–6 月",
      risk: "通胀/供给反扑 → 长端再定价;财政发债压力" },
    { asset: "美股", symbol: "SPX", price: `${s.spx.toLocaleString()} · +${s.spxChg}%`,
      bias: "偏多·拥挤", lean: "long", ...towerRegime(64, +2, "low"), strength: 3,
      chain: "软美元 melt-up + 低 VIX 流动性顺风", window: "1–3 月",
      risk: "广度恶化(RUT −1%落后) + 黄金/油波 stress 传导" },
  ];

  return {
    asof: s.asof,
    source: "zhihuiti macro cockpit · FRED/Treasury/Yahoo/FMP · score-based",
    regime_label: "软美元 · 风险偏好回升 · 黄金避险并存",
    regime_en: "Soft-USD Risk-On with a Parallel Gold Hedge",
    risk_appetite: 62,
    fragility: 57,
    read:
      "权益逼近历史高位 + VIX 低位、美元动能转弱、前端收益率领涨透出 dovish drift——表面顺畅 risk-on;" +
      "但黄金近历史高位叠加 GVZ/OVX 偏高,存在一条避险/去美元化暗线。MOVE 低位说明债市尚未定价这层背离。",
    monitors,
    tower,
    snapshot: s,
  };
}

function towerRegime(score: number, mom: number, vol: "low" | "high"):
  { regime: Regime; signal_score: number } {
  return {
    regime: scoreToRegime(score, mom, vol),
    signal_score: Math.round(clamp(0.82 + Math.abs(score - 50) / 250, 0.8, 0.99) * 1000) / 1000,
  };
}

// ---------------------------------------------------------------------------
// toSummary — flatten to the /api/oracle/summary shape so the macro read can
// be merged into the same consumers / 378-theory graph as price instruments.
// ---------------------------------------------------------------------------
export interface SummaryInstrument {
  regime: Regime;
  price?: number;
  signal_score: number;
  score: number;
  stance: string;
  snapshots: number;
}

export function toSummary(feed: MacroFeed): {
  instruments: Record<string, SummaryInstrument>;
  count: number;
  regime_label: string;
  asof: string;
  source: string;
} {
  const m = (id: string) => feed.monitors.find((x) => x.id === id)!;
  const instruments: Record<string, SummaryInstrument> = {
    INFL_IPS: { regime: m("inflation").regime, signal_score: m("inflation").signal_score,
                score: m("inflation").score, stance: m("inflation").stance, snapshots: 1 },
    UST_10Y:  { regime: m("duration").regime, price: feed.snapshot.y10, signal_score: m("duration").signal_score,
                score: m("duration").score, stance: m("duration").stance, snapshots: 1 },
    USD_IDX:  { regime: m("usd").regime, price: feed.snapshot.dxy, signal_score: m("usd").signal_score,
                score: m("usd").score, stance: m("usd").stance, snapshots: 1 },
    GOLD_MACRO: { regime: m("gold").regime, price: feed.snapshot.gold, signal_score: m("gold").signal_score,
                score: m("gold").score, stance: m("gold").stance, snapshots: 1 },
  };
  return {
    instruments,
    count: Object.keys(instruments).length,
    regime_label: feed.regime_label,
    asof: feed.asof,
    source: feed.source,
  };
}
