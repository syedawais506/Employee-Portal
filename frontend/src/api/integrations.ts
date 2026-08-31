import { apiClient } from "@/api/client";
import type { IntegrationSettings } from "@/types";

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
