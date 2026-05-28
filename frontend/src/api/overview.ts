import { apiClient } from "./client";
import type { ApiResponse } from "./types";

export interface MetricCard {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  status: "ready" | "empty" | "error" | string;
  description: string;
}

export interface DependencyStatus {
  name: string;
  status: "ok" | "error" | string;
  message: string;
}

export interface DistributionItem {
  key: string;
  label: string;
  count: number;
}

export interface FlowStep {
  key: string;
  label: string;
  description: string;
  count: number | null;
  status: "ready" | "empty" | "error" | string;
}

export interface OverviewSummary {
  metrics: MetricCard[];
  dependencies: DependencyStatus[];
  entity_types: DistributionItem[];
  relation_types: DistributionItem[];
  document_sources: DistributionItem[];
  flow_steps: FlowStep[];
}

export async function fetchOverviewSummary(): Promise<OverviewSummary> {
  const response = await apiClient.get<ApiResponse<OverviewSummary>>("/api/overview/summary");
  return response.data.data;
}
