import { FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Download, Plus, ShieldAlert, UserX } from "lucide-react";
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
import {
  createUser,
  deactivateUser,
  downloadUserPrivacyExport,
  getUser,
  listUsers,
  type CreateUserInput
} from "./api";

export function UserListPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.users.list,
    queryFn: listUsers
  });

  return (
    <div>
      <PageHeader
        title="Người dùng"
        description="Quản lý tài khoản, vai trò và trạng thái"
        actions={
          <Link to="new">
            <Button>
              <Plus size={16} /> Thêm người dùng
            </Button>
          </Link>
        }
      />
      <Card>
        <CardHeader title="Danh sách người dùng" />
        {isLoading && <Spinner />}
        {isError && <ErrorState error={error} />}
        {data && data.length === 0 && <EmptyState message="Chưa có người dùng" />}
        {data && data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Họ tên</Th>
                <Th>Email</Th>
                <Th>Vai trò</Th>
                <Th>Trạng thái</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <Td>
                    <Link className="font-medium text-brand-600 hover:underline" to={String(u.id)}>
                      {u.fullName}
                    </Link>
                  </Td>
                  <Td>{u.email}</Td>
                  <Td>{u.role ?? "—"}</Td>
                  <Td>
                    <Badge value={u.status} />
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

export function UserDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const [deactivationReason, setDeactivationReason] = useState("");
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.users.detail(id),
    queryFn: () => getUser(id),
    enabled: Boolean(id)
  });
  const privacyExport = useMutation({
    mutationFn: () => downloadUserPrivacyExport(id)
  });
  const deactivate = useMutation({
    mutationFn: () => deactivateUser(id, deactivationReason.trim()),
    onSuccess: (user) => {
      qc.setQueryData(queryKeys.users.detail(id), user);
      qc.invalidateQueries({ queryKey: queryKeys.users.all });
      setDeactivationReason("");
    }
  });

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorState error={error} />;
  if (!data) return null;
  const isDeactivated = data.status === "DEACTIVATED";

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader
        title={data.fullName}
        description={data.email}
        actions={
          <Button
            variant="secondary"
            disabled={privacyExport.isPending}
            onClick={() => privacyExport.mutate()}
          >
            <Download size={16} />
            {privacyExport.isPending ? "Đang xuất" : "Xuất dữ liệu"}
          </Button>
        }
      />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,0.75fr)]">
        <Card>
          <CardHeader title="Hồ sơ tài khoản" subtitle="Thông tin định danh và trạng thái vận hành." />
          <dl className="grid grid-cols-[140px_1fr] gap-y-3 p-4 text-sm">
            <dt className="text-slate-500">ID</dt>
            <dd>{data.id}</dd>
            <dt className="text-slate-500">Email</dt>
            <dd>{data.email}</dd>
            <dt className="text-slate-500">Vai trò</dt>
            <dd>{data.role ?? "—"}</dd>
            <dt className="text-slate-500">Trạng thái</dt>
            <dd>
              <Badge value={data.status} />
            </dd>
          </dl>
          {privacyExport.isError && <ErrorState error={privacyExport.error} />}
          {privacyExport.isSuccess && (
            <div className="mx-4 mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">
              Đã tải file export JSON cho user #{data.id}.
            </div>
          )}
        </Card>

        <Card>
          <CardHeader
            title="Privacy & lifecycle"
            subtitle="Deactivation khóa đăng nhập, thu hồi phiên và role grants đang còn hiệu lực."
            actions={<ShieldAlert size={18} className="text-amber-600" />}
          />
          <form
            className="space-y-4 p-4"
            onSubmit={(event: FormEvent<HTMLFormElement>) => {
              event.preventDefault();
              deactivate.mutate();
            }}
          >
            <FormField
              label="Lý do deactivation"
              htmlFor="deactivate-reason"
              hint="Bắt buộc để giữ audit trail cho yêu cầu privacy/compliance."
            >
              <Textarea
                id="deactivate-reason"
                value={deactivationReason}
                maxLength={255}
                disabled={isDeactivated}
                onChange={(event) => setDeactivationReason(event.target.value)}
                placeholder="Ví dụ: User requested account deactivation under retention policy."
                required
              />
            </FormField>
            {deactivate.isError && <ErrorState error={deactivate.error} />}
            {deactivate.isSuccess && (
              <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">
                Đã deactivate và revoke phiên/role grants của tài khoản.
              </div>
            )}
            <Button
              type="submit"
              variant="danger"
              disabled={isDeactivated || deactivate.isPending || !deactivationReason.trim()}
            >
              <UserX size={16} />
              {isDeactivated ? "Đã deactivate" : deactivate.isPending ? "Đang deactivate" : "Deactivate user"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}

export function UserCreatePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const create = useMutation({
    mutationFn: (input: CreateUserInput) => createUser(input),
    onSuccess: (user) => {
      qc.invalidateQueries({ queryKey: queryKeys.users.all });
      navigate(`../${user.id}`);
    }
  });
  const [form, setForm] = useState<CreateUserInput>({
    email: "",
    fullName: "",
    role: "STUDENT",
    password: ""
  });

  function update<K extends keyof CreateUserInput>(k: K, v: CreateUserInput[K]) {
    setForm((p) => ({ ...p, [k]: v }));
  }
  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    create.mutate(form);
  }

  return (
    <div>
      <PageHeader title="Thêm người dùng" />
      <Card className="max-w-lg">
        <form className="space-y-4 p-4" onSubmit={submit}>
          <FormField label="Họ tên" htmlFor="fullName">
            <Input id="fullName" value={form.fullName} onChange={(e) => update("fullName", e.target.value)} required />
          </FormField>
          <FormField label="Email" htmlFor="email">
            <Input id="email" type="email" value={form.email} onChange={(e) => update("email", e.target.value)} required />
          </FormField>
          <FormField label="Mật khẩu" htmlFor="password">
            <Input id="password" type="password" value={form.password} onChange={(e) => update("password", e.target.value)} required />
          </FormField>
          <FormField label="Vai trò" htmlFor="role">
            <Select id="role" value={form.role} onChange={(e) => update("role", e.target.value)}>
              <option value="STUDENT">STUDENT</option>
              <option value="INSTRUCTOR">INSTRUCTOR</option>
              <option value="ADMIN">ADMIN</option>
            </Select>
          </FormField>
          {create.isError && <ErrorState error={create.error} />}
          <div className="flex gap-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Đang lưu" : "Tạo"}
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
