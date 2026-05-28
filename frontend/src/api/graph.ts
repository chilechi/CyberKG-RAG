import { apiClient } from "./client";
import type { ApiResponse, GraphData } from "./types";

export async function fetchGraphNeighbors(entityId: string, depth: number): Promise<GraphData> {
  const response = await apiClient.get<ApiResponse<GraphData>>("/api/graph/neighbors", {
    params: {
      entity_id: entityId,
      depth,
    },
  });
  return response.data.data;
}
