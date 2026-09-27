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
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          Research History
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Browse all past and current research
        </p>
      </header>

      {/* Filters */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder="Search questions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        />
        <div className="flex gap-1">
          {STATUS_FILTER_OPTIONS.map(({ label, value }) => (
            <button
              key={value}
              type="button"
              onClick={() => setStatusFilter(value)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                statusFilter === value
                  ? "bg-blue-600 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="text-sm text-zinc-400">Loading...</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {!loading && !error && filtered.length === 0 && (
        <p className="text-sm text-zinc-400">
          {jobs.length === 0
            ? "No research history yet."
            : "No results match your filters."}
        </p>
      )}

      <div className="space-y-2">
        {filtered.map((job) => (
          <Link
            key={job.id}
            href={`/research/${job.id}`}
            className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-4 py-3 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-blue-800 dark:hover:bg-blue-950/30"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {job.question}
              </p>
              <p className="mt-0.5 text-xs text-zinc-400">
                {new Date(job.created_at).toLocaleString()}
              </p>
            </div>
            <StatusBadge status={job.status} />
          </Link>
        ))}
      </div>
    </>
  );
}
