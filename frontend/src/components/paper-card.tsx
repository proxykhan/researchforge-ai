import type { PaperResponse } from "@/lib/types";

export function PaperCard({ paper }: { paper: PaperResponse }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-zinc-900 hover:text-blue-600 dark:text-zinc-100 dark:hover:text-blue-400"
          >
            {paper.title}
          </a>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            {paper.authors.slice(0, 3).join(", ")}
            {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
          </p>
        </div>
        <span className="shrink-0 rounded bg-zinc-100 px-2 py-0.5 text-[10px] font-medium uppercase text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
          {paper.source}
        </span>
      </div>

      {paper.abstract && (
        <p className="mt-2 text-xs leading-relaxed text-zinc-600 line-clamp-3 dark:text-zinc-400">
          {paper.abstract}
        </p>
      )}

      <div className="mt-3 flex items-center gap-4 text-xs text-zinc-400 dark:text-zinc-500">
        {paper.published_date && <span>{paper.published_date}</span>}
        {paper.doi && (
          <a
            href={`https://doi.org/${paper.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-blue-500"
          >
            DOI: {paper.doi}
          </a>
        )}
        {paper.citation_count != null && (
          <span>{paper.citation_count} citations</span>
        )}
      </div>
    </div>
  );
}
