import type { ResearchStatus } from "@/lib/types";
import { STAGE_LABELS } from "@/lib/types";

const STATUS_COLORS: Record<ResearchStatus, string> = {
  queued: "bg-gray-100 text-gray-600",
  planning: "bg-amber-50 text-amber-700",
  researching: "bg-blue-50 text-blue-700",
  synthesizing: "bg-purple-50 text-purple-700",
  verifying: "bg-cyan-50 text-cyan-700",
  debating: "bg-orange-50 text-orange-700",
  critiquing: "bg-rose-50 text-rose-700",
  evaluating: "bg-indigo-50 text-indigo-700",
  completed: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-700",
};

export function StatusBadge({ status }: { status: ResearchStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${STATUS_COLORS[status]}`}
    >
      {STAGE_LABELS[status]}
    </span>
  );
}
