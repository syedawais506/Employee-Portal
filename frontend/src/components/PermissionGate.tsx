import type { ReactNode } from "react";

import { useAuthStore } from "@/store/authStore";

interface PermissionGateProps {
  module: string;
  action: string;
  fallback?: ReactNode;
  children: ReactNode;
}

/**
 * UX convenience only — hides actions the user can't perform. The API is
 * the real enforcement boundary (see docs/LLD.md section 6.2).
 */
export function PermissionGate({ module, action, fallback = null, children }: PermissionGateProps) {
  const hasPermission = useAuthStore((state) => state.hasPermission(module, action));
  return hasPermission ? <>{children}</> : <>{fallback}</>;
}
