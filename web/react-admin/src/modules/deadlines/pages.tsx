import { FormEvent, useState } from "react";
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
import {
  createPolicy,
  createReminder,
  dispatchReminder,
  listDueReminders,
  listPolicies
} from "./api";

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function policyLabel(policy?: { id: string; name: string }, fallbackId?: string) {
  if (policy) return policy.name;
  return fallbackId ? `Policy ${compactId(fallbackId)}` : "Chọn chính sách";
}

export function DeadlinesPage() {
  const qc = useQueryClient();
  const policies = useQuery({ queryKey: queryKeys.deadlines.policies, queryFn: listPolicies });
  const due = useQuery({ queryKey: queryKeys.deadlines.due, queryFn: listDueReminders });
  const policyById = new Map((policies.data ?? []).map((policy) => [policy.id, policy]));

  const [policyForm, setPolicyForm] = useState({ name: "", graceHours: 24, penaltyPercent: 10 });
  const createP = useMutation({
    mutationFn: () => createPolicy(policyForm),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.deadlines.policies })
  });

  const [reminderForm, setReminderForm] = useState({ policyId: "", dueAt: "" });
  const createR = useMutation({
    mutationFn: () => createReminder(reminderForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.deadlines.due });
      setReminderForm({ policyId: "", dueAt: "" });
    }
  });

  const dispatch = useMutation({
    mutationFn: (id: string) => dispatchReminder(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.deadlines.due })
  });

  return (
    <div>
      <PageHeader title="Hạn chót" description="Chính sách hạn nộp và nhắc nhở" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Chính sách" />
          {policies.isLoading && <Spinner />}
          {policies.isError && <ErrorState error={policies.error} />}
          {policies.data && policies.data.length === 0 && <EmptyState message="Chưa có chính sách" />}
          {policies.data && policies.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Tên</Th>
                  <Th>Gia hạn (giờ)</Th>
                  <Th>Phạt (%)</Th>
                </tr>
              </thead>
              <tbody>
                {policies.data.map((p) => (
                  <tr key={p.id}>
                    <Td>{p.name}</Td>
                    <Td>{p.graceHours ?? "—"}</Td>
                    <Td>{p.penaltyPercent ?? "—"}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader title="Nhắc nhở đến hạn" />
          {due.isLoading && <Spinner />}
          {due.isError && <ErrorState error={due.error} />}
          {due.data && due.data.length === 0 && <EmptyState message="Không có nhắc nhở đến hạn" />}
          {due.data && due.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Đến hạn</Th>
                  <Th>Chính sách</Th>
                  <Th>Trạng thái</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {due.data.map((r) => (
                  <tr key={r.id}>
                    <Td>{r.dueAt ?? "—"}</Td>
                    <Td>
                      <div className="font-semibold text-slate-900">{policyLabel(policyById.get(r.policyId ?? ""), r.policyId)}</div>
                      {r.policyId && <div className="mt-1 text-xs text-slate-500">ID {compactId(r.policyId)}</div>}
                    </Td>
                    <Td>
                      <Badge value={r.status} />
                    </Td>
                    <Td>
                      <Button size="sm" variant="secondary" disabled={dispatch.isPending} onClick={() => dispatch.mutate(r.id)}>
                        Gửi
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader title="Tạo chính sách" />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createP.mutate();
            }}
          >
            <FormField label="Tên" htmlFor="dp-name">
              <Input id="dp-name" value={policyForm.name} onChange={(e) => setPolicyForm({ ...policyForm, name: e.target.value })} required />
            </FormField>
            <FormField label="Gia hạn (giờ)" htmlFor="dp-grace">
              <Input id="dp-grace" type="number" value={policyForm.graceHours} onChange={(e) => setPolicyForm({ ...policyForm, graceHours: Number(e.target.value) })} />
            </FormField>
            <FormField label="Phạt (%)" htmlFor="dp-pen">
              <Input id="dp-pen" type="number" value={policyForm.penaltyPercent} onChange={(e) => setPolicyForm({ ...policyForm, penaltyPercent: Number(e.target.value) })} />
            </FormField>
            {createP.isError && <ErrorState error={createP.error} />}
            <Button type="submit" disabled={createP.isPending}>
              {createP.isPending ? "Đang lưu" : "Tạo chính sách"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title="Tạo nhắc nhở" />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createR.mutate();
            }}
          >
            <FormField label="Chính sách" htmlFor="dr-policy">
              <Select
                id="dr-policy"
                value={reminderForm.policyId}
                onChange={(e) => setReminderForm({ ...reminderForm, policyId: e.target.value })}
                required
              >
                <option value="">Chọn chính sách</option>
                {(policies.data ?? []).map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policyLabel(policy)}
                  </option>
                ))}
                {reminderForm.policyId && !policyById.has(reminderForm.policyId) && (
                  <option value={reminderForm.policyId}>Policy {compactId(reminderForm.policyId)}</option>
                )}
              </Select>
            </FormField>
            <FormField label="Đến hạn (ISO)" htmlFor="dr-due">
              <Input id="dr-due" placeholder="2026-07-01T00:00:00Z" value={reminderForm.dueAt} onChange={(e) => setReminderForm({ ...reminderForm, dueAt: e.target.value })} required />
            </FormField>
            {createR.isError && <ErrorState error={createR.error} />}
            <Button type="submit" disabled={createR.isPending}>
              {createR.isPending ? "Đang lưu" : "Tạo nhắc nhở"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
