import { apiClient } from "@/api/client";
import type { ChatMessage } from "@/types";

export async function sendChatMessage(message: string, history: ChatMessage[]): Promise<string> {
  const response = await apiClient.post<{ reply: string }>("/ai/chat", { message, history });
  return response.data.reply;
}
