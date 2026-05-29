import { apiClient } from "./client";
import type { ApiResponse, QaEvidence } from "./types";

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

export interface QaEvaluationModeSummary {
  avg_final_score: number;
  avg_entity_hit_rate: number;
  avg_relation_hit_rate: number;
  avg_keyword_coverage: number;
  avg_evidence_score: number;
  avg_confidence: number;
  avg_graph_path_count: number;
  avg_text_evidence_count: number;
  avg_elapsed_ms: number;
  case_count: number;
}

export interface QaEvaluationCaseResult {
  mode: string;
  final_score: number;
  entity_hit_rate: number;
  relation_hit_rate: number;
  keyword_coverage: number;
  evidence_score: number;
  confidence: number;
  elapsed_ms: number;
  graph_path_count: number;
  text_evidence_count: number;
  observed_entities: string[];
  observed_relations: string[];
  answer: string;
}

export interface QaEvaluationCase {
  id: string;
  question: string;
  reference_answer: string;
  expected_entities: string[];
  expected_relations: string[];
  expected_keywords: string[];
  best_mode: string;
  results: QaEvaluationCaseResult[];
}

export interface QaEvaluationResponse {
  case_count: number;
  best_mode: string;
  mode_summary: Record<string, QaEvaluationModeSummary>;
  cases: QaEvaluationCase[];
}

export async function getQaComparisonEvaluation(): Promise<QaEvaluationResponse> {
  const response = await apiClient.get<ApiResponse<QaEvaluationResponse>>("/api/experiments/qa-comparison");
  return response.data.data;
}

export async function runQaComparison(question: string): Promise<QaComparisonResponse> {
  const response = await apiClient.post<ApiResponse<QaComparisonResponse>>(
    "/api/experiments/qa-comparison",
    { question },
    { timeout: 60000 },
  );
  return response.data.data;
}
