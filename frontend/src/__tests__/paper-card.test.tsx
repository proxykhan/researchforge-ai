import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PaperCard } from "@/components/paper-card";
import type { PaperResponse } from "@/lib/types";

const basePaper: PaperResponse = {
  source: "arxiv",
  source_id: "2401.00001",
  title: "Attention Is All You Need",
  authors: ["Vaswani", "Shazeer", "Parmar", "Uszkoreit"],
  abstract: "We propose a new architecture based entirely on attention mechanisms.",
  url: "https://arxiv.org/abs/2401.00001",
  published_date: "2024-01-01",
  doi: "10.1234/test",
  citation_count: 42,
};

describe("PaperCard", () => {
  it("renders paper title as a link", () => {
    render(<PaperCard paper={basePaper} />);
    const link = screen.getByText("Attention Is All You Need");
    expect(link.closest("a")).toHaveAttribute("href", basePaper.url);
  });

  it("shows first 3 authors with overflow count", () => {
    render(<PaperCard paper={basePaper} />);
    expect(screen.getByText(/Vaswani, Shazeer, Parmar/)).toBeInTheDocument();
    expect(screen.getByText(/\+1 more/)).toBeInTheDocument();
  });

  it("renders source badge", () => {
    render(<PaperCard paper={basePaper} />);
    expect(screen.getByText("arxiv")).toBeInTheDocument();
  });

  it("renders abstract when present", () => {
    render(<PaperCard paper={basePaper} />);
    expect(screen.getByText(/attention mechanisms/)).toBeInTheDocument();
  });

  it("omits abstract when not provided", () => {
    render(<PaperCard paper={{ ...basePaper, abstract: "" }} />);
    expect(screen.queryByText(/attention mechanisms/)).not.toBeInTheDocument();
  });

  it("renders DOI link", () => {
    render(<PaperCard paper={basePaper} />);
    const doi = screen.getByText(/DOI: 10\.1234\/test/);
    expect(doi.closest("a")).toHaveAttribute(
      "href",
      "https://doi.org/10.1234/test",
    );
  });

  it("renders citation count", () => {
    render(<PaperCard paper={basePaper} />);
    expect(screen.getByText("42 citations")).toBeInTheDocument();
  });
});
