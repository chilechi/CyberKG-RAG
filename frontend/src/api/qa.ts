import { apiClient } from "./client";
import type { ApiResponse, QaAnswer } from "./mock";

export async function askKgRagQuestion(question: string): Promise<QaAnswer> {
  const response = await apiClient.post<ApiResponse<QaAnswer>>("/api/qa/ask", {
    question,
  });
  return response.data.data;
}
