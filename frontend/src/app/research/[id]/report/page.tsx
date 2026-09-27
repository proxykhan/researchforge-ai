"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { ResearchDetail } from "@/lib/types";

export default function ResearchReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ResearchDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getResearchReport(id)
      .then(setReport)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load"),
      );
  }, [id]);

  if (error) {
    return <p className="text-sm text-red-500">{error}</p>;
  }
  if (!report) {
    return <p className="text-sm text-zinc-400">Loading report...</p>;
  }

  return (
    <>
      <header className="mb-8">
        <nav className="mb-4 text-xs text-zinc-400">
          <Link href={`/research/${id}`} className="hover:text-blue-500">
            Research
          </Link>
          <span className="mx-1">/</span>
          <span>Report</span>
        </nav>
        <div className="flex items-start justify-between">
          <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
            Research Report
          </h1>
          <StatusBadge status={report.status} />
        </div>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          {report.question}
        </p>
        <div className="mt-2 flex items-center gap-4 text-xs text-zinc-400">
          <span>{report.paper_count} papers analyzed</span>
          <span>{report.search_queries.length} queries executed</span>
          {report.completed_at && (
            <span>
              Completed {new Date(report.completed_at).toLocaleString()}
            </span>
          )}
        </div>
      </header>

      {report.error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950/30">
          <p className="text-sm text-red-700 dark:text-red-300">
            {report.error}
          </p>
        </div>
      )}

      {report.synthesis ? (
        <article className="prose prose-zinc max-w-none dark:prose-invert">
          <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
              {report.synthesis}
            </div>
          </div>
        </article>
      ) : (
        <p className="text-sm text-zinc-400">
          No synthesis available yet. The research may still be in progress.
        </p>
      )}

      <div className="mt-8 flex gap-3">
        <Link
          href={`/research/${id}/sources`}
          className="inline-flex items-center rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          View Sources ({report.paper_count})
        </Link>
        <Link
          href={`/research/${id}`}
          className="inline-flex items-center rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          Back to Progress
        </Link>
      </div>
    </>
  );
}
