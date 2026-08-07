import { apiClient } from "@/api/client";
import type { PermissionCatalogEntry, PermissionGrant, Role } from "@/types";

export async function listRoles(): Promise<Role[]> {
  const response = await apiClient.get<Role[]>("/roles");
  return response.data;
}

export async function getPermissionCatalog(): Promise<PermissionCatalogEntry[]> {
  const response = await apiClient.get<PermissionCatalogEntry[]>("/permissions/catalog");
  return response.data;
}

export async function createRole(name: string): Promise<Role> {
  const response = await apiClient.post<Role>("/roles", { name });
  return response.data;
}

export async function updateRolePermissions(roleId: string, permissions: PermissionGrant[]): Promise<Role> {
  const response = await apiClient.put<Role>(`/roles/${roleId}/permissions`, { permissions });
  return response.data;
}

export async function deleteRole(roleId: string): Promise<void> {
  await apiClient.delete(`/roles/${roleId}`);
}
