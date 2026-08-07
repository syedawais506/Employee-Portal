import { useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { getOnboardingContext, setOnboardingPassword, uploadOnboardingDocument } from "@/api/onboarding";
import type { DocumentType, EmployeeDocument } from "@/types";

const STATUS_LABEL: Record<string, string> = {
  invited: "Awaiting your submission",
  submitted: "Submitted — awaiting HR review",
  hr_approved: "Reviewed by HR — awaiting final activation",
  completed: "Onboarding complete — your account is active",
};

interface PasswordFormValues {
  password: string;
  confirmPassword: string;
}

function DocumentRow({
  token,
  documentType,
  document,
  disabled,
  onUploaded,
}: {
  token: string;
  documentType: DocumentType;
  document?: EmployeeDocument;
  disabled: boolean;
  onUploaded: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (file: File) => uploadOnboardingDocument(token, documentType.id, file),
    onSuccess: onUploaded,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const statusColor = document?.status === "approved" ? "success" : document?.status === "rejected" ? "error" : "default";

  return (
    <Box sx={{ py: 1.5 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="body1">{documentType.name}</Typography>
          {documentType.is_required && <Chip label="Required" size="small" variant="outlined" />}
          {document && <Chip label={document.status} size="small" color={statusColor} />}
        </Stack>
        <Stack direction="row" spacing={1} alignItems="center">
          {document && (
            <Typography variant="caption" color="text.secondary">
              {document.original_filename}
            </Typography>
          )}
          <Button
            size="small"
            startIcon={mutation.isPending ? <CircularProgress size={14} /> : <UploadFileIcon fontSize="small" />}
            disabled={disabled || mutation.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            {document ? "Replace" : "Upload"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            hidden
            accept="application/pdf,image/png,image/jpeg"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                setErrorMessage(null);
                mutation.mutate(file);
              }
              event.target.value = "";
            }}
          />
        </Stack>
      </Stack>
      {document?.status === "rejected" && document.review_notes && (
        <Alert severity="warning" sx={{ mt: 1 }}>
          HR requested changes: {document.review_notes}
        </Alert>
      )}
      {errorMessage && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {errorMessage}
        </Alert>
      )}
    </Box>
  );
}

export function PublicOnboardingPage() {
  const { token } = useParams<{ token: string }>();
  const queryClient = useQueryClient();
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const { data: context, isLoading, isError, error } = useQuery({
    queryKey: ["onboarding-context", token],
    queryFn: () => getOnboardingContext(token as string),
    enabled: Boolean(token),
    retry: false,
  });

  const { control, handleSubmit, watch } = useForm<PasswordFormValues>({
    defaultValues: { password: "", confirmPassword: "" },
  });

  const passwordMutation = useMutation({
    mutationFn: (password: string) => setOnboardingPassword(token as string, password),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["onboarding-context", token] }),
    onError: (err) => setPasswordError(extractApiErrorMessage(err)),
  });

  function refetchContext() {
    queryClient.invalidateQueries({ queryKey: ["onboarding-context", token] });
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", justifyContent: "center", bgcolor: "background.default", py: 6, px: 2 }}>
      <Paper elevation={0} sx={{ width: "100%", maxWidth: 640, height: "fit-content", p: 4, border: "1px solid", borderColor: "divider" }}>
        <Typography variant="h2" sx={{ mb: 0.5 }}>
          Welcome to Employee Portal
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Complete your onboarding below.
        </Typography>

        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {isError && (
          <Alert severity="error">{extractApiErrorMessage(error, "This onboarding link is invalid or has expired.")}</Alert>
        )}

        {context && (
          <Stack spacing={3}>
            <Alert severity={context.employee.onboarding_status === "completed" ? "success" : "info"}>
              <b>{context.employee.company_name}</b> — {STATUS_LABEL[context.employee.onboarding_status]}
            </Alert>

            <Typography variant="body1">
              Hi {context.employee.first_name}, please set a password and upload the documents below.
            </Typography>

            {context.employee.onboarding_status === "completed" ? (
              <Alert severity="success" icon={<CheckCircleIcon />}>
                Your account is active. You can now{" "}
                <a href="/login" style={{ color: "inherit" }}>
                  sign in
                </a>
                .
              </Alert>
            ) : (
              <>
                {!context.password_already_set && (
                  <Box component="form" onSubmit={handleSubmit((values) => {
                    setPasswordError(null);
                    if (values.password !== values.confirmPassword) {
                      setPasswordError("Passwords do not match");
                      return;
                    }
                    passwordMutation.mutate(values.password);
                  })}>
                    <Typography variant="h3" sx={{ mb: 1.5 }}>
                      Set your password
                    </Typography>
                    {passwordError && (
                      <Alert severity="error" sx={{ mb: 2 }}>
                        {passwordError}
                      </Alert>
                    )}
                    <Stack spacing={2}>
                      <Controller
                        name="password"
                        control={control}
                        rules={{ required: "Required", minLength: { value: 10, message: "At least 10 characters" } }}
                        render={({ field, fieldState }) => (
                          <TextField
                            {...field}
                            type="password"
                            label="Password"
                            fullWidth
                            error={Boolean(fieldState.error)}
                            helperText={fieldState.error?.message ?? "At least 10 characters, with a letter and a digit"}
                          />
                        )}
                      />
                      <Controller
                        name="confirmPassword"
                        control={control}
                        rules={{ required: "Required", validate: (v) => v === watch("password") || "Passwords do not match" }}
                        render={({ field, fieldState }) => (
                          <TextField
                            {...field}
                            type="password"
                            label="Confirm password"
                            fullWidth
                            error={Boolean(fieldState.error)}
                            helperText={fieldState.error?.message}
                          />
                        )}
                      />
                      <Box>
                        <Button type="submit" variant="contained" disabled={passwordMutation.isPending}>
                          Save password
                        </Button>
                      </Box>
                    </Stack>
                  </Box>
                )}

                {context.password_already_set && (
                  <Alert severity="success" variant="outlined">
                    Password set.
                  </Alert>
                )}

                <Divider />

                <Box>
                  <Typography variant="h3" sx={{ mb: 1 }}>
                    Documents
                  </Typography>
                  {context.document_types.map((documentType) => (
                    <DocumentRow
                      key={documentType.id}
                      token={token as string}
                      documentType={documentType}
                      document={context.uploaded_documents.find((d) => d.document_type_id === documentType.id)}
                      disabled={!["invited", "submitted"].includes(context.employee.onboarding_status)}
                      onUploaded={refetchContext}
                    />
                  ))}
                </Box>
              </>
            )}
          </Stack>
        )}
      </Paper>
    </Box>
  );
}
