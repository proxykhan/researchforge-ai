"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Markdown } from "@/components/markdown";
import { StagePipeline } from "@/components/stage-pipeline";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { ResearchDetail } from "@/lib/types";

export default function ResearchProgressPage() {
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
    return <p className="text-sm text-red-500">{error}</p>;
  }
  if (!research) {
    return <p className="text-sm text-zinc-400">Loading...</p>;
  }

  const isDone =
    research.status === "completed" || research.status === "failed";

  return (
    <>
      <header className="mb-6">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
              {research.question}
            </h1>
            <p className="mt-1 text-xs text-zinc-400">
              Started {new Date(research.created_at).toLocaleString()}
            </p>
          </div>
          <StatusBadge status={research.status} />
        </div>
      </header>

      {/* Stage pipeline */}
      <section className="mb-8">
        <h2 className="mb-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Progress
        </h2>
        <StagePipeline current={research.status} />
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
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950/30">
          <p className="text-sm font-medium text-red-800 dark:text-red-300">
            Error
          </p>
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {research.error}
          </p>
        </div>
      )}

      {/* Synthesis preview */}
      {research.synthesis && (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
            Synthesis Preview
          </h2>
          <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
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
            className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            View Report
          </Link>
          <Link
            href={`/research/${id}/sources`}
            className="inline-flex items-center rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
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
    <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-[10px] font-medium uppercase tracking-wide text-zinc-400">
        {label}
      </p>
      <p className="mt-0.5 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        {value}
      </p>
    </div>
  );
}
