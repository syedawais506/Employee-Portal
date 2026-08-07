import { useEffect } from "react";
import axios from "axios";

import { fetchCurrentUser } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/**
 * The access token lives only in memory (see docs/LLD.md section 6.2), so a
 * hard page reload loses it. On mount, try to mint a fresh one from the
 * httpOnly refresh cookie before deciding whether the user is logged in.
 */
export function useBootstrapSession() {
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const response = await axios.post<{ access_token: string }>(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true },
        );
        if (cancelled) return;
        useAuthStore.setState({ accessToken: response.data.access_token });
        const user = await fetchCurrentUser();
        if (!cancelled) useAuthStore.setState({ user });
      } catch {
        if (!cancelled) useAuthStore.getState().clearSession();
      } finally {
        if (!cancelled) useAuthStore.getState().setHydrating(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);
}
