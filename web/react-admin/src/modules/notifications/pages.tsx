import { FormEvent, useMemo, useState } from "react";
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
import { listUsers, type AdminUser } from "@/modules/identity/api";
import {
  createNotification,
  getPreferences,
  listNotifications,
  markRead,
  savePreferences
} from "./api";

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function userLabel(user?: Pick<AdminUser, "fullName" | "email">, fallbackId?: string) {
  if (user) return `${user.fullName || user.email} · ${user.email}`;
  return fallbackId ? `User ${compactId(fallbackId)}` : "Tất cả người dùng";
}

function notificationRead(notification: { read?: boolean; readAt?: string }) {
  return Boolean(notification.readAt ?? notification.read);
}

function deliveryStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    PENDING: "Chờ gửi",
    DISPATCHING: "Đang gửi",
    DELIVERED: "Đã gửi",
    FAILED: "Lỗi gửi"
  };
  return labels[status ?? ""] ?? status ?? "Chưa rõ";
}

export function NotificationsPage() {
  const qc = useQueryClient();
  const [userId, setUserId] = useState("");
  const users = useQuery({
    queryKey: queryKeys.users.list,
    queryFn: listUsers,
    staleTime: 60_000
  });
  const userRows = users.data ?? [];
  const userById = useMemo(() => new Map(userRows.map((user) => [String(user.id), user])), [userRows]);
  const selectedFilterUser = userById.get(userId);
  const list = useQuery({
    queryKey: queryKeys.notifications.list(userId),
    queryFn: () => listNotifications(userId),
    enabled: Boolean(userId)
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["notifications"] });

  const read = useMutation({ mutationFn: (id: string) => markRead(id), onSuccess: invalidate });
  const [form, setForm] = useState({ userId: "", notificationType: "SYSTEM", title: "", body: "" });
  const selectedFormUser = userById.get(form.userId);
  const create = useMutation({
    mutationFn: () => createNotification(form),
    onSuccess: () => {
      invalidate();
      setForm({ userId: form.userId, notificationType: form.notificationType, title: "", body: "" });
    }
  });
  const [prefs, setPrefs] = useState({ userId: "", channel: "EMAIL", enabled: true });
  const selectedPrefsUser = userById.get(prefs.userId);
  const prefsQuery = useQuery({
    queryKey: queryKeys.notifications.preferences(prefs.userId),
    queryFn: () => getPreferences(prefs.userId),
    enabled: Boolean(prefs.userId)
  });
  const save = useMutation({
    mutationFn: () => savePreferences(prefs),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.notifications.preferences(prefs.userId) })
  });

  return (
    <div>
      <PageHeader title="Thông báo hệ thống" description="Hộp thư và tùy chọn nhận thông báo" />
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader
            title="Danh sách thông báo"
            subtitle={userLabel(selectedFilterUser, userId)}
            actions={
              <Select value={userId} onChange={(e) => setUserId(e.target.value)} className="w-64" aria-label="Lọc người nhận">
                <option value="">Tất cả người dùng</option>
                {userRows.map((user) => (
                  <option key={user.id} value={user.id}>
                    {userLabel(user)}
                  </option>
                ))}
                {userId && !selectedFilterUser && <option value={userId}>User {compactId(userId)}</option>}
              </Select>
            }
          />
          {!userId && <EmptyState message="Chọn một người dùng để xem inbox và trạng thái delivery." />}
          {userId && list.isLoading && <Spinner />}
          {list.isError && <ErrorState error={list.error} />}
          {list.data && list.data.length === 0 && <EmptyState message="Không có thông báo" />}
          {list.data && list.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Tiêu đề</Th>
                  <Th>Người nhận</Th>
                  <Th>Trạng thái</Th>
                  <Th>Delivery</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {list.data.map((n) => (
                  <tr key={n.id}>
                    <Td>{n.title}</Td>
                    <Td>
                      <div className="font-medium text-slate-900">{userLabel(userById.get(n.userId ?? ""), n.userId)}</div>
                      {n.userId && <div className="mt-1 text-xs text-slate-500">ID {compactId(n.userId)}</div>}
                    </Td>
                    <Td>
                      <Badge value={notificationRead(n) ? "READ" : "UNREAD"} />
                    </Td>
                    <Td>
                      <div className="space-y-1">
                        <Badge value={n.deliveryStatus} label={deliveryStatusLabel(n.deliveryStatus)} />
                        {n.deliveredAt && (
                          <div className="text-xs text-slate-500">
                            {new Date(n.deliveredAt).toLocaleString("vi-VN")}
                          </div>
                        )}
                        {n.deliveryError && (
                          <div className="max-w-xs text-xs text-red-600">{n.deliveryError}</div>
                        )}
                      </div>
                    </Td>
                    <Td>
                      {!notificationRead(n) && (
                        <Button size="sm" variant="secondary" disabled={read.isPending} onClick={() => read.mutate(n.id)}>
                          Đánh dấu đã đọc
                        </Button>
                      )}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Gửi thông báo" />
            <form
              className="space-y-4 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                create.mutate();
              }}
            >
              <FormField label="Người nhận" htmlFor="n-user">
                <Select id="n-user" value={form.userId} onChange={(e) => setForm({ ...form, userId: e.target.value })} required>
                  <option value="">Chọn người nhận</option>
                  {userRows.map((user) => (
                    <option key={user.id} value={user.id}>
                      {userLabel(user)}
                    </option>
                  ))}
                  {form.userId && !selectedFormUser && <option value={form.userId}>User {compactId(form.userId)}</option>}
                </Select>
              </FormField>
              <FormField label="Loại thông báo" htmlFor="n-type">
                <Select
                  id="n-type"
                  value={form.notificationType}
                  onChange={(e) => setForm({ ...form, notificationType: e.target.value })}
                >
                  <option value="SYSTEM">SYSTEM</option>
                  <option value="ANNOUNCEMENT">ANNOUNCEMENT</option>
                  <option value="DEADLINE">DEADLINE</option>
                  <option value="GRADE">GRADE</option>
                  <option value="CERTIFICATE">CERTIFICATE</option>
                </Select>
              </FormField>
              <FormField label="Tiêu đề" htmlFor="n-title">
                <Input id="n-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
              </FormField>
              <FormField label="Nội dung" htmlFor="n-body">
                <Input id="n-body" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required />
              </FormField>
              {create.isError && <ErrorState error={create.error} />}
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? "Đang gửi" : "Gửi"}
              </Button>
            </form>
          </Card>

          <Card>
            <CardHeader title="Tùy chọn nhận" subtitle="ADMIN có thể kiểm tra và cập nhật từng channel cho người dùng." />
            <form
              className="space-y-3 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                save.mutate();
              }}
            >
              <FormField label="Người dùng" htmlFor="p-user">
                <Select id="p-user" value={prefs.userId} onChange={(e) => setPrefs({ ...prefs, userId: e.target.value })} required>
                  <option value="">Chọn người dùng</option>
                  {userRows.map((user) => (
                    <option key={user.id} value={user.id}>
                      {userLabel(user)}
                    </option>
                  ))}
                  {prefs.userId && !selectedPrefsUser && <option value={prefs.userId}>User {compactId(prefs.userId)}</option>}
                </Select>
              </FormField>
              <FormField label="Channel" htmlFor="p-channel">
                <Select id="p-channel" value={prefs.channel} onChange={(e) => setPrefs({ ...prefs, channel: e.target.value })}>
                  <option value="IN_APP">IN_APP</option>
                  <option value="EMAIL">EMAIL</option>
                  <option value="PUSH">PUSH</option>
                  <option value="ANNOUNCEMENT">ANNOUNCEMENT</option>
                  <option value="DEADLINE">DEADLINE</option>
                  <option value="GRADE">GRADE</option>
                </Select>
              </FormField>
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input type="checkbox" checked={prefs.enabled} onChange={(e) => setPrefs({ ...prefs, enabled: e.target.checked })} />
                Bật channel này
              </label>
              {prefsQuery.isLoading && <Spinner label="Đang tải preference" />}
              {prefsQuery.isError && <ErrorState error={prefsQuery.error} />}
              {prefsQuery.data && prefsQuery.data.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                  <p className="mb-2 font-semibold text-slate-700">Preference hiện tại</p>
                  <div className="flex flex-wrap gap-2">
                    {prefsQuery.data.map((pref) => (
                      <Badge
                        key={pref.id ?? pref.channel}
                        value={pref.enabled ? "ACTIVE" : "SUSPENDED"}
                        label={`${pref.channel}: ${pref.enabled ? "ON" : "OFF"}`}
                      />
                    ))}
                  </div>
                </div>
              )}
              {save.isError && <ErrorState error={save.error} />}
              {save.isSuccess && <p className="text-sm text-emerald-600">Đã lưu</p>}
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? "Đang lưu" : "Lưu tùy chọn"}
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
