import { apiClient } from "@/api/client";
import type { AIChatbotSettings, IntegrationSettings } from "@/types";

export async function getSlackIntegration(): Promise<IntegrationSettings> {
  const response = await apiClient.get<IntegrationSettings>("/integrations/slack");
  return response.data;
}

export async function updateSlackIntegration(slackWebhookUrl: string | null): Promise<IntegrationSettings> {
  const response = await apiClient.patch<IntegrationSettings>("/integrations/slack", {
    slack_webhook_url: slackWebhookUrl,
  });
  return response.data;
}

export async function sendSlackTestMessage(): Promise<{ sent: boolean }> {
  const response = await apiClient.post<{ sent: boolean }>("/integrations/slack/test");
  return response.data;
}

export async function getAIIntegration(): Promise<AIChatbotSettings> {
  const response = await apiClient.get<AIChatbotSettings>("/integrations/ai");
  return response.data;
}

export async function updateAIIntegration(enabled: boolean): Promise<AIChatbotSettings> {
  const response = await apiClient.patch<AIChatbotSettings>("/integrations/ai", { enabled });
  return response.data;
}
