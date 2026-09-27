import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StagePipeline } from "@/components/stage-pipeline";

describe("StagePipeline", () => {
  it("renders all stage labels", () => {
    render(<StagePipeline current="queued" />);
    expect(screen.getByText("Queued")).toBeInTheDocument();
    expect(screen.getByText("Planning")).toBeInTheDocument();
    expect(screen.getByText("Researching")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("marks earlier stages as done", () => {
    render(<StagePipeline current="researching" />);
    const queued = screen.getByText("Queued").closest("div");
    expect(queued?.className).toContain("bg-blue-100");
  });

  it("marks current stage as active", () => {
    render(<StagePipeline current="researching" />);
    const active = screen.getByText("Researching").closest("div");
    expect(active?.className).toContain("bg-blue-600");
  });

  it("marks later stages as pending", () => {
    render(<StagePipeline current="researching" />);
    const pending = screen.getByText("Evaluating").closest("div");
    expect(pending?.className).toContain("bg-zinc-100");
  });

  it("shows checkmark for completed stages", () => {
    render(<StagePipeline current="synthesizing" />);
    const queued = screen.getByText("Queued").closest("div");
    expect(queued?.textContent).toContain("✓");
  });
});
