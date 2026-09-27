import type {
  HealthResponse,
  ResearchDetail,
  ResearchSourcesResponse,
  ResearchSummary,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) ?? {}),
  };

  const apiKey = typeof window !== "undefined"
    ? localStorage.getItem("rf_api_key")
    : null;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  const res = await fetch(url, { ...init, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/api/v1/health"),

  createResearch: (question: string) =>
    request<ResearchSummary>("/api/v1/research", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  listResearch: () => request<ResearchSummary[]>("/api/v1/research"),

  getResearch: (id: string) =>
    request<ResearchDetail>(`/api/v1/research/${id}`),

  getResearchStatus: (id: string) =>
    request<{ id: string; status: string }>(`/api/v1/research/${id}/status`),

  getResearchSources: (id: string) =>
    request<ResearchSourcesResponse>(`/api/v1/research/${id}/sources`),

  getResearchReport: (id: string) =>
    request<ResearchDetail>(`/api/v1/research/${id}/report`),

  cancelResearch: (id: string) =>
    request<{ id: string; status: string }>(`/api/v1/research/${id}/cancel`, {
      method: "POST",
    }),
};
