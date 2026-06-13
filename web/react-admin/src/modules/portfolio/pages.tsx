import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import {
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
import { adminUserLabel, useLearnerUsers } from "../identity/useLearnerUsers";
import { addEvidence, listEvidence } from "./api";

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

export function PortfolioPage() {
  const qc = useQueryClient();
  const { learnerUsers, roleQueriesLoading, userById, usersQuery } = useLearnerUsers();
  const [studentId, setStudentId] = useState("");
  const [submitted, setSubmitted] = useState("");
  const evidence = useQuery({
    queryKey: queryKeys.portfolio.evidence(submitted),
    queryFn: () => listEvidence(submitted),
    enabled: Boolean(submitted)
  });
  const [form, setForm] = useState({ title: "", type: "PROJECT", url: "" });
  const add = useMutation({
    mutationFn: () => addEvidence(submitted, form),
    onSuccess: () => {
      setForm({ title: "", type: "PROJECT", url: "" });
      qc.invalidateQueries({ queryKey: queryKeys.portfolio.evidence(submitted) });
    }
  });
  const selectedLearner = userById.get(studentId);
  const submittedLearner = userById.get(submitted);
  const learnerRows = useMemo(() => {
    if (!selectedLearner) return learnerUsers;
    return learnerUsers.some((user) => String(user.id) === String(selectedLearner.id))
      ? learnerUsers
      : [selectedLearner, ...learnerUsers];
  }, [learnerUsers, selectedLearner]);
  const learnerHint =
    usersQuery.isLoading || roleQueriesLoading
      ? "Đang tải danh sách learner..."
      : usersQuery.isError
        ? "Không tải được danh sách learner."
        : `${learnerRows.length} learner khả dụng`;

  return (
    <div>
      <PageHeader title="Hồ sơ năng lực" description="Minh chứng năng lực theo học viên, dự án và chứng chỉ." />
      <Card className="mb-4">
        <CardHeader
          title="Chọn học viên"
          subtitle={submittedLearner ? adminUserLabel(submittedLearner) : submitted ? `Học viên ${compactId(submitted)}` : "Chọn learner để xem và bổ sung minh chứng."}
        />
        <form
          className="grid gap-3 p-4 lg:grid-cols-[1fr_auto]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setSubmitted(studentId.trim());
          }}
        >
          <FormField label="Học viên" htmlFor="pf-student" hint={learnerHint}>
            <Select
              id="pf-student"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              disabled={usersQuery.isLoading && learnerRows.length === 0}
              required
            >
              <option value="">Chọn học viên</option>
              {learnerRows.map((user) => (
                <option key={user.id} value={String(user.id)}>
                  {adminUserLabel(user)}
                </option>
              ))}
              {studentId && !selectedLearner && (
                <option value={studentId}>Học viên {compactId(studentId)}</option>
              )}
            </Select>
          </FormField>
          <div className="flex items-end">
            <Button type="submit" disabled={!studentId}>Xem hồ sơ</Button>
          </div>
        </form>
      </Card>

      {submitted && (
        <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
          <Card>
            <CardHeader title="Minh chứng" />
            {evidence.isLoading && <Spinner />}
            {evidence.isError && <ErrorState error={evidence.error} />}
            {evidence.data && evidence.data.length === 0 && <EmptyState message="Chưa có minh chứng" />}
            {evidence.data && evidence.data.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Tiêu đề</Th>
                    <Th>Loại</Th>
                    <Th>Liên kết</Th>
                  </tr>
                </thead>
                <tbody>
                  {evidence.data.map((ev) => (
                    <tr key={ev.id}>
                      <Td>{ev.title}</Td>
                      <Td>{ev.type ?? "—"}</Td>
                      <Td>
                        {ev.url ? (
                          <a className="text-brand-600 hover:underline" href={ev.url} target="_blank" rel="noreferrer">
                            Mở
                          </a>
                        ) : (
                          "—"
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <CardHeader title="Thêm minh chứng" subtitle={submittedLearner ? adminUserLabel(submittedLearner) : `Học viên ${compactId(submitted)}`} />
            <form
              className="space-y-4 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                add.mutate();
              }}
            >
              <FormField label="Tiêu đề" htmlFor="pf-title">
                <Input id="pf-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
              </FormField>
              <FormField label="Loại" htmlFor="pf-type">
                <Select id="pf-type" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  <option value="PROJECT">PROJECT</option>
                  <option value="CERTIFICATE">CERTIFICATE</option>
                  <option value="ASSIGNMENT">ASSIGNMENT</option>
                </Select>
              </FormField>
              <FormField label="URL" htmlFor="pf-url">
                <Input id="pf-url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
              </FormField>
              {add.isError && <ErrorState error={add.error} />}
              <Button type="submit" disabled={add.isPending || !submitted}>
                {add.isPending ? "Đang lưu" : "Thêm"}
              </Button>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
