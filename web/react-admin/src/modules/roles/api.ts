import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";

export type Permission = {
  code: string;
  description: string;
  category: string;
  scopeType?: string;
};

export type PermissionGrant = {
  code: string;
  description?: string;
  category?: string;
  effect: string; // ALLOW | DENY
};

export type Role = {
  id: string;
  code: string;
  name: string;
  description?: string;
  isSystem: boolean;
  parentRoleId?: string;
  permissions?: PermissionGrant[];
};

export type RoleAssignment = {
  id: number;
  userId: number;
  roleId: string;
  roleCode: string;
  roleName: string;
  scopeType: string;
  scopeId?: string;
  grantedBy?: string;
};

export async function listRoles(): Promise<Role[]> {
  const { data } = await apiClient.get("/admin/v1/roles");
  return unwrap<Role[]>(data);
}

export async function getRole(roleId: string): Promise<Role> {
  const { data } = await apiClient.get(`/admin/v1/roles/${roleId}`);
  return unwrap<Role>(data);
}

export async function createRole(input: {
  code: string;
  name: string;
  description?: string;
  parentRoleId?: string;
}): Promise<Role> {
  const { data } = await apiClient.post("/admin/v1/roles", input);
  return unwrap<Role>(data);
}

export async function updateRole(
  roleId: string,
  input: { name: string; description?: string; parentRoleId?: string }
): Promise<Role> {
  const { data } = await apiClient.put(`/admin/v1/roles/${roleId}`, input);
  return unwrap<Role>(data);
}

export async function deleteRole(roleId: string): Promise<void> {
  await apiClient.delete(`/admin/v1/roles/${roleId}`);
}

export async function grantPermission(
  roleId: string,
  permCode: string,
  effect: string
): Promise<Role> {
  const { data } = await apiClient.post(`/admin/v1/roles/${roleId}/permissions`, {
    permCode,
    effect
  });
  return unwrap<Role>(data);
}

export async function revokePermission(roleId: string, permCode: string): Promise<Role> {
  const { data } = await apiClient.delete(
    `/admin/v1/roles/${roleId}/permissions/${permCode}`
  );
  return unwrap<Role>(data);
}

export async function listPermissions(): Promise<Permission[]> {
  const { data } = await apiClient.get("/admin/v1/permissions");
  return unwrap<Permission[]>(data);
}

export async function getUserAssignments(userId: string): Promise<RoleAssignment[]> {
  const { data } = await apiClient.get(`/admin/v1/users/${userId}/assignments`);
  return unwrap<RoleAssignment[]>(data);
}

export async function assignRole(
  userId: string,
  input: {
    roleId: string;
    scopeType: string;
    scopeId?: string;
    grantedBy?: string;
  }
): Promise<RoleAssignment> {
  const { data } = await apiClient.post(`/admin/v1/users/${userId}/assignments`, input);
  return unwrap<RoleAssignment>(data);
}

export async function revokeAssignment(
  userId: string,
  assignmentId: number
): Promise<void> {
  await apiClient.delete(`/admin/v1/users/${userId}/assignments/${assignmentId}`);
}
