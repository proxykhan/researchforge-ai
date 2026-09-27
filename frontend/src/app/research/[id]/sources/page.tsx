"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PaperCard } from "@/components/paper-card";
import { api } from "@/lib/api";
import type { ResearchSourcesResponse } from "@/lib/types";

export default function ResearchSourcesPage() {
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
    return <p className="text-sm text-red-500">{error}</p>;
  }
  if (!data) {
    return <p className="text-sm text-zinc-400">Loading sources...</p>;
  }

  const filtered = data.papers.filter(
    (p) =>
      !filter ||
      p.title.toLowerCase().includes(filter.toLowerCase()) ||
      p.authors.some((a) => a.toLowerCase().includes(filter.toLowerCase())),
  );

  return (
    <>
      <header className="mb-6">
        <nav className="mb-4 text-xs text-zinc-400">
          <Link href={`/research/${id}`} className="hover:text-blue-500">
            Research
          </Link>
          <span className="mx-1">/</span>
          <span>Sources</span>
        </nav>
        <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          Sources & Papers
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          {data.papers.length} papers discovered during research
        </p>
      </header>

      {data.papers.length > 0 && (
        <div className="mb-4">
          <input
            type="text"
            placeholder="Filter by title or author..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full max-w-md rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
          />
        </div>
      )}

      {filtered.length === 0 && data.papers.length > 0 && (
        <p className="text-sm text-zinc-400">
          No papers match your filter.
        </p>
      )}

      <div className="space-y-3">
        {filtered.map((paper) => (
          <PaperCard key={`${paper.source}-${paper.source_id}`} paper={paper} />
        ))}
      </div>

      {data.papers.length === 0 && (
        <p className="text-sm text-zinc-400">
          No papers found for this research.
        </p>
      )}
    </>
  );
}
