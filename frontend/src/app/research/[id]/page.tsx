"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Markdown } from "@/components/markdown";
import { StagePipeline } from "@/components/stage-pipeline";
import { StatusBadge } from "@/components/status-badge";
import { AuthGuard } from "@/components/auth-guard";
import { api } from "@/lib/api";
import type { ResearchDetail, ResearchStatus } from "@/lib/types";
import { STAGE_ORDER } from "@/lib/types";

const STAGE_MESSAGES: Record<ResearchStatus, string> = {
  queued: "Preparing to start your research",
  planning: "Breaking down your question into focused sub-tasks",
  researching: "Searching academic databases for relevant papers",
  synthesizing: "Analyzing and combining findings into a coherent synthesis",
  verifying: "Fact-checking claims and cross-referencing sources",
  debating: "AI agents are debating different perspectives",
  critiquing: "Critically evaluating the research quality",
  evaluating: "Running final evaluation and quality assessment",
  completed: "Research complete",
  failed: "Research encountered an error",
};

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

  const isDone =
    research !== null &&
    (research.status === "completed" || research.status === "failed");

  useEffect(() => {
    load();
    if (isDone) return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [load, isDone]);

  if (error) {
    return (
      <div className="rounded-2xl bg-error-bg px-5 py-4 text-sm text-error-fg">
        {error}
      </div>
    );
  }
  if (!research) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        <p className="mt-4 text-muted">Loading research...</p>
      </div>
    );
  }

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

      {/* Activity Banner — visible while research is in progress */}
      {!isDone && (
        <section className="mb-8">
          <div className="flex items-center gap-4 rounded-2xl border border-accent/20 bg-accent-light p-5">
            <div className="relative flex h-12 w-12 shrink-0 items-center justify-center">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/20" />
              <span className="relative flex h-6 w-6 items-center justify-center rounded-full bg-accent">
                <span className="h-2 w-2 rounded-full bg-white" />
              </span>
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-foreground">
                {STAGE_MESSAGES[research.status]}
                <AnimatedDots />
              </p>
              <p className="mt-0.5 text-sm text-muted">
                Stage {STAGE_ORDER.indexOf(research.status) + 1} of{" "}
                {STAGE_ORDER.length - 1} &middot; Elapsed:{" "}
                <ElapsedTime startTime={research.created_at} />
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Stats */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MiniStat label="Papers Found" value={research.paper_count} />
        <MiniStat
          label="Search Queries"
          value={research.search_queries.length}
        />
        <MiniStat label="Status" value={research.status} />
        <div className="rounded-2xl border border-border bg-accent-light px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">
            Duration
          </p>
          <p className="mt-1 text-lg font-bold text-foreground">
            {research.completed_at ? (
              formatDuration(
                new Date(research.completed_at).getTime() -
                  new Date(research.created_at).getTime(),
              )
            ) : (
              <ElapsedTime startTime={research.created_at} />
            )}
          </p>
        </div>
      </div>

      {/* Error */}
      {research.error && (
        <div className="mb-8 rounded-2xl bg-error-bg px-5 py-4">
          <p className="font-semibold text-error-fg">Error</p>
          <p className="mt-1 text-sm text-error-fg/80">{research.error}</p>
        </div>
      )}

      {/* Synthesis preview */}
      {research.synthesis && (
        <section className="mb-8">
          <h2 className="mb-3 text-sm font-semibold text-foreground">
            Synthesis Preview
          </h2>
          <div className="rounded-2xl border border-border bg-card p-6">
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
      {isDone && research.status === "completed" && (
        <div className="flex gap-3">
          <Link
            href={`/research/${id}/report`}
            className="rounded-full bg-accent px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            View Report
          </Link>
          <Link
            href={`/research/${id}/sources`}
            className="rounded-full border border-border bg-card px-6 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-accent-light"
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

function formatDuration(ms: number): string {
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

function ElapsedTime({ startTime }: { startTime: string }) {
  const [elapsed, setElapsed] = useState("0s");

  useEffect(() => {
    const start = new Date(startTime).getTime();
    function update() {
      const diff = Math.max(0, Date.now() - start);
      setElapsed(formatDuration(diff));
    }
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [startTime]);

  return <span>{elapsed}</span>;
}

function AnimatedDots() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setCount((c) => (c + 1) % 4), 400);
    return () => clearInterval(id);
  }, []);

  return (
    <span className="inline-block w-5 text-left">
      {".".repeat(count)}
    </span>
  );
}
