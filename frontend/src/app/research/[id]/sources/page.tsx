"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PaperCard } from "@/components/paper-card";
import { AuthGuard } from "@/components/auth-guard";
import { api } from "@/lib/api";
import type { ResearchSourcesResponse } from "@/lib/types";

export default function ResearchSourcesPage() {
  return (
    <AuthGuard>
      <ResearchSourcesContent />
    </AuthGuard>
  );
}

function ResearchSourcesContent() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ResearchSourcesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api
      .getResearchSources(id)
      .then(setData)
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
  if (!data) {
    return <div className="py-20 text-center text-muted">Loading sources...</div>;
  }

  const filtered = data.papers.filter(
    (p) =>
      !filter ||
      p.title.toLowerCase().includes(filter.toLowerCase()) ||
      p.authors.some((a) => a.toLowerCase().includes(filter.toLowerCase())),
  );

  return (
    <>
      <header className="mb-8">
        <nav className="mb-5 flex items-center gap-2 text-sm text-muted">
          <Link href={`/research/${id}`} className="hover:text-accent">
            Research
          </Link>
          <span>/</span>
          <span className="text-foreground">Sources</span>
        </nav>
        <p className="mb-2 text-sm font-semibold text-accent">Sources</p>
        <h1 className="font-display text-3xl font-bold tracking-tight text-foreground">
          Papers & References
        </h1>
        <p className="mt-2 text-muted">
          {data.papers.length} papers discovered during research
        </p>
      </header>

      {data.papers.length > 0 && (
        <div className="mb-6">
          <input
            type="text"
            placeholder="Filter by title or author..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full max-w-md rounded-full border border-border bg-white px-5 py-2.5 text-sm text-foreground placeholder:text-muted/60 focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none"
          />
        </div>
      )}

      {filtered.length === 0 && data.papers.length > 0 && (
        <p className="text-muted">No papers match your filter.</p>
      )}

      <div className="space-y-4">
        {filtered.map((paper) => (
          <PaperCard key={`${paper.source}-${paper.source_id}`} paper={paper} />
        ))}
      </div>

      {data.papers.length === 0 && (
        <div className="rounded-2xl border-2 border-dashed border-border py-16 text-center text-muted">
          No papers found for this research.
        </div>
      )}
    </>
  );
}
