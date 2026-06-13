import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type AdminUser = {
  id: number;
  email: string;
  fullName: string;
  role?: string;
  status: string;
};

export type UserPrivacyExport = {
  profile: AdminUser & {
    emailVerified?: boolean;
    mfaEnabled?: boolean;
  };
  accountSecurity: {
    mustChangePassword: boolean;
    passwordChangedAt?: string;
    lastLoginAt?: string;
    lockedUntil?: string;
    accessTokensValidAfter?: string;
    mfaEnabled: boolean;
    createdOn?: string;
    createdBy?: string;
    lastModifiedOn?: string;
    lastModifiedBy?: string;
  };
  roleAssignments: Array<{
    id: number;
    roleId: string;
    roleCode: string;
    roleName: string;
    scopeType: string;
    scopeId?: string;
    grantedBy?: string;
    grantedAt?: string;
    expiresAt?: string;
    revokedAt?: string;
    revokedBy?: string;
    createdAt?: string;
  }>;
  exportedAt: string;
};

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get("/admin/v1/users");
  return unwrapList<AdminUser>(data);
}

export async function getUser(id: string): Promise<AdminUser> {
  const { data } = await apiClient.get(`/admin/v1/users/${id}`);
  return unwrap<AdminUser>(data);
}

export type CreateUserInput = {
  email: string;
  fullName: string;
  role: string;
  password: string;
};

export async function createUser(input: CreateUserInput): Promise<AdminUser> {
  const { data } = await apiClient.post("/admin/v1/users", input);
  return unwrap<AdminUser>(data);
}

export async function exportUserPrivacy(id: string): Promise<UserPrivacyExport> {
  const { data } = await apiClient.get(`/admin/v1/users/${id}/privacy-export`);
  return unwrap<UserPrivacyExport>(data);
}

export async function downloadUserPrivacyExport(id: string): Promise<UserPrivacyExport> {
  const payload = await exportUserPrivacy(id);
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `courseflow-user-${id}-privacy-export.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  return payload;
}

export async function deactivateUser(id: string, reason: string): Promise<AdminUser> {
  const { data } = await apiClient.post(`/admin/v1/users/${id}/deactivate`, { reason });
  return unwrap<AdminUser>(data);
}
