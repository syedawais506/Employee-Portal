import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { useAuthStore } from "@/store/authStore";
import type { ApiErrorBody } from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const response = await axios.post<{ access_token: string }>(
    `${API_BASE_URL}/auth/refresh`,
    {},
    { withCredentials: true },
  );
  return response.data.access_token;
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const originalRequest = error.config as RetriableConfig | undefined;
    const url = originalRequest?.url ?? "";
    // Unauthenticated-by-design endpoints: a 401 here means an invalid/expired
    // resource token (e.g. a public onboarding link), not an expired session —
    // don't try to refresh a session that was never established. Anchored to
    // the start of the path so it doesn't also match the authenticated
    // `/employees/{id}/onboarding/*` management endpoints.
    const isUnauthenticatedEndpoint =
      url.includes("/auth/login") ||
      url.includes("/auth/refresh") ||
      (url.startsWith("/onboarding/") && !url.startsWith("/onboarding/queue"));

    if (error.response?.status === 401 && originalRequest && !originalRequest._retried && !isUnauthenticatedEndpoint) {
      originalRequest._retried = true;
      try {
        refreshPromise ??= refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
        const newToken = await refreshPromise;
        useAuthStore.setState({ accessToken: newToken });
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch {
        useAuthStore.getState().clearSession();
      }
    }

    return Promise.reject(error);
  },
);

export function extractApiErrorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (body?.error?.message) return body.error.message;
  }
  return fallback;
}
