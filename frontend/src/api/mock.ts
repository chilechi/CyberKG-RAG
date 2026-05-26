import { apiClient } from "./client";

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  description: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface QaEvidence {
  source: string;
  entity_id: string;
  text: string;
  score: number;
}

export interface QaAnswer {
  question: string;
  answer: string;
  graph_paths: string[][];
  text_evidence: QaEvidence[];
  confidence: number;
}

export async function fetchMockGraph(): Promise<GraphData> {
  const response = await apiClient.get<ApiResponse<GraphData>>("/api/mock/graph");
  return response.data.data;
}

export async function askMockQuestion(question: string): Promise<QaAnswer> {
  const response = await apiClient.post<ApiResponse<QaAnswer>>("/api/mock/qa", {
    question,
  });
  return response.data.data;
}
