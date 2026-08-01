import { describe, expect, it } from "vitest";
import { clampRatio, filterAgentList, formatBudgetStatus, formatFreshness } from "./dashboard-view";

const agents = [
  { id: "alpha-1", role: "analyst", realm: "research", budget: 120, alive: true },
  { id: "trade-1", role: "trader", realm: "execution", budget: 300, alive: true },
  { id: "alpha-2", role: "researcher", realm: "research", budget: 200, alive: false },
];

describe("dashboard view helpers", () => {
  it("filters, sorts, and limits agents", () => {
    expect(filterAgentList(agents, { query: "alpha", realm: "research", limit: 1 }))
      .toEqual([agents[2]]);
  });

  it("clamps health ratios to a renderable range", () => {
    expect(clampRatio(-3.3)).toBe(0);
    expect(clampRatio(0.74)).toBe(0.74);
    expect(clampRatio(1.8)).toBe(1);
  });

  it("explains overspending instead of showing a negative percentage", () => {
    expect(formatBudgetStatus(-27_619, 4_577.2)).toBe("27,619 over budget");
  });

  it("formats data freshness", () => {
    expect(formatFreshness(1_000, 4_000)).toBe("updated now");
    expect(formatFreshness(1_000, 31_000)).toBe("updated 30s ago");
  });
});
