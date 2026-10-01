import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/status-badge";
import type { ResearchStatus } from "@/lib/types";

describe("StatusBadge", () => {
  it("renders the label for each status", () => {
    const statuses: ResearchStatus[] = [
      "queued",
      "planning",
      "researching",
      "completed",
      "failed",
    ];

    for (const status of statuses) {
      const { unmount } = render(<StatusBadge status={status} />);
      const label = status.charAt(0).toUpperCase() + status.slice(1);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it("applies completed styling", () => {
    render(<StatusBadge status="completed" />);
    const badge = screen.getByText("Completed");
    expect(badge.className).toContain("badge-completed");
  });

  it("applies failed styling", () => {
    render(<StatusBadge status="failed" />);
    const badge = screen.getByText("Failed");
    expect(badge.className).toContain("badge-failed");
  });
});
