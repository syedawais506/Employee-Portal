import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link as RouterLink, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Box, Button, Link, Stack, TextField } from "@mui/material";

import { resetPassword } from "@/api/auth";
import { extractApiErrorMessage } from "@/api/client";

interface FormValues {
  newPassword: string;
  confirmPassword: string;
}

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") ?? "";
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const { control, handleSubmit, watch, formState } = useForm<FormValues>({
    defaultValues: { newPassword: "", confirmPassword: "" },
  });

  async function onSubmit(values: FormValues) {
    setErrorMessage(null);
    try {
      await resetPassword(token, values.newPassword);
      setSuccess(true);
      setTimeout(() => navigate("/login", { replace: true }), 1500);
    } catch (error) {
      setErrorMessage(extractApiErrorMessage(error, "This reset link is invalid or has expired."));
    }
  }

  if (!token) {
    return <Alert severity="error">This reset link is missing its token. Please request a new one.</Alert>;
  }

  if (success) {
    return <Alert severity="success">Password updated. Redirecting to sign in…</Alert>;
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <Stack spacing={2.5}>
        {errorMessage && <Alert severity="error">{errorMessage}</Alert>}

        <Controller
          name="newPassword"
          control={control}
          rules={{ required: "New password is required", minLength: { value: 10, message: "At least 10 characters" } }}
          render={({ field, fieldState }) => (
            <TextField
              {...field}
              label="New password"
              type="password"
              error={Boolean(fieldState.error)}
              helperText={fieldState.error?.message ?? "At least 10 characters, with a letter and a digit"}
              fullWidth
            />
          )}
        />

        <Controller
          name="confirmPassword"
          control={control}
          rules={{
            required: "Please confirm your password",
            validate: (value) => value === watch("newPassword") || "Passwords do not match",
          }}
          render={({ field, fieldState }) => (
            <TextField
              {...field}
              label="Confirm new password"
              type="password"
              error={Boolean(fieldState.error)}
              helperText={fieldState.error?.message}
              fullWidth
            />
          )}
        />

        <Button type="submit" variant="contained" size="large" disabled={formState.isSubmitting} fullWidth>
          Reset password
        </Button>
        <Link component={RouterLink} to="/login" variant="body2" sx={{ alignSelf: "center" }}>
          Back to sign in
        </Link>
      </Stack>
    </Box>
  );
}
