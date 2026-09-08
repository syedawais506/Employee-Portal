import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import SendIcon from "@mui/icons-material/Send";
import { Alert, Button, Checkbox, FormControlLabel, Paper, Stack, TextField, Typography } from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import {
  getAIIntegration,
  getSlackIntegration,
  sendSlackTestMessage,
  updateAIIntegration,
  updateSlackIntegration,
} from "@/api/integrations";
import { PageHeader } from "@/components/PageHeader";

export function IntegrationsPage() {
  const queryClient = useQueryClient();
  const [webhookUrl, setWebhookUrl] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: settings } = useQuery({ queryKey: ["integrations", "slack"], queryFn: getSlackIntegration });

  useEffect(() => {
    setWebhookUrl(settings?.slack_webhook_url ?? "");
  }, [settings?.slack_webhook_url]);

  const saveMutation = useMutation({
    mutationFn: () => updateSlackIntegration(webhookUrl.trim() || null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations", "slack"] });
      setSuccessMessage("Webhook URL saved.");
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const testMutation = useMutation({
    mutationFn: sendSlackTestMessage,
    onSuccess: (result) => {
      setSuccessMessage(
        result.sent ? "Test message sent — check your Slack/Teams channel." : "Save a webhook URL first.",
      );
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const { data: aiSettings } = useQuery({ queryKey: ["integrations", "ai"], queryFn: getAIIntegration });

  const aiMutation = useMutation({
    mutationFn: (enabled: boolean) => updateAIIntegration(enabled),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["integrations", "ai"] });
      setSuccessMessage(
        `HR assistant ${result.enabled ? "enabled" : "disabled"}. Employees will see it after their next login or page reload.`,
      );
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  return (
    <>
      <PageHeader title="Integrations" subtitle="Send a message whenever something happens in the portal" />

      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      )}
      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 3, maxWidth: 640 }}>
        <Typography variant="h3" sx={{ mb: 1 }}>
          Slack / Microsoft Teams Webhook
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Paste an incoming webhook URL from Slack or a connector URL from Teams. Every leave, timesheet, asset,
          onboarding, and reminder notification that already appears in the notification bell will also be posted
          there as a plain text message.
        </Typography>
        <Stack spacing={2}>
          <TextField
            label="Webhook URL"
            placeholder="https://hooks.slack.com/services/..."
            fullWidth
            size="small"
            value={webhookUrl}
            onChange={(event) => setWebhookUrl(event.target.value)}
          />
          <Stack direction="row" spacing={1}>
            <Button variant="contained" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              Save
            </Button>
            <Button
              variant="outlined"
              startIcon={<SendIcon />}
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
            >
              Send test message
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 3, maxWidth: 640, mt: 3 }}>
        <Typography variant="h3" sx={{ mb: 1 }}>
          HR Assistant
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Adds an "Ask HR" page where employees can ask questions about leave policy, the holiday calendar, and their
          own leave balances, answered by an AI assistant grounded in your company's own data — never another
          employee's data. Requires the server to have an AI provider configured; contact your platform administrator
          if enabling this has no effect.
        </Typography>
        <FormControlLabel
          control={
            <Checkbox
              checked={aiSettings?.enabled ?? false}
              onChange={(event) => aiMutation.mutate(event.target.checked)}
              disabled={aiMutation.isPending}
            />
          }
          label="Enable the Ask HR assistant for this company"
        />
      </Paper>
    </>
  );
}
