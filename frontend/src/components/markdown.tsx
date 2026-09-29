"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="mb-4 mt-6 text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="mb-3 mt-5 text-xl font-bold text-zinc-900 dark:text-zinc-100">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="mb-2 mt-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {children}
          </h3>
        ),
        h4: ({ children }) => (
          <h4 className="mb-2 mt-3 text-base font-semibold text-zinc-900 dark:text-zinc-100">
            {children}
          </h4>
        ),
        p: ({ children }) => (
          <p className="mb-3 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
            {children}
          </p>
        ),
        ul: ({ children }) => (
          <ul className="mb-3 ml-4 list-disc space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-3 ml-4 list-decimal space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
            {children}
          </ol>
        ),
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        strong: ({ children }) => (
          <strong className="font-semibold text-zinc-900 dark:text-zinc-100">
            {children}
          </strong>
        ),
        em: ({ children }) => (
          <em className="italic text-zinc-600 dark:text-zinc-400">
            {children}
          </em>
        ),
        blockquote: ({ children }) => (
          <blockquote className="mb-3 border-l-2 border-blue-500 pl-4 italic text-zinc-600 dark:text-zinc-400">
            {children}
          </blockquote>
        ),
        code: ({ children, className }) => {
          const isBlock = className?.includes("language-");
          if (isBlock) {
            return (
              <pre className="mb-3 overflow-x-auto rounded-lg bg-zinc-100 p-4 dark:bg-zinc-800">
                <code className="text-xs text-zinc-800 dark:text-zinc-200">
                  {children}
                </code>
              </pre>
            );
          }
          return (
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs font-mono text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200">
              {children}
            </code>
          );
        },
        table: ({ children }) => (
          <div className="mb-4 overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="border-b border-zinc-300 dark:border-zinc-600">
            {children}
          </thead>
        ),
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => (
          <tr className="border-b border-zinc-200 dark:border-zinc-700">
            {children}
          </tr>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-400">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300">
            {children}
          </td>
        ),
        hr: () => (
          <hr className="my-6 border-zinc-200 dark:border-zinc-700" />
        ),
        a: ({ children, href }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 underline hover:text-blue-500 dark:text-blue-400"
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
