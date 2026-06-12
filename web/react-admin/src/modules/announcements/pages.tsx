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
  Textarea,
  Th
} from "@/shared/ui";
import {
  createAnnouncement,
  getAnnouncement,
  listAnnouncements,
  publishAnnouncement
} from "./api";

export function AnnouncementListPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.announcements.list,
    queryFn: listAnnouncements
  });

  return (
    <div>
      <PageHeader
        title="Thông báo"
        description="Soạn, lên lịch và xuất bản thông báo"
        actions={
          <Link to="new">
            <Button>
              <Plus size={16} /> Tạo thông báo
            </Button>
          </Link>
        }
      />
      <Card>
        <CardHeader title="Danh sách thông báo" />
        {isLoading && <Spinner />}
        {isError && <ErrorState error={error} />}
        {data && data.length === 0 && <EmptyState message="Chưa có thông báo" />}
        {data && data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Tiêu đề</Th>
                <Th>Đối tượng</Th>
                <Th>Trạng thái</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50">
                  <Td>
                    <Link className="font-medium text-brand-600 hover:underline" to={a.id}>
                      {a.title}
                    </Link>
                  </Td>
                  <Td>{a.audience ?? "—"}</Td>
                  <Td>
                    <Badge value={a.status} />
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

export function AnnouncementDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.announcements.detail(id),
    queryFn: () => getAnnouncement(id),
    enabled: Boolean(id)
  });
  const publish = useMutation({
    mutationFn: () => publishAnnouncement(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["announcements"] })
  });

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorState error={error} />;
  if (!data) return null;

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader
        title={data.title}
        actions={
          <Button disabled={publish.isPending || data.status === "PUBLISHED"} onClick={() => publish.mutate()}>
            {publish.isPending ? "Đang xuất bản" : "Xuất bản"}
          </Button>
        }
      />
      <Card>
        <dl className="grid grid-cols-[140px_1fr] gap-y-3 p-4 text-sm">
          <dt className="text-slate-500">Đối tượng</dt>
          <dd>{data.audience ?? "—"}</dd>
          <dt className="text-slate-500">Trạng thái</dt>
          <dd>
            <Badge value={data.status} />
          </dd>
          <dt className="text-slate-500">Nội dung</dt>
          <dd className="whitespace-pre-wrap">{data.body ?? "—"}</dd>
        </dl>
      </Card>
    </div>
  );
}

export function AnnouncementCreatePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState({ title: "", body: "", audience: "ALL" });
  const create = useMutation({
    mutationFn: () => createAnnouncement(form),
    onSuccess: (a) => {
      qc.invalidateQueries({ queryKey: ["announcements"] });
      navigate(`../${a.id}`);
    }
  });

  return (
    <div>
      <PageHeader title="Tạo thông báo" />
      <Card className="max-w-2xl">
        <form
          className="space-y-4 p-4"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <FormField label="Tiêu đề" htmlFor="an-title">
            <Input id="an-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          </FormField>
          <FormField label="Đối tượng" htmlFor="an-aud">
            <Select id="an-aud" value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })}>
              <option value="ALL">Tất cả</option>
              <option value="STUDENTS">Học viên</option>
              <option value="INSTRUCTORS">Giảng viên</option>
            </Select>
          </FormField>
          <FormField label="Nội dung" htmlFor="an-body">
            <Textarea id="an-body" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required />
          </FormField>
          {create.isError && <ErrorState error={create.error} />}
          <div className="flex gap-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Đang tạo" : "Tạo"}
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
