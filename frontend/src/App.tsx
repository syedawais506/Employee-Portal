import { useMemo } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { RouterProvider } from "react-router-dom";

import { queryClient } from "@/app/queryClient";
import { useBootstrapSession } from "@/app/useBootstrapSession";
import { router } from "@/routes/router";
import { useThemeStore } from "@/store/themeStore";
import { buildTheme } from "@/theme";

export function App() {
  useBootstrapSession();
  const mode = useThemeStore((state) => state.mode);
  const theme = useMemo(() => buildTheme(mode), [mode]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <RouterProvider router={router} />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
