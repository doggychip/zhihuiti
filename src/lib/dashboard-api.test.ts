import { afterEach, describe, expect, it, vi } from "vitest";
import { DashboardApiError, requestDashboardJson, runDashboardGoal } from "./dashboard-api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard API", () => {
  it("returns JSON for a successful response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ agents: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ));

    await expect(requestDashboardJson("/api/data")).resolves.toEqual({ agents: [] });
  });

  it("rejects an HTTP error using the API message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: "Goal is invalid" }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      }),
    ));

    await expect(requestDashboardJson("/api/run")).rejects.toMatchObject({
      name: "DashboardApiError",
      message: "Goal is invalid",
      status: 422,
    } satisfies Partial<DashboardApiError>);
  });

  it("extracts a returned job id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ job_id: "job-42" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ));

    await expect(runDashboardGoal("Review risk")).resolves.toMatchObject({ jobId: "job-42" });
  });
});
