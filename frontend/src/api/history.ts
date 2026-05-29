import { apiClient } from "./client";
import type { ApiResponse, QaEvidence } from "./types";

export interface HistoryItem {
  id: number;
  question: string;
  answer: string;
  mode: string;
  confidence: number;
  elapsed_ms: number;
  graph_path_count: number;
  text_evidence_count: number;
  graph_paths: string[][];
  text_evidence: QaEvidence[];
  created_at: string;
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface HistoryStats {
  total: number;
  avg_confidence: number | null;
  avg_elapsed_ms: number | null;
  kg_rag_count: number;
}

export async function fetchHistory(page = 1, pageSize = 10, keyword = ""): Promise<HistoryListResponse> {
  const response = await apiClient.get<ApiResponse<HistoryListResponse>>("/api/history", {
    params: { page, page_size: pageSize, keyword },
  });
  return response.data.data;
}

export async function fetchHistoryStats(): Promise<HistoryStats> {
  const response = await apiClient.get<ApiResponse<HistoryStats>>("/api/history/stats");
  return response.data.data;
}

export async function deleteHistoryItem(id: number): Promise<void> {
  await apiClient.delete(`/api/history/${id}`);
}
