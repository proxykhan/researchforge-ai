"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="mb-4 mt-8 font-display text-2xl font-bold text-foreground">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="mb-3 mt-6 font-display text-xl font-bold text-foreground">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="mb-2 mt-5 font-display text-lg font-semibold text-foreground">
            {children}
          </h3>
        ),
        h4: ({ children }) => (
          <h4 className="mb-2 mt-4 font-semibold text-foreground">
            {children}
          </h4>
        ),
        p: ({ children }) => (
          <p className="mb-3 leading-relaxed text-muted">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="mb-4 ml-5 list-disc space-y-1.5 text-muted">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-4 ml-5 list-decimal space-y-1.5 text-muted">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="leading-relaxed">{children}</li>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-foreground">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="italic text-muted">{children}</em>
        ),
        blockquote: ({ children }) => (
          <blockquote className="mb-4 border-l-3 border-accent pl-4 italic text-muted">
            {children}
          </blockquote>
        ),
        code: ({ children, className }) => {
          const isBlock = className?.includes("language-");
          if (isBlock) {
            return (
              <pre className="mb-4 overflow-x-auto rounded-xl bg-surface p-5">
                <code className="text-sm text-foreground">{children}</code>
              </pre>
            );
          }
          return (
            <code className="rounded-md bg-accent-light px-1.5 py-0.5 font-mono text-sm text-accent">
              {children}
            </code>
          );
        },
        table: ({ children }) => (
          <div className="mb-5 overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-accent-light">{children}</thead>
        ),
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => (
          <tr className="border-b border-border last:border-0">
            {children}
          </tr>
        ),
        th: ({ children }) => (
          <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-accent">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-4 py-2.5 text-muted">{children}</td>
        ),
        hr: () => <hr className="my-8 border-border" />,
        a: ({ children, href }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-accent underline decoration-accent/30 hover:decoration-accent"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
