import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronUp, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  FormField,
  Input,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Textarea,
  Th
} from "@/shared/ui";
import { fallbackCourses, listCourses } from "@/modules/courses/api";
import { listUsers, type AdminUser } from "@/modules/identity/api";
import { listDepartments } from "@/modules/organization/api";
import {
  assignRole,
  createRole,
  deleteRole,
  getRole,
  grantPermission,
  getUserAssignments,
  listPermissions,
  listRoles,
  revokeAssignment,
  revokePermission,
  updateRole
} from "./api";
import type { Role } from "./api";

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function roleLabel(role?: Pick<Role, "code" | "name">, fallbackId?: string) {
  if (role) return [role.code, role.name].filter(Boolean).join(" · ");
  return fallbackId ? `Role ${compactId(fallbackId)}` : "Chọn vai trò";
}

function userLabel(user?: Pick<AdminUser, "fullName" | "email">, fallbackId?: string) {
  if (user) return `${user.fullName || user.email} · ${user.email}`;
  return fallbackId ? `User ${compactId(fallbackId)}` : "Chọn người dùng";
}

function courseLabel(course?: { code?: string; title?: string }, fallbackId?: string) {
  if (course) return [course.code, course.title].filter(Boolean).join(" · ");
  return fallbackId ? `Course ${compactId(fallbackId)}` : "Chọn khóa học";
}

function orgLabel(org?: { code?: string; name?: string }, fallbackId?: string) {
  if (org) return [org.code, org.name].filter(Boolean).join(" · ");
  return fallbackId ? `Org ${compactId(fallbackId)}` : "Chọn tổ chức/phòng ban";
}

