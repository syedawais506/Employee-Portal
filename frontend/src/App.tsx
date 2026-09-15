import { Suspense, useMemo } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { RouterProvider } from "react-router-dom";

import { queryClient } from "@/app/queryClient";
import { useBootstrapSession } from "@/app/useBootstrapSession";
import { RouteLoadingFallback } from "@/components/RouteLoadingFallback";
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
        {/* Single boundary covers every route below, regardless of which
            layout (or no layout, e.g. the public onboarding page) wraps it —
            simpler than one Suspense per layout's <Outlet />. */}
        <Suspense fallback={<RouteLoadingFallback />}>
          <RouterProvider router={router} />
        </Suspense>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
