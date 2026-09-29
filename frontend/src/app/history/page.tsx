"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { ResearchStatus, ResearchSummary } from "@/lib/types";

const STATUS_FILTER_OPTIONS: Array<{
  label: string;
  value: ResearchStatus | "all";
}> = [
  { label: "All", value: "all" },
  { label: "Active", value: "researching" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
];

export default function HistoryPage() {
  const [jobs, setJobs] = useState<ResearchSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<ResearchStatus | "all">(
    "all",
  );

  useEffect(() => {
    api
      .listResearch()
      .then(setJobs)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load"),
      )
      .finally(() => setLoading(false));
  }, []);

  const filtered = jobs.filter((job) => {
    if (search && !job.question.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (statusFilter === "all") return true;
    if (statusFilter === "researching") {
      return job.status !== "completed" && job.status !== "failed";
    }
    return job.status === statusFilter;
  });

  return (
    <>
      <header className="mb-8">
        <p className="mb-2 text-sm font-semibold text-accent">History</p>
        <h1 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Research History
        </h1>
        <p className="mt-2 text-lg text-muted">
          Browse all past and current research
        </p>
      </header>

      {/* Filters */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder="Search questions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-full border border-border bg-white px-5 py-2.5 text-sm text-foreground placeholder:text-muted/60 focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none"
        />
        <div className="flex gap-2">
          {STATUS_FILTER_OPTIONS.map(({ label, value }) => (
            <button
              key={value}
              type="button"
              onClick={() => setStatusFilter(value)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                statusFilter === value
                  ? "bg-accent text-white"
                  : "bg-accent-light text-muted hover:text-foreground"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="py-20 text-center text-muted">Loading...</div>
      )}
      {error && (
        <div className="rounded-2xl bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="rounded-2xl border-2 border-dashed border-border py-16 text-center text-muted">
          {jobs.length === 0
            ? "No research history yet."
            : "No results match your filters."}
        </div>
      )}

      <div className="space-y-3">
        {filtered.map((job) => (
          <Link
            key={job.id}
            href={`/research/${job.id}`}
            className="group flex items-center justify-between rounded-2xl border border-border bg-card px-5 py-4 transition-all hover:border-accent/30 hover:bg-card-hover hover:shadow-sm"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-foreground group-hover:text-accent">
                {job.question}
              </p>
              <p className="mt-1 text-sm text-muted">
                {new Date(job.created_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </p>
            </div>
            <StatusBadge status={job.status} />
          </Link>
        ))}
      </div>
    </>
  );
}
