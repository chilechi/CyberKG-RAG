import { apiClient } from "./client";
import type { ApiResponse } from "./mock";

export interface KgCompletionModelMetric {
  model: string;
  mrr: number;
  hits_at_1: number;
  hits_at_3: number;
  hits_at_10: number;
  train_seconds: number;
}

export interface KgCompletionCurvePoint {
  epoch: number;
  transe: number;
  complex: number;
  rotate: number;
}

export interface KgCompletionDataset {
  entity_count: number;
  relation_count: number;
  triple_count: number;
  train_count: number;
  valid_count: number;
  test_count: number;
  entity_types: Record<string, number>;
  relation_types: Record<string, number>;
}

export interface KgCompletionResponse {
  dataset: KgCompletionDataset;
  model_metrics: KgCompletionModelMetric[];
  mrr_curve: KgCompletionCurvePoint[];
  hits_at_10_curve: KgCompletionCurvePoint[];
  loss_curve: KgCompletionCurvePoint[];
  conclusion: string;
}

export interface KgCompletionPrediction {
  rank: number;
  tail: string;
  tail_name: string;
  tail_type: string;
  score: number;
  reason: string;
}

export interface KgCompletionPredictResponse {
  head: string;
  relation: string;
  predictions: KgCompletionPrediction[];
}

export async function fetchKgCompletionSummary(): Promise<KgCompletionResponse> {
  const response = await apiClient.get<ApiResponse<KgCompletionResponse>>("/api/experiments/kg-completion");
  return response.data.data;
}

export async function predictKgCompletion(
  head: string,
  relation: string,
  topK: number,
): Promise<KgCompletionPredictResponse> {
  const response = await apiClient.post<ApiResponse<KgCompletionPredictResponse>>(
    "/api/experiments/kg-completion/predict",
    {
      head,
      relation,
      top_k: topK,
    },
  );
  return response.data.data;
}
