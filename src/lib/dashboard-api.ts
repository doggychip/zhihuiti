const API_BASE_URL = "https://zhihuiti.zeabur.app";
const REQUEST_TIMEOUT_MS = 12_000;

export class DashboardApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "DashboardApiError";
    this.status = status;
  }
}

function errorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    const message = record.message ?? record.error ?? record.detail;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}

export async function requestDashboardJson<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
    });

    let payload: unknown = null;
    if (response.status !== 204) {
      try {
        payload = await response.json();
      } catch {
        if (response.ok) throw new DashboardApiError("The API returned an unreadable response.");
      }
    }

    if (!response.ok) {
      throw new DashboardApiError(
        errorMessage(payload, `Request failed with status ${response.status}.`),
        response.status,
      );
    }

    return payload as T;
  } catch (error) {
    if (error instanceof DashboardApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new DashboardApiError("The API request timed out.");
    }
    throw new DashboardApiError(error instanceof Error ? error.message : "The API request failed.");
  } finally {
    window.clearTimeout(timeout);
  }
}

export function fetchDashboardData<T>(): Promise<T> {
  return requestDashboardJson<T>("/api/data");
}

export function fetchDashboardJobs<T>(): Promise<T> {
  return requestDashboardJson<T>("/api/jobs");
}

export function fetchDashboardJob<T>(jobId: string): Promise<T> {
  return requestDashboardJson<T>(`/api/job/${encodeURIComponent(jobId)}`);
}

export async function runDashboardGoal(goal: string): Promise<{ jobId: string | null; payload: unknown }> {
  const payload = await requestDashboardJson<unknown>("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });

  const record = payload && typeof payload === "object" ? payload as Record<string, unknown> : null;
  const rawJobId = record?.job_id ?? record?.jobId ?? record?.id;
  return {
    jobId: typeof rawJobId === "string" ? rawJobId : null,
    payload,
  };
}
