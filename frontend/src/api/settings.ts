import { apiClient } from "./client";
import type { ApiResponse } from "./types";

export interface ConnectionSetting {
  name: string;
  host: string;
  port: number | string;
  database: string;
  status: "ok" | "error" | string;
  message: string;
}

export interface ModelSetting {
  llm_provider: string;
  llm_model: string;
  llm_base_url: string;
  llm_timeout: number;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  embedding_url: string;
  milvus_collection: string;
  dashscope_configured: boolean;
  deepseek_configured: boolean;
}

export interface BasicSetting {
  system_name: string;
  description: string;
  default_qa_mode: string;
  language: string;
  timezone: string;
}

export interface SettingsResponse {
  basic: BasicSetting;
  model: ModelSetting;
  connections: ConnectionSetting[];
}

export async function fetchSettings(): Promise<SettingsResponse> {
  const response = await apiClient.get<ApiResponse<SettingsResponse>>("/api/settings");
  return response.data.data;
}
