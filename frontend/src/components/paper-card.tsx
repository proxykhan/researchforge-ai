import type { PaperResponse } from "@/lib/types";

export function PaperCard({ paper }: { paper: PaperResponse }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 transition-all hover:shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-foreground hover:text-accent"
          >
            {paper.title}
          </a>
          <p className="mt-1.5 text-sm text-muted">
            {paper.authors.slice(0, 3).join(", ")}
            {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-accent-light px-3 py-1 text-xs font-semibold text-accent">
          {paper.source}
        </span>
      </div>

      {paper.abstract && (
        <p className="mt-3 text-sm leading-relaxed text-muted line-clamp-3">
          {paper.abstract}
        </p>
      )}

      <div className="mt-3 flex items-center gap-4 text-sm text-muted">
        {paper.published_date && <span>{paper.published_date}</span>}
        {paper.doi && (
          <a
            href={`https://doi.org/${paper.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-accent"
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
