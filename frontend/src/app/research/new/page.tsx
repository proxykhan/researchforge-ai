"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function NewResearchPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const job = await api.createResearch(question.trim());
      router.push(`/research/${job.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit");
      setSubmitting(false);
    }
  }

  return (
    <>
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          New Research
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Enter a complex research question and our AI agents will investigate
          it.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-4">
        <div>
          <label
            htmlFor="question"
            className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
          >
            Research Question
          </label>
          <textarea
            id="question"
            rows={4}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder='e.g., "What are the latest approaches to improving long-context reasoning in large language models?"'
            className="mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500"
            minLength={3}
            maxLength={2000}
            required
          />
          <p className="mt-1 text-xs text-zinc-400">
            {question.length}/2000 characters
          </p>
        </div>

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting || question.trim().length < 3}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Start Research"}
        </button>
      </form>

      <div className="mt-12 max-w-2xl rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-900/50">
        <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          What happens next?
        </h3>
        <ol className="mt-2 list-inside list-decimal space-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <li>A planner agent decomposes your question into sub-tasks</li>
          <li>Research agents search academic databases (arXiv, Semantic Scholar, Crossref)</li>
          <li>Paper analyst extracts key findings and claims</li>
          <li>Fact-checker verifies claims against retrieved evidence</li>
          <li>Debate agents argue competing conclusions</li>
          <li>Critic evaluates completeness and may request more research</li>
          <li>Synthesizer produces a citation-grounded report</li>
          <li>Evaluation agent scores the final output</li>
        </ol>
      </div>
    </>
  );
}
