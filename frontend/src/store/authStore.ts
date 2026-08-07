import { create } from "zustand";

import type { CurrentUser } from "@/types";

interface AuthState {
  accessToken: string | null;
  user: CurrentUser | null;
  isHydrating: boolean;
  setSession: (accessToken: string, user: CurrentUser) => void;
  setUser: (user: CurrentUser) => void;
  setHydrating: (value: boolean) => void;
  clearSession: () => void;
  hasPermission: (module: string, action: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  isHydrating: true,
  setSession: (accessToken, user) => set({ accessToken, user }),
  setUser: (user) => set({ user }),
  setHydrating: (value) => set({ isHydrating: value }),
  clearSession: () => set({ accessToken: null, user: null }),
  hasPermission: (module, action) => {
    const { user } = get();
    if (!user) return false;
    if (user.is_super_admin) return true;
    return user.permissions.includes(`${module}.${action}`);
  },
}));
