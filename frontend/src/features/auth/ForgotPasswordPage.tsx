import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link as RouterLink } from "react-router-dom";
import { Alert, Box, Button, Link, Stack, TextField, Typography } from "@mui/material";

import { forgotPassword } from "@/api/auth";

interface FormValues {
  email: string;
}

export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const { control, handleSubmit, formState } = useForm<FormValues>({ defaultValues: { email: "" } });

  async function onSubmit(values: FormValues) {
    await forgotPassword(values.email);
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <Stack spacing={2}>
        <Alert severity="success">
          If an account exists for that email, a password reset link has been sent.
        </Alert>
        <Link component={RouterLink} to="/login" variant="body2">
          Back to sign in
        </Link>
      </Stack>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <Stack spacing={2.5}>
        <Typography variant="body2" color="text.secondary">
          Enter your email and we'll send you a link to reset your password.
        </Typography>
        <Controller
          name="email"
          control={control}
          rules={{ required: "Email is required" }}
          render={({ field, fieldState }) => (
            <TextField
              {...field}
              label="Email"
              type="email"
              error={Boolean(fieldState.error)}
              helperText={fieldState.error?.message}
              fullWidth
            />
          )}
        />
        <Button type="submit" variant="contained" size="large" disabled={formState.isSubmitting} fullWidth>
          Send reset link
        </Button>
        <Link component={RouterLink} to="/login" variant="body2" sx={{ alignSelf: "center" }}>
          Back to sign in
        </Link>
      </Stack>
    </Box>
  );
}
