"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Markdown } from "@/components/markdown";
import { StagePipeline } from "@/components/stage-pipeline";
import { StatusBadge } from "@/components/status-badge";
import { AuthGuard } from "@/components/auth-guard";
import { api } from "@/lib/api";
import type { ResearchDetail } from "@/lib/types";

export default function ResearchProgressPage() {
  return (
    <AuthGuard>
      <ResearchProgressContent />
    </AuthGuard>
  );
}

function ResearchProgressContent() {
  const { id } = useParams<{ id: string }>();
  const [research, setResearch] = useState<ResearchDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .getResearch(id)
      .then(setResearch)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load"),
      );
  }, [id]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [load]);

  useEffect(() => {
    if (
      research &&
      (research.status === "completed" || research.status === "failed")
    ) {
      // stop polling once done
    }
  }, [research]);

  if (error) {
    return (
      <div className="rounded-2xl bg-red-50 px-5 py-4 text-sm text-red-700">
        {error}
      </div>
    );
  }
  if (!research) {
    return <div className="py-20 text-center text-muted">Loading...</div>;
  }

  const isDone =
    research.status === "completed" || research.status === "failed";

  return (
    <>
      {/* Header */}
      <header className="mb-8">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="mb-2 text-sm font-semibold text-accent">Research</p>
            <h1 className="font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              {research.question}
            </h1>
            <p className="mt-2 text-sm text-muted">
              Started{" "}
              {new Date(research.created_at).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </p>
          </div>
          <StatusBadge status={research.status} />
        </div>
      </header>

      {/* Pipeline */}
      <section className="mb-8">
        <h2 className="mb-3 text-sm font-semibold text-foreground">
          Progress
        </h2>
        <div className="rounded-2xl border border-border bg-accent-light p-4">
          <StagePipeline current={research.status} />
        </div>
      </section>

      {/* Stats */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MiniStat label="Papers Found" value={research.paper_count} />
        <MiniStat
          label="Search Queries"
          value={research.search_queries.length}
        />
        <MiniStat label="Status" value={research.status} />
        <MiniStat
          label="Duration"
          value={
            research.completed_at
              ? `${Math.round((new Date(research.completed_at).getTime() - new Date(research.created_at).getTime()) / 1000)}s`
              : "..."
          }
        />
      </div>

      {/* Error */}
      {research.error && (
        <div className="mb-8 rounded-2xl bg-red-50 px-5 py-4">
          <p className="font-semibold text-red-800">Error</p>
          <p className="mt-1 text-sm text-red-700">{research.error}</p>
        </div>
      )}

      {/* Synthesis preview */}
      {research.synthesis && (
        <section className="mb-8">
          <h2 className="mb-3 text-sm font-semibold text-foreground">
            Synthesis Preview
          </h2>
          <div className="rounded-2xl border border-border bg-white p-6">
            <Markdown
              content={
                research.synthesis.length > 500
                  ? research.synthesis.slice(0, 500) + "..."
                  : research.synthesis
              }
            />
          </div>
        </section>
      )}

      {/* Actions */}
      {isDone && (
        <div className="flex gap-3">
          <Link
            href={`/research/${id}/report`}
            className="rounded-full bg-accent px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            View Report
          </Link>
          <Link
            href={`/research/${id}/sources`}
            className="rounded-full border border-border bg-white px-6 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-accent-light"
          >
            View Sources ({research.paper_count})
          </Link>
        </div>
      )}
    </>
  );
}

function MiniStat({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-2xl border border-border bg-accent-light px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">
        {label}
      </p>
      <p className="mt-1 text-lg font-bold text-foreground">{value}</p>
    </div>
  );
}
