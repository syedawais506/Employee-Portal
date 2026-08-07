import { apiClient } from "@/api/client";
import type { CurrentUser } from "@/types";

export interface LoginPayload {
  email: string;
  password: string;
  remember_me: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/auth/login", payload);
  return response.data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await apiClient.get<CurrentUser>("/auth/me");
  return response.data;
}

export async function forgotPassword(email: string): Promise<void> {
  await apiClient.post("/auth/forgot-password", { email });
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await apiClient.post("/auth/reset-password", { token, new_password: newPassword });
}
