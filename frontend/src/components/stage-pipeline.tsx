import type { ResearchStatus } from "@/lib/types";
import { STAGE_LABELS, STAGE_ORDER } from "@/lib/types";

export function StagePipeline({ current }: { current: ResearchStatus }) {
  const currentIdx = STAGE_ORDER.indexOf(current);
  const isFailed = current === "failed";

  return (
    <div className="flex items-center gap-1.5 overflow-x-auto py-1">
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
          <div key={stage} className="flex items-center gap-1.5">
            {idx > 0 && (
              <div
                className={`h-0.5 w-5 rounded ${
                  state === "pending" ? "bg-border" : "bg-accent"
                }`}
              />
            )}
            <div
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-all ${
                state === "active"
                  ? "bg-accent text-white shadow-sm"
                  : state === "done"
                    ? "bg-accent/10 text-accent"
                    : "bg-gray-100 text-muted"
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
