import { Box, CircularProgress } from "@mui/material";
import { Navigate, Outlet } from "react-router-dom";

import { useAuthStore } from "@/store/authStore";

export function ProtectedRoute() {
  const isHydrating = useAuthStore((state) => state.isHydrating);
  const user = useAuthStore((state) => state.user);

  if (isHydrating) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export function RequirePermission({ module, action }: { module: string; action: string }) {
  const hasPermission = useAuthStore((state) => state.hasPermission(module, action));
  if (!hasPermission) return <Navigate to="/" replace />;
  return <Outlet />;
}

export function RequireSuperAdmin() {
  const isSuperAdmin = useAuthStore((state) => state.user?.is_super_admin ?? false);
  if (!isSuperAdmin) return <Navigate to="/" replace />;
  return <Outlet />;
}
