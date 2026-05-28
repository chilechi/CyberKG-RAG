import { apiClient } from "./client";
import type { ApiResponse, QaEvidence } from "./mock";

export interface QaComparisonResult {
  mode: string;
  answer: string;
  confidence: number;
  elapsed_ms: number;
  graph_path_count: number;
  text_evidence_count: number;
  graph_paths: string[][];
  text_evidence: QaEvidence[];
}

export interface QaComparisonMetric {
  best_mode: string;
  fastest_mode: string;
  max_confidence: number;
  total_elapsed_ms: number;
}

export interface QaComparisonResponse {
  question: string;
  results: QaComparisonResult[];
  metrics: QaComparisonMetric;
}

export async function runQaComparison(question: string): Promise<QaComparisonResponse> {
  const response = await apiClient.post<ApiResponse<QaComparisonResponse>>(
    "/api/experiments/qa-comparison",
    { question },
    { timeout: 60000 },
  );
  return response.data.data;
}
