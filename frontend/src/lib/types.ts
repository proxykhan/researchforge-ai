export type ResearchStatus =
  | "queued"
  | "planning"
  | "researching"
  | "synthesizing"
  | "verifying"
  | "debating"
  | "critiquing"
  | "evaluating"
  | "completed"
  | "failed";

export interface ResearchSummary {
  id: string;
  question: string;
  status: ResearchStatus;
  created_at: string;
}

export interface ResearchDetail {
  id: string;
  question: string;
  status: ResearchStatus;
  created_at: string;
  completed_at: string | null;
  search_queries: string[];
  paper_count: number;
  synthesis: string | null;
  error: string | null;
}

export interface PaperResponse {
  source: string;
  source_id: string;
  title: string;
  authors: string[];
  abstract: string;
  url: string;
  published_date: string | null;
  doi: string | null;
  citation_count: number | null;
}

export interface ResearchSourcesResponse {
  id: string;
  papers: PaperResponse[];
}

export interface HealthResponse {
  status: string;
  version: string;
}

export const STAGE_ORDER: ResearchStatus[] = [
  "queued",
  "planning",
  "researching",
  "synthesizing",
  "verifying",
  "debating",
  "critiquing",
  "evaluating",
  "completed",
];

export const STAGE_LABELS: Record<ResearchStatus, string> = {
  queued: "Queued",
  planning: "Planning",
  researching: "Researching",
  synthesizing: "Synthesizing",
  verifying: "Verifying",
  debating: "Debating",
  critiquing: "Critiquing",
  evaluating: "Evaluating",
  completed: "Completed",
  failed: "Failed",
};
