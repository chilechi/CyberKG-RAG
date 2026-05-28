import { apiClient } from "./client";
import type { ApiResponse } from "./types";

export interface DataMetric {
  key: string;
  label: string;
  value: number | null;
  description: string;
  status: "ready" | "empty" | "error" | string;
}

export interface DataSourceItem {
  name: string;
  source_type: string;
  storage_targets: string[];
  document_count: number;
  status: string;
}

export interface DataImportStep {
  key: string;
  label: string;
  description: string;
  count: number | null;
  status: string;
}

export interface DataManagementSummary {
  metrics: DataMetric[];
  sources: DataSourceItem[];
  import_steps: DataImportStep[];
}

export async function fetchDataManagementSummary(): Promise<DataManagementSummary> {
  const response = await apiClient.get<ApiResponse<DataManagementSummary>>("/api/data/summary");
  return response.data.data;
}
