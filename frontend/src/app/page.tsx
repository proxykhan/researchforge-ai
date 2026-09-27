"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { ResearchSummary } from "@/lib/types";

export default function DashboardPage() {
  const [jobs, setJobs] = useState<ResearchSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listResearch()
      .then(setJobs)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load"),
      )
      .finally(() => setLoading(false));
  }, []);

  const active = jobs.filter(
    (j) => j.status !== "completed" && j.status !== "failed",
  );
  const completed = jobs.filter((j) => j.status === "completed");

  return (
    <>
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Overview of your research activity
        </p>
      </header>

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Total" value={jobs.length} />
        <StatCard label="Active" value={active.length} />
        <StatCard label="Completed" value={completed.length} />
      </div>

      <div className="mb-8">
        <Link
          href="/research/new"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
        >
          + New Research
        </Link>
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Recent Research
        </h2>

        {loading && <p className="text-sm text-zinc-400">Loading...</p>}
        {error && <p className="text-sm text-red-500">{error}</p>}
        {!loading && !error && jobs.length === 0 && (
          <p className="text-sm text-zinc-400">
            No research yet.{" "}
            <Link
              href="/research/new"
              className="text-blue-600 hover:underline"
            >
              Start one
            </Link>
            .
          </p>
        )}

        <div className="space-y-2">
          {jobs.slice(0, 10).map((job) => (
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
                  {new Date(job.created_at).toLocaleDateString()}
                </p>
              </div>
              <StatusBadge status={job.status} />
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-zinc-900 dark:text-zinc-100">
        {value}
      </p>
    </div>
  );
}
