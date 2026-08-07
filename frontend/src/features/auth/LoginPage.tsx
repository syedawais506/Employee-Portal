import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { Alert, Box, Button, Checkbox, FormControlLabel, Link, Stack, TextField } from "@mui/material";

import { fetchCurrentUser, login } from "@/api/auth";
import { extractApiErrorMessage } from "@/api/client";
import { useAuthStore } from "@/store/authStore";

interface LoginFormValues {
  email: string;
  password: string;
  rememberMe: boolean;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((state) => state.setSession);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<LoginFormValues>({ defaultValues: { email: "", password: "", rememberMe: false } });

  async function onSubmit(values: LoginFormValues) {
    setErrorMessage(null);
    try {
      const tokenResponse = await login({
        email: values.email,
        password: values.password,
        remember_me: values.rememberMe,
      });
      useAuthStore.setState({ accessToken: tokenResponse.access_token });
      const user = await fetchCurrentUser();
      setSession(tokenResponse.access_token, user);
      const redirectTo = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      setErrorMessage(extractApiErrorMessage(error, "Unable to sign in. Please check your credentials."));
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <Stack spacing={2.5}>
        {errorMessage && <Alert severity="error">{errorMessage}</Alert>}

        <Controller
          name="email"
          control={control}
          rules={{ required: "Email is required" }}
          render={({ field, fieldState }) => (
            <TextField
              {...field}
              label="Email"
              type="email"
              autoComplete="email"
              error={Boolean(fieldState.error)}
              helperText={fieldState.error?.message}
              fullWidth
            />
          )}
        />

        <Controller
          name="password"
          control={control}
          rules={{ required: "Password is required" }}
          render={({ field, fieldState }) => (
            <TextField
              {...field}
              label="Password"
              type="password"
              autoComplete="current-password"
              error={Boolean(fieldState.error)}
              helperText={fieldState.error?.message}
              fullWidth
            />
          )}
        />

        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Controller
            name="rememberMe"
            control={control}
            render={({ field }) => (
              <FormControlLabel
                control={<Checkbox {...field} checked={field.value} />}
                label="Remember me"
              />
            )}
          />
          <Link component={RouterLink} to="/forgot-password" variant="body2">
            Forgot password?
          </Link>
        </Stack>

        <Button type="submit" variant="contained" size="large" disabled={isSubmitting} fullWidth>
          Sign in
        </Button>
      </Stack>
    </Box>
  );
}
