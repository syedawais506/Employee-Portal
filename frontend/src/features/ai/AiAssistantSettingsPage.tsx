import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Checkbox, FormControlLabel, Paper, Typography } from "@mui/material";
import { useState } from "react";

import { extractApiErrorMessage } from "@/api/client";
import { getAIIntegration, updateAIIntegration } from "@/api/integrations";
import { PageHeader } from "@/components/PageHeader";

export function AiAssistantSettingsPage() {
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

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
      <PageHeader title="AI Assistant" subtitle="Turn the Ask HR assistant on or off for your company." />

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
