import type { ResearchStatus } from "@/lib/types";
import { STAGE_LABELS, STAGE_ORDER } from "@/lib/types";

export function StagePipeline({ current }: { current: ResearchStatus }) {
  const currentIdx = STAGE_ORDER.indexOf(current);
  const isFailed = current === "failed";

  return (
    <div className="flex items-center gap-1 overflow-x-auto py-2">
      {STAGE_ORDER.map((stage, idx) => {
        let state: "done" | "active" | "pending" = "pending";
        if (isFailed) {
          state = idx <= currentIdx ? "done" : "pending";
        } else if (idx < currentIdx) {
          state = "done";
        } else if (idx === currentIdx) {
          state = "active";
        }

        return (
          <div key={stage} className="flex items-center gap-1">
            {idx > 0 && (
              <div
                className={`h-0.5 w-4 ${
                  state === "pending"
                    ? "bg-zinc-200 dark:bg-zinc-700"
                    : "bg-blue-500"
                }`}
              />
            )}
            <div
              className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium whitespace-nowrap ${
                state === "active"
                  ? "bg-blue-600 text-white ring-2 ring-blue-300 dark:ring-blue-800"
                  : state === "done"
                    ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                    : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500"
              }`}
            >
              {state === "done" && <span>&#10003;</span>}
              {state === "active" && (
                <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
              )}
              {STAGE_LABELS[stage]}
            </div>
          </div>
        );
      })}
    </div>
  );
}
