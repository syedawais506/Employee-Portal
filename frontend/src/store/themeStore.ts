import { create } from "zustand";

type ThemeMode = "light" | "dark";

const STORAGE_KEY = "employee-portal-theme-mode";

function getInitialMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

interface ThemeState {
  mode: ThemeMode;
  toggleMode: () => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  mode: getInitialMode(),
  toggleMode: () =>
    set((state) => {
      const next = state.mode === "light" ? "dark" : "light";
      localStorage.setItem(STORAGE_KEY, next);
      return { mode: next };
    }),
}));
