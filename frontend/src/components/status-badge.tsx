import type { ResearchStatus } from "@/lib/types";
import { STAGE_LABELS } from "@/lib/types";

export function StatusBadge({ status }: { status: ResearchStatus }) {
  return (
    <span
      className={`badge-${status} inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold`}
    >
      {STAGE_LABELS[status]}
    </span>
  );
}
