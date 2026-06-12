import { FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus } from "lucide-react";
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
  Th
} from "@/shared/ui";
import { createUser, getUser, listUsers, type CreateUserInput } from "./api";

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
                  <Td>{u.role}</Td>
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
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.users.detail(id),
    queryFn: () => getUser(id),
    enabled: Boolean(id)
  });

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorState error={error} />;
  if (!data) return null;

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader title={data.fullName} description={data.email} />
      <Card className="max-w-lg">
        <dl className="grid grid-cols-[120px_1fr] gap-y-3 p-4 text-sm">
          <dt className="text-slate-500">ID</dt>
          <dd>{data.id}</dd>
          <dt className="text-slate-500">Vai trò</dt>
          <dd>{data.role}</dd>
          <dt className="text-slate-500">Trạng thái</dt>
          <dd>
            <Badge value={data.status} />
          </dd>
        </dl>
      </Card>
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
