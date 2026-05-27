import { apiClient } from "./client";
import type { ApiResponse } from "./mock";

export interface ReservedApiResponse {
  implemented: boolean;
  message: string;
  items: Record<string, unknown>[];
}

export async function fetchReservedApi(path: string): Promise<ReservedApiResponse> {
  const response = await apiClient.get<ApiResponse<ReservedApiResponse>>(path);
  return response.data.data;
}

export async function fetchPublicSettings(): Promise<Record<string, unknown>> {
  const response = await apiClient.get<ApiResponse<Record<string, unknown>>>("/api/settings");
  return response.data.data;
}
