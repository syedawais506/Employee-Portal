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
  const isSuperAdmin = useAuthStore((state) => state.user?.is_super_admin ?? false);
  const hasPermission = useAuthStore((state) => state.hasPermission(module, action));
  // Super Admin has no company_id/employee record, so hasPermission's blanket
  // "super admin can do anything" bypass (correct for the backend, which
  // still requires a company context on every tenant-scoped endpoint) would
  // otherwise let them into a page that just errors on every API call.
  if (isSuperAdmin || !hasPermission) return <Navigate to="/" replace />;
  return <Outlet />;
}

export function RequireSuperAdmin() {
  const isSuperAdmin = useAuthStore((state) => state.user?.is_super_admin ?? false);
  if (!isSuperAdmin) return <Navigate to="/" replace />;
  return <Outlet />;
}

export function RequireNotSuperAdmin() {
  const isSuperAdmin = useAuthStore((state) => state.user?.is_super_admin ?? false);
  if (isSuperAdmin) return <Navigate to="/" replace />;
  return <Outlet />;
}
