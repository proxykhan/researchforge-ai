"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Markdown } from "@/components/markdown";
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
    return (
      <div className="rounded-2xl bg-red-50 px-5 py-4 text-sm text-red-700">
        {error}
      </div>
    );
  }
  if (!report) {
    return <div className="py-20 text-center text-muted">Loading report...</div>;
  }

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-10">
        <nav className="mb-5 flex items-center gap-2 text-sm text-muted">
          <Link href={`/research/${id}`} className="hover:text-accent">
            Research
          </Link>
          <span>/</span>
          <span className="text-foreground">Report</span>
        </nav>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="mb-2 text-sm font-semibold text-accent">
              Research Report
            </p>
            <h1 className="font-display text-3xl font-bold tracking-tight text-foreground">
              {report.question}
            </h1>
          </div>
          <StatusBadge status={report.status} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-muted">
          <span>{report.paper_count} papers analyzed</span>
          <span className="text-border">|</span>
          <span>{report.search_queries.length} queries executed</span>
          {report.completed_at && (
            <>
              <span className="text-border">|</span>
              <span>
                Completed{" "}
                {new Date(report.completed_at).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
            </>
          )}
        </div>
      </header>

      {report.error && (
        <div className="mb-8 rounded-2xl bg-red-50 px-5 py-4 text-sm text-red-700">
          {report.error}
        </div>
      )}

      {report.synthesis ? (
        <article>
          <div className="rounded-2xl border border-border bg-white p-8">
            <Markdown content={report.synthesis} />
          </div>
        </article>
      ) : (
        <div className="rounded-2xl border-2 border-dashed border-border py-16 text-center text-muted">
          No synthesis available yet. The research may still be in progress.
        </div>
      )}

      <div className="mt-8 flex gap-3">
        <Link
          href={`/research/${id}/sources`}
          className="rounded-full border border-border bg-white px-6 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-accent-light"
        >
          View Sources ({report.paper_count})
        </Link>
        <Link
          href={`/research/${id}`}
          className="rounded-full border border-border bg-white px-6 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-accent-light"
        >
          Back to Progress
        </Link>
      </div>
    </div>
  );
}
