import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

vi.stubGlobal("localStorage", {
  getItem: vi.fn(() => "test-key"),
  setItem: vi.fn(),
  removeItem: vi.fn(),
});

beforeEach(() => {
  mockFetch.mockReset();
  vi.resetModules();
});

describe("api client", () => {
  it("sends Authorization header from localStorage", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: "ok", version: "1.0.0" }),
    });

    const { api } = await import("@/lib/api");
    await api.health();

    expect(mockFetch).toHaveBeenCalledOnce();
    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers["Authorization"]).toBe("Bearer test-key");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Invalid API key" }),
    });

    const { api } = await import("@/lib/api");
    await expect(api.health()).rejects.toThrow("Invalid API key");
  });

  it("createResearch sends POST with question", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          id: "abc",
          question: "test?",
          status: "queued",
          created_at: "2024-01-01",
        }),
    });

    const { api } = await import("@/lib/api");
    const result = await api.createResearch("test?");

    expect(result.id).toBe("abc");
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/research");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ question: "test?" });
  });

  it("cancelResearch sends POST to cancel endpoint", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: "abc", status: "failed" }),
    });

    const { api } = await import("@/lib/api");
    await api.cancelResearch("abc");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/research/abc/cancel");
    expect(init.method).toBe("POST");
  });
});
