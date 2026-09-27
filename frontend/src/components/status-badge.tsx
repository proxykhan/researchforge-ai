import type { ResearchStatus } from "@/lib/types";
import { STAGE_LABELS } from "@/lib/types";

const STATUS_COLORS: Record<ResearchStatus, string> = {
  queued: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  planning: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  researching: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  synthesizing: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  verifying: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
  debating: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  critiquing: "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-200",
  evaluating: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
  completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

export function StatusBadge({ status }: { status: ResearchStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[status]}`}
    >
      {STAGE_LABELS[status]}
    </span>
  );
}
