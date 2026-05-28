import { apiClient } from "./client";
import type { ApiResponse, QaAnswer } from "./types";

export type QaMode = "llm" | "rag" | "kg-rag";

export async function askQuestion(question: string, mode: QaMode): Promise<QaAnswer> {
  const response = await apiClient.post<ApiResponse<QaAnswer>>(
    "/api/qa/ask",
    {
      question,
      mode,
    },
    { timeout: 60000 },
  );
  return response.data.data;
}
