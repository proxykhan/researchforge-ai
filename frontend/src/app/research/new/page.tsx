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
    <div className="mx-auto max-w-3xl">
      {/* Hero */}
      <header className="mb-10 text-center">
        <p className="mb-3 text-sm font-semibold tracking-wide text-accent">
          New Research
        </p>
        <h1 className="font-display text-4xl font-bold tracking-tight text-foreground">
          What do you want to explore?
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
          Enter your research question and our AI agents will investigate it
          across academic databases.
        </p>
      </header>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label
            htmlFor="question"
            className="mb-2 block text-sm font-semibold text-foreground"
          >
            Research Question
          </label>
          <textarea
            id="question"
            rows={4}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder='e.g., "What are the latest approaches to improving long-context reasoning in large language models?"'
            className="block w-full rounded-2xl border border-border bg-white px-5 py-4 text-foreground placeholder:text-muted/60 focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none"
            minLength={3}
            maxLength={2000}
            required
          />
          <p className="mt-2 text-sm text-muted">
            {question.length}/2000 characters
          </p>
        </div>

        {error && (
          <div className="rounded-2xl bg-red-50 px-5 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting || question.trim().length < 3}
          className="w-full rounded-full bg-accent px-6 py-3 text-base font-semibold text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Starting Research..." : "Start Research"}
        </button>
      </form>

      {/* Steps */}
      <div className="mt-14">
        <h3 className="mb-5 text-center font-display text-xl font-bold text-foreground">
          How it works
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[
            {
              step: "1",
              title: "Plan",
              desc: "AI decomposes your question into focused sub-tasks",
            },
            {
              step: "2",
              title: "Research",
              desc: "Agents search arXiv, Semantic Scholar, and Crossref",
            },
            {
              step: "3",
              title: "Verify & Debate",
              desc: "Claims are fact-checked, then debated by competing agents",
            },
            {
              step: "4",
              title: "Synthesize",
              desc: "A clear, citation-grounded report is produced for you",
            },
          ].map(({ step, title, desc }) => (
            <div
              key={step}
              className="rounded-2xl border border-border bg-accent-light px-5 py-4"
            >
              <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-accent text-sm font-bold text-white">
                {step}
              </div>
              <p className="font-semibold text-foreground">{title}</p>
              <p className="mt-1 text-sm text-muted">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