// ---------------------------------------------------------------------------
// RolesListPage
// ---------------------------------------------------------------------------
export function RolesListPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.roles.list,
    queryFn: listRoles
  });
  const roleById = useMemo(() => new Map((data ?? []).map((role) => [role.id, role])), [data]);

  const deleteMutation = useMutation({
    mutationFn: (roleId: string) => deleteRole(roleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.roles.list })
  });

  function handleDelete(roleId: string, name: string) {
    if (window.confirm(`Bạn có chắc muốn xóa vai trò "${name}"?`)) {
      deleteMutation.mutate(roleId);
    }
  }

  return (
    <div>
      <PageHeader
        title="Vai trò & Phân quyền"
        description="Quản lý vai trò và phân quyền hệ thống"
        actions={
          <div className="flex gap-2">
            <Link to="user-assignments">
              <Button variant="secondary">Phân công người dùng</Button>
            </Link>
            <Link to="new">
              <Button>
                <Plus size={16} /> Thêm vai trò
              </Button>
            </Link>
          </div>
        }
      />
      <Card>
        <CardHeader title="Danh sách vai trò" />
        {isLoading && <Spinner />}
        {isError && <ErrorState error={error} />}
        {data && data.length === 0 && <EmptyState message="Chưa có vai trò nào" />}
        {data && data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Mã vai trò</Th>
                <Th>Tên</Th>
                <Th>Mô tả</Th>
                <Th>Hệ thống</Th>
                <Th>Vai trò cha</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {data.map((role) => (
                <tr key={role.id} className="hover:bg-slate-50">
                  <Td>
                    <Link
                      className="font-medium text-brand-600 hover:underline"
                      to={role.id}
                    >
                      {role.code}
                    </Link>
                  </Td>
                  <Td>{role.name}</Td>
                  <Td>{role.description ?? "—"}</Td>
                  <Td>
                    <Badge value={role.isSystem ? "HỆ THỐNG" : "TÙY CHỈNH"} />
                  </Td>
                  <Td>
                    {role.parentRoleId ? (
                      <div>
                        <p className="font-medium text-slate-900">{roleLabel(roleById.get(role.parentRoleId), role.parentRoleId)}</p>
                        <p className="mt-1 text-xs text-slate-500">ID {compactId(role.parentRoleId)}</p>
                      </div>
                    ) : (
                      "—"
                    )}
                  </Td>
                  <Td>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={deleteMutation.isPending}
                      onClick={() => handleDelete(role.id, role.name)}
                    >
                      Xóa
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// RoleCreatePage
// ---------------------------------------------------------------------------
export function RoleCreatePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const rolesQuery = useQuery({
    queryKey: queryKeys.roles.list,
    queryFn: listRoles,
    staleTime: 60_000
  });
  const [form, setForm] = useState({
    code: "",
    name: "",
    description: "",
    parentRoleId: ""
  });
  const roleById = useMemo(() => new Map((rolesQuery.data ?? []).map((role) => [role.id, role])), [rolesQuery.data]);
  const selectedParent = roleById.get(form.parentRoleId);

  const create = useMutation({
    mutationFn: () =>
      createRole({
        code: form.code,
        name: form.name,
        description: form.description || undefined,
        parentRoleId: form.parentRoleId || undefined
      }),
    onSuccess: (role) => {
      qc.invalidateQueries({ queryKey: queryKeys.roles.list });
      navigate(`../${role.id}`);
    }
  });

  return (
    <div>
      <Link
        to=".."
        className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader title="Thêm vai trò mới" />
      <Card className="max-w-2xl">
        <form
          className="space-y-4 p-4"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <FormField label="Mã vai trò" htmlFor="role-code">
            <Input
              id="role-code"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="VD: MANAGER, INSTRUCTOR_SENIOR"
              required
            />
          </FormField>
          <FormField label="Tên vai trò" htmlFor="role-name">
            <Input
              id="role-name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="VD: Quản lý, Giảng viên cấp cao"
              required
            />
          </FormField>
          <FormField label="Mô tả" htmlFor="role-desc">
            <Textarea
              id="role-desc"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Mô tả ngắn về vai trò này"
            />
          </FormField>
          <FormField label="Vai trò cha" htmlFor="role-parent">
            <Select
              id="role-parent"
              value={form.parentRoleId}
              onChange={(e) => setForm({ ...form, parentRoleId: e.target.value })}
            >
              <option value="">Không có vai trò cha</option>
              {(rolesQuery.data ?? []).map((role) => (
                <option key={role.id} value={role.id}>
                  {roleLabel(role)}
                </option>
              ))}
              {form.parentRoleId && !selectedParent && (
                <option value={form.parentRoleId}>Role {compactId(form.parentRoleId)}</option>
              )}
            </Select>
          </FormField>
          {create.isError && <ErrorState error={create.error} />}
          <div className="flex gap-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Đang tạo..." : "Tạo vai trò"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => navigate("..")}>
              Hủy
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// RoleDetailPage
// ---------------------------------------------------------------------------
export function RoleDetailPage() {
  const { roleId = "" } = useParams();
  const qc = useQueryClient();
  const [showAllPerms, setShowAllPerms] = useState(false);
  const [grantForm, setGrantForm] = useState({ permCode: "", effect: "ALLOW" });
  const [editForm, setEditForm] = useState<{
    name: string;
    description: string;
    parentRoleId: string;
  } | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.roles.detail(roleId),
    queryFn: () => getRole(roleId),
    enabled: Boolean(roleId)
  });

  const allPermsQuery = useQuery({
    queryKey: queryKeys.roles.permissions,
    queryFn: listPermissions,
    enabled: showAllPerms
  });
  const rolesQuery = useQuery({
    queryKey: queryKeys.roles.list,
    queryFn: listRoles,
    staleTime: 60_000
  });
  const roleById = useMemo(() => new Map((rolesQuery.data ?? []).map((role) => [role.id, role])), [rolesQuery.data]);
  const selectedEditParent = editForm?.parentRoleId ? roleById.get(editForm.parentRoleId) : undefined;

  const updateMutation = useMutation({
    mutationFn: (input: { name: string; description?: string; parentRoleId?: string }) =>
      updateRole(roleId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.roles.detail(roleId) });
      setEditForm(null);
    }
  });

  const grantMutation = useMutation({
    mutationFn: () => grantPermission(roleId, grantForm.permCode, grantForm.effect),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.roles.detail(roleId) });
      setGrantForm({ permCode: "", effect: "ALLOW" });
    }
  });

  const revokeMutation = useMutation({
    mutationFn: (permCode: string) => revokePermission(roleId, permCode),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.roles.detail(roleId) })
  });

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorState error={error} />;
  if (!data) return null;

  const isEditing = editForm !== null;

  function startEdit() {
    setEditForm({
      name: data!.name,
      description: data!.description ?? "",
      parentRoleId: data!.parentRoleId ?? ""
    });
  }

  function submitEdit(e: FormEvent) {
    e.preventDefault();
    if (!editForm) return;
    updateMutation.mutate({
      name: editForm.name,
      description: editForm.description || undefined,
      parentRoleId: editForm.parentRoleId || undefined
    });
  }

  return (
    <div className="space-y-6">
      <Link
        to=".."
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft size={16} /> Quay lại danh sách
      </Link>

      <PageHeader
        title={data.name}
        description={`Mã: ${data.code}`}
        actions={
          !isEditing ? (
            <Button variant="secondary" onClick={startEdit}>
              Chỉnh sửa
            </Button>
          ) : undefined
        }
      />

      {/* Info / Edit card */}
      <Card className="max-w-2xl">
        {!isEditing ? (
          <dl className="grid grid-cols-[140px_1fr] gap-y-3 p-4 text-sm">
            <dt className="text-slate-500">Mã vai trò</dt>
            <dd className="font-mono">{data.code}</dd>
            <dt className="text-slate-500">Tên</dt>
            <dd>{data.name}</dd>
            <dt className="text-slate-500">Mô tả</dt>
            <dd>{data.description ?? "—"}</dd>
            <dt className="text-slate-500">Loại</dt>
            <dd>
              <Badge value={data.isSystem ? "HỆ THỐNG" : "TÙY CHỈNH"} />
            </dd>
            <dt className="text-slate-500">Vai trò cha</dt>
            <dd>
              {data.parentRoleId ? (
                <span>
                  {roleLabel(roleById.get(data.parentRoleId), data.parentRoleId)}
                  <span className="ml-2 text-xs text-slate-500">ID {compactId(data.parentRoleId)}</span>
                </span>
              ) : (
                "—"
              )}
            </dd>
          </dl>
        ) : (
          <form className="space-y-4 p-4" onSubmit={submitEdit}>
            <FormField label="Tên vai trò" htmlFor="edit-name">
              <Input
                id="edit-name"
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                required
              />
            </FormField>
            <FormField label="Mô tả" htmlFor="edit-desc">
              <Textarea
                id="edit-desc"
                value={editForm.description}
                onChange={(e) =>
                  setEditForm({ ...editForm, description: e.target.value })
                }
              />
            </FormField>
            <FormField label="Vai trò cha" htmlFor="edit-parent">
              <Select
                id="edit-parent"
                value={editForm.parentRoleId}
                onChange={(e) =>
                  setEditForm({ ...editForm, parentRoleId: e.target.value })
                }
              >
                <option value="">Không có vai trò cha</option>
                {(rolesQuery.data ?? [])
                  .filter((role) => role.id !== roleId)
                  .map((role) => (
                    <option key={role.id} value={role.id}>
                      {roleLabel(role)}
                    </option>
                  ))}
                {editForm.parentRoleId && !selectedEditParent && (
                  <option value={editForm.parentRoleId}>Role {compactId(editForm.parentRoleId)}</option>
                )}
              </Select>
            </FormField>
            {updateMutation.isError && <ErrorState error={updateMutation.error} />}
            <div className="flex gap-2">
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => setEditForm(null)}
              >
                Hủy
              </Button>
            </div>
          </form>
        )}
      </Card>

      {/* Permissions section */}
      <Card>
        <CardHeader title="Quyền hạn được gán" />

        {(!data.permissions || data.permissions.length === 0) && (
          <EmptyState message="Chưa có quyền hạn nào được gán cho vai trò này" />
        )}

        {data.permissions && data.permissions.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Mã quyền</Th>
                <Th>Danh mục</Th>
                <Th>Mô tả</Th>
                <Th>Hiệu lực</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {data.permissions.map((perm) => (
                <tr key={perm.code} className="hover:bg-slate-50">
                  <Td>
                    <span className="font-mono text-sm">{perm.code}</span>
                  </Td>
                  <Td>{perm.category ?? "—"}</Td>
                  <Td>{perm.description ?? "—"}</Td>
                  <Td>
                    <Badge value={perm.effect} />
                  </Td>
                  <Td>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={revokeMutation.isPending}
                      onClick={() => revokeMutation.mutate(perm.code)}
                    >
                      Xóa
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}

        {/* Grant permission form */}
        <div className="border-t p-4">
          <p className="mb-3 text-sm font-medium text-slate-700">Thêm quyền</p>
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              grantMutation.mutate();
            }}
          >
            <FormField label="Mã quyền" htmlFor="grant-code">
              <Input
                id="grant-code"
                value={grantForm.permCode}
                onChange={(e) =>
                  setGrantForm({ ...grantForm, permCode: e.target.value })
                }
                placeholder="VD: course.read"
                required
              />
            </FormField>
            <FormField label="Hiệu lực" htmlFor="grant-effect">
              <Select
                id="grant-effect"
                value={grantForm.effect}
                onChange={(e) =>
                  setGrantForm({ ...grantForm, effect: e.target.value })
                }
              >
                <option value="ALLOW">ALLOW</option>
                <option value="DENY">DENY</option>
              </Select>
            </FormField>
            <Button type="submit" disabled={grantMutation.isPending}>
              {grantMutation.isPending ? "Đang thêm..." : "Thêm quyền"}
            </Button>
          </form>
          {grantMutation.isError && <ErrorState error={grantMutation.error} />}
        </div>
      </Card>

      {/* All system permissions (collapsible reference) */}
      <Card>
        <button
          type="button"
          className="flex w-full items-center justify-between p-4 text-left text-sm font-medium text-slate-700 hover:bg-slate-50"
          onClick={() => setShowAllPerms((v) => !v)}
        >
          <span>Tất cả quyền hệ thống</span>
          {showAllPerms ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showAllPerms && (
          <div>
            {allPermsQuery.isLoading && <Spinner />}
            {allPermsQuery.isError && <ErrorState error={allPermsQuery.error} />}
            {allPermsQuery.data && allPermsQuery.data.length === 0 && (
              <EmptyState message="Không có quyền nào trong hệ thống" />
            )}
            {allPermsQuery.data && allPermsQuery.data.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Mã quyền</Th>
                    <Th>Danh mục</Th>
                    <Th>Mô tả</Th>
                    <Th>Phạm vi</Th>
                  </tr>
                </thead>
                <tbody>
                  {allPermsQuery.data.map((perm) => (
                    <tr key={perm.code} className="hover:bg-slate-50">
                      <Td>
                        <span className="font-mono text-sm">{perm.code}</span>
                      </Td>
                      <Td>{perm.category}</Td>
                      <Td>{perm.description}</Td>
                      <Td>{perm.scopeType ?? "—"}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// UserAssignmentsPage
// ---------------------------------------------------------------------------
export function UserAssignmentsPage() {
  const qc = useQueryClient();
  const [userId, setUserId] = useState("");
  const [searchedUserId, setSearchedUserId] = useState("");
  const [assignForm, setAssignForm] = useState({
    roleId: "",
    scopeType: "PLATFORM",
    scopeId: "",
    grantedBy: ""
  });
  const usersQuery = useQuery({
    queryKey: queryKeys.users.list,
    queryFn: listUsers,
    staleTime: 60_000
  });
  const rolesQuery = useQuery({
    queryKey: queryKeys.roles.list,
    queryFn: listRoles,
    staleTime: 60_000
  });
  const coursesQuery = useQuery({
    queryKey: queryKeys.courses.list("roles-scope"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const departmentsQuery = useQuery({
    queryKey: queryKeys.organization.departments,
    queryFn: () => listDepartments(),
    retry: 1,
    staleTime: 60_000
  });
  const userRows = usersQuery.data ?? [];
  const roleRows = rolesQuery.data ?? [];
  const courseRows = coursesQuery.data?.length ? coursesQuery.data : fallbackCourses;
  const departmentRows = departmentsQuery.data ?? [];
  const userById = useMemo(() => new Map(userRows.map((user) => [String(user.id), user])), [userRows]);
  const roleById = useMemo(() => new Map(roleRows.map((role) => [role.id, role])), [roleRows]);
  const courseById = useMemo(() => new Map(courseRows.map((course) => [course.id, course])), [courseRows]);
  const departmentById = useMemo(
    () => new Map(departmentRows.map((department) => [department.id, department])),
    [departmentRows]
  );
  const selectedUser = userById.get(userId);
  const searchedUser = userById.get(searchedUserId);
  const selectedRole = roleById.get(assignForm.roleId);
  const selectedScopeCourse = courseById.get(assignForm.scopeId);
  const selectedScopeOrg = departmentById.get(assignForm.scopeId);

  const assignmentsQuery = useQuery({
    queryKey: queryKeys.roles.assignments(searchedUserId),
    queryFn: () => getUserAssignments(searchedUserId),
    enabled: Boolean(searchedUserId)
  });

  const revokeMutation = useMutation({
    mutationFn: (assignmentId: number) =>
      revokeAssignment(searchedUserId, assignmentId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.roles.assignments(searchedUserId) })
  });

  const assignMutation = useMutation({
    mutationFn: () =>
      assignRole(searchedUserId, {
        roleId: assignForm.roleId,
        scopeType: assignForm.scopeType,
        scopeId: assignForm.scopeId || undefined,
        grantedBy: assignForm.grantedBy || undefined
      }),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.roles.assignments(searchedUserId)
      });
      setAssignForm({ roleId: "", scopeType: "PLATFORM", scopeId: "", grantedBy: "" });
    }
  });

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    setSearchedUserId(userId.trim());
  }

  function scopeLabel(scopeType: string, scopeId?: string) {
    if (!scopeId) return "Toàn hệ thống";
    if (scopeType === "COURSE") return courseLabel(courseById.get(scopeId), scopeId);
    if (scopeType === "DEPARTMENT" || scopeType === "ORG") return orgLabel(departmentById.get(scopeId), scopeId);
    return `Scope ${compactId(scopeId)}`;
  }

  return (
    <div className="space-y-6">
      <Link
        to=".."
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft size={16} /> Quay lại danh sách vai trò
      </Link>

      <PageHeader
        title="Phân công vai trò cho người dùng"
        description="Tra cứu và quản lý phân công vai trò theo từng người dùng"
      />

      {/* User search */}
      <Card className="max-w-3xl">
        <form className="grid gap-3 p-4 md:grid-cols-[1fr_auto]" onSubmit={handleSearch}>
          <FormField label="Người dùng" htmlFor="user-id-input">
            <Select
              id="user-id-input"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              required
            >
              <option value="">Chọn người dùng</option>
              {userRows.map((user) => (
                <option key={user.id} value={user.id}>
                  {userLabel(user)}
                </option>
              ))}
              {userId && !selectedUser && <option value={userId}>User {compactId(userId)}</option>}
            </Select>
          </FormField>
          <div className="flex items-end">
            <Button type="submit">Tra cứu</Button>
          </div>
        </form>
      </Card>

      {/* Assignments table */}
      {searchedUserId && (
        <Card>
          <CardHeader
            title="Phân công của người dùng"
            subtitle={userLabel(searchedUser, searchedUserId)}
          />
          {assignmentsQuery.isLoading && <Spinner />}
          {assignmentsQuery.isError && <ErrorState error={assignmentsQuery.error} />}
          {assignmentsQuery.data && assignmentsQuery.data.length === 0 && (
            <EmptyState message="Người dùng này chưa được phân công vai trò nào" />
          )}
          {assignmentsQuery.data && assignmentsQuery.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Mã vai trò</Th>
                  <Th>Tên vai trò</Th>
                  <Th>Phạm vi</Th>
                  <Th>Đối tượng</Th>
                  <Th>Cấp bởi</Th>
                  <Th></Th>
                </tr>
              </thead>
              <tbody>
                {assignmentsQuery.data.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50">
                    <Td>
                      <span className="font-mono text-sm">{a.roleCode}</span>
                    </Td>
                    <Td>{a.roleName}</Td>
                    <Td>
                      <Badge value={a.scopeType} />
                    </Td>
                    <Td>
                      <div className="font-medium text-slate-900">{scopeLabel(a.scopeType, a.scopeId)}</div>
                      {a.scopeId && <div className="mt-1 text-xs text-slate-500">ID {compactId(a.scopeId)}</div>}
                    </Td>
                    <Td>{a.grantedBy ? userLabel(userById.get(a.grantedBy), a.grantedBy) : "—"}</Td>
                    <Td>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={revokeMutation.isPending}
                        onClick={() => revokeMutation.mutate(a.id)}
                      >
                        Thu hồi
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}

          {/* Assign role form */}
          <div className="border-t p-4">
            <p className="mb-3 text-sm font-medium text-slate-700">
              Phân công vai trò mới
            </p>
            <form
              className="grid gap-3 lg:grid-cols-2"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                assignMutation.mutate();
              }}
            >
              <FormField label="Vai trò" htmlFor="assign-role">
                <Select
                  id="assign-role"
                  value={assignForm.roleId}
                  onChange={(e) =>
                    setAssignForm({ ...assignForm, roleId: e.target.value })
                  }
                  required
                >
                  <option value="">Chọn vai trò</option>
                  {roleRows.map((role) => (
                    <option key={role.id} value={role.id}>
                      {roleLabel(role)}
                    </option>
                  ))}
                  {assignForm.roleId && !selectedRole && (
                    <option value={assignForm.roleId}>Role {compactId(assignForm.roleId)}</option>
                  )}
                </Select>
              </FormField>
              <FormField label="Loại phạm vi" htmlFor="assign-scope-type">
                <Select
                  id="assign-scope-type"
                  value={assignForm.scopeType}
                  onChange={(e) =>
                    setAssignForm({ ...assignForm, scopeType: e.target.value, scopeId: "" })
                  }
                >
                  <option value="PLATFORM">PLATFORM</option>
                  <option value="ORG">ORG</option>
                  <option value="COURSE">COURSE</option>
                  <option value="DEPARTMENT">DEPARTMENT</option>
                </Select>
              </FormField>
              {assignForm.scopeType === "COURSE" && (
                <FormField label="Khóa học" htmlFor="assign-scope-course">
                  <Select
                    id="assign-scope-course"
                    value={assignForm.scopeId}
                    onChange={(e) => setAssignForm({ ...assignForm, scopeId: e.target.value })}
                  >
                    <option value="">Tất cả khóa học</option>
                    {courseRows.map((course) => (
                      <option key={course.id} value={course.id}>
                        {courseLabel(course)}
                      </option>
                    ))}
                    {assignForm.scopeId && !selectedScopeCourse && (
                      <option value={assignForm.scopeId}>Course {compactId(assignForm.scopeId)}</option>
                    )}
                  </Select>
                </FormField>
              )}
              {(assignForm.scopeType === "ORG" || assignForm.scopeType === "DEPARTMENT") && (
                <FormField label="Tổ chức/phòng ban" htmlFor="assign-scope-org">
                  <Select
                    id="assign-scope-org"
                    value={assignForm.scopeId}
                    onChange={(e) => setAssignForm({ ...assignForm, scopeId: e.target.value })}
                  >
                    <option value="">Toàn bộ</option>
                    {departmentRows.map((department) => (
                      <option key={department.id} value={department.id}>
                        {orgLabel(department)}
                      </option>
                    ))}
                    {assignForm.scopeId && !selectedScopeOrg && (
                      <option value={assignForm.scopeId}>Org {compactId(assignForm.scopeId)}</option>
                    )}
                  </Select>
                </FormField>
              )}
              <FormField label="Cấp bởi" htmlFor="assign-granted-by">
                <Select
                  id="assign-granted-by"
                  value={assignForm.grantedBy}
                  onChange={(e) =>
                    setAssignForm({ ...assignForm, grantedBy: e.target.value })
                  }
                >
                  <option value="">Không ghi người cấp</option>
                  {userRows.map((user) => (
                    <option key={user.id} value={user.id}>
                      {userLabel(user)}
                    </option>
                  ))}
                  {assignForm.grantedBy && !userById.has(assignForm.grantedBy) && (
                    <option value={assignForm.grantedBy}>User {compactId(assignForm.grantedBy)}</option>
                  )}
                </Select>
              </FormField>
              <div className="lg:col-span-2">
                <Button type="submit" disabled={assignMutation.isPending || !assignForm.roleId}>
                  {assignMutation.isPending ? "Đang phân công..." : "Phân công"}
                </Button>
              </div>
            </form>
            {assignMutation.isError && <ErrorState error={assignMutation.error} />}
          </div>
        </Card>
      )}
    </div>
  );
}
