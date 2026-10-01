"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { AuthGuard } from "@/components/auth-guard";
import { api } from "@/lib/api";
import type { ResearchSummary } from "@/lib/types";

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
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
      {/* Hero */}
      <header className="mb-12 text-center">
        <p className="mb-3 text-sm font-semibold tracking-wide text-accent">
          AI-Powered Research
        </p>
        <h1 className="font-display text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Your research dashboard
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted">
          Submit complex questions and let our multi-agent system research,
          verify, debate, and synthesize findings from academic databases.
        </p>
      </header>

      {/* Stats */}
      <div className="mb-10 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <StatCard label="Total Research" value={jobs.length} icon="&#9670;" />
        <StatCard label="In Progress" value={active.length} icon="&#9656;" />
        <StatCard label="Completed" value={completed.length} icon="&#10003;" />
      </div>

      {/* Recent Research */}
      <section>
        <div className="mb-5 flex items-center justify-between">
          <h2 className="font-display text-2xl font-bold text-foreground">
            Recent Research
          </h2>
          <Link
            href="/history"
            className="text-sm font-medium text-accent hover:text-accent-hover"
          >
            View all
          </Link>
        </div>

        {loading && (
          <div className="py-12 text-center text-muted">Loading...</div>
        )}
        {error && (
          <div className="rounded-2xl bg-error-bg px-5 py-4 text-sm text-error-fg">
            {error}
          </div>
        )}
        {!loading && !error && jobs.length === 0 && (
          <div className="rounded-2xl border-2 border-dashed border-border py-16 text-center">
            <p className="text-lg font-medium text-muted">No research yet</p>
            <p className="mt-2 text-sm text-muted">
              Start your first research to see results here.
            </p>
            <Link
              href="/research/new"
              className="mt-6 inline-flex rounded-full bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
            >
              Start Research
            </Link>
          </div>
        )}

        <div className="space-y-3">
          {jobs.slice(0, 10).map((job) => (
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
                  })}
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

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-accent-light px-6 py-5">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-lg text-accent">
          {icon}
        </span>
        <div>
          <p className="text-sm font-medium text-muted">{label}</p>
          <p className="text-2xl font-bold text-foreground">{value}</p>
        </div>
      </div>
    </div>
  );
}
