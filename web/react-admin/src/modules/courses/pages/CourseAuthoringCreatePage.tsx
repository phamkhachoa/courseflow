import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  BookOpenCheck,
  CheckCircle2,
  FilePenLine,
  Sparkles,
  WandSparkles
} from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ErrorState,
  FormField,
  Input,
  PageHeader,
  Select,
  Textarea
} from "@/shared/ui";
import { cn } from "@/shared/ui/cn";
import { createCourseDraft } from "../api";

type DraftTemplate = {
  id: string;
  label: string;
  detail: string;
  values: {
    code: string;
    title: string;
    summary: string;
    departmentId: string;
    level: string;
    listPrice: number;
    currency: string;
  };
};

const departments = [
  { value: "20000000-0000-0000-0000-000000000001", label: "Software Engineering" },
  { value: "20000000-0000-0000-0000-000000000002", label: "Computer Science" },
  { value: "20000000-0000-0000-0000-000000000003", label: "AI Lab" }
];

const templates: DraftTemplate[] = [
  {
    id: "backend",
    label: "Khóa backend production",
    detail: "Spring Boot, microservices, events, bảo mật.",
    values: {
      code: "SE4XX",
      title: "Production Backend Service Design",
      summary: "Design and build production backend services with clear boundaries, API contracts, resilient events, observability and secure delivery practices.",
      departmentId: "20000000-0000-0000-0000-000000000001",
      level: "ADVANCED",
      listPrice: 199,
      currency: "USD"
    }
  },
  {
    id: "ai",
    label: "Khóa sản phẩm AI",
    detail: "Evaluation, guardrails ra mắt, responsible AI.",
    values: {
      code: "AI2XX",
      title: "Applied AI Product Delivery",
      summary: "Plan, evaluate and ship AI product features with measurable success metrics, offline eval sets, red-team scenarios, monitoring and rollback playbooks.",
      departmentId: "20000000-0000-0000-0000-000000000003",
      level: "INTERMEDIATE",
      listPrice: 149,
      currency: "USD"
    }
  },
  {
    id: "learning",
    label: "Khóa thiết kế học tập",
    detail: "Outcome map, storyboard, vòng lặp đánh giá.",
    values: {
      code: "LX1XX",
      title: "Online Learning Experience Studio",
      summary: "Create a complete online course experience with learner personas, outcome mapping, video lesson planning, assessment design and feedback loops.",
      departmentId: "20000000-0000-0000-0000-000000000001",
      level: "BEGINNER",
      listPrice: 99,
      currency: "USD"
    }
  }
];

function slugify(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 90);
}

function templateById(id: string | null) {
  return templates.find((template) => template.id === id) ?? templates[0];
}

function levelLabel(level?: string) {
  const labels: Record<string, string> = {
    BEGINNER: "Cơ bản",
    INTERMEDIATE: "Trung cấp",
    ADVANCED: "Nâng cao"
  };
  return labels[level ?? ""] ?? level ?? "—";
}

export function CourseAuthoringCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialTemplate = templateById(searchParams.get("template"));
  const [selectedTemplate, setSelectedTemplate] = useState(initialTemplate.id);
  const [slugTouched, setSlugTouched] = useState(false);
  const [form, setForm] = useState({
    ...initialTemplate.values,
    slug: slugify(initialTemplate.values.title)
  });

  const selectedDepartment = departments.find((department) => department.value === form.departmentId);
  const summaryWords = useMemo(
    () => form.summary.trim().split(/\s+/).filter(Boolean).length,
    [form.summary]
  );
  const readyChecks = [
    { label: "Có mã khóa học", done: Boolean(form.code.trim()) },
    { label: "Có tiêu đề", done: Boolean(form.title.trim()) },
    { label: "Slug hợp lệ", done: /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(form.slug) },
    { label: "Tóm tắt đủ rõ", done: summaryWords >= 12 },
    { label: "Giá không âm", done: Number.isFinite(form.listPrice) && form.listPrice >= 0 },
    { label: "Currency ISO3", done: /^[A-Z]{3}$/.test(form.currency) }
  ];

  const create = useMutation({
    mutationFn: () => createCourseDraft(form),
    onSuccess: (draft) => {
      navigate(`../${draft.courseId}/draft`);
    }
  });

  function applyTemplate(templateId: string) {
    const template = templateById(templateId);
    setSelectedTemplate(template.id);
    setSlugTouched(false);
    setForm({
      ...template.values,
      slug: slugify(template.values.title)
    });
  }

  function updateTitle(title: string) {
    setForm((current) => ({
      ...current,
      title,
      slug: slugTouched ? current.slug : slugify(title)
    }));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-brand-700">
        <ArrowLeft size={16} /> Quay lại authoring
      </Link>

      <PageHeader
        title="Tạo draft khóa học mới"
        description="Bắt đầu từ template, kiểm tra metadata và chuyển thẳng sang editor để xây chương học."
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <Card>
            <CardHeader title="Template nhanh" subtitle="Chọn một mẫu để tự điền metadata nền tảng." />
            <div className="grid gap-3 p-4 md:grid-cols-3">
              {templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => applyTemplate(template.id)}
                  className={cn(
                    "rounded-lg border p-4 text-left transition",
                    selectedTemplate === template.id
                      ? "border-brand-300 bg-brand-50 text-brand-900"
                      : "border-slate-200 bg-white hover:border-brand-200 hover:bg-brand-50/60"
                  )}
                >
                  <span className="grid size-9 place-items-center rounded-md bg-white text-brand-700 shadow-sm">
                    <Sparkles size={16} />
                  </span>
                  <span className="mt-3 block text-sm font-bold">{template.label}</span>
                  <span className="mt-1 block text-xs leading-5 text-slate-500">{template.detail}</span>
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Thông tin khóa học" />
            <form className="grid gap-4 p-4 md:grid-cols-2" onSubmit={handleSubmit}>
              <FormField label="Mã" htmlFor="ac-code">
                <Input
                  id="ac-code"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                  required
                />
              </FormField>
              <FormField label="Cấp độ" htmlFor="ac-level">
                <Select
                  id="ac-level"
                  value={form.level}
                  onChange={(e) => setForm({ ...form, level: e.target.value })}
                >
                  <option value="BEGINNER">Cơ bản</option>
                  <option value="INTERMEDIATE">Trung cấp</option>
                  <option value="ADVANCED">Nâng cao</option>
                </Select>
              </FormField>
              <FormField label="Tiêu đề" htmlFor="ac-title">
                <Input
                  id="ac-title"
                  value={form.title}
                  onChange={(e) => updateTitle(e.target.value)}
                  required
                />
              </FormField>
              <FormField label="Slug" htmlFor="ac-slug" hint="Slug dùng trên learner URL.">
                <div className="flex gap-2">
                  <Input
                    id="ac-slug"
                    value={form.slug}
                    onChange={(e) => {
                      setSlugTouched(true);
                      setForm({ ...form, slug: slugify(e.target.value) });
                    }}
                    required
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setSlugTouched(false);
                      setForm({ ...form, slug: slugify(form.title) });
                    }}
                  >
                    <WandSparkles size={16} />
                  </Button>
                </div>
              </FormField>
              <FormField label="List price" htmlFor="ac-list-price" hint="Nguồn giá dùng cho coupon checkout.">
                <Input
                  id="ac-list-price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.listPrice ?? "")}
                  onChange={(e) => setForm({ ...form, listPrice: e.target.value === "" ? 0 : Number(e.target.value) })}
                />
              </FormField>
              <FormField label="Currency" htmlFor="ac-currency">
                <Input
                  id="ac-currency"
                  value={form.currency}
                  maxLength={3}
                  onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })}
                />
              </FormField>
              <FormField label="Phòng ban" htmlFor="ac-dept">
                <Select
                  id="ac-dept"
                  value={form.departmentId}
                  onChange={(e) => setForm({ ...form, departmentId: e.target.value })}
                  required
                >
                  {departments.map((department) => (
                    <option key={department.value} value={department.value}>
                      {department.label}
                    </option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Tóm tắt" htmlFor="ac-summary" hint={`${summaryWords} từ`}>
                <Textarea
                  id="ac-summary"
                  value={form.summary}
                  onChange={(e) => setForm({ ...form, summary: e.target.value })}
                  rows={5}
                  className="md:min-h-[132px]"
                />
              </FormField>
              {create.isError && <ErrorState error={create.error} />}
              <div className="flex flex-wrap gap-2 md:col-span-2">
                <Button
                  type="submit"
                  disabled={create.isPending || readyChecks.some((check) => !check.done)}
                >
                  <FilePenLine size={16} />
                  {create.isPending ? "Đang tạo..." : "Tạo draft và mở editor"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => navigate("..")}>
                  Hủy
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardHeader title="Preview learner catalog" />
            <div className="p-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="mb-4 flex flex-wrap gap-2">
                  <Badge value="DRAFT" label="Đang biên soạn" />
                  <Badge value="LESSON" label={levelLabel(form.level)} />
                  <Badge value="default" label={form.code || "CODE"} />
                </div>
                <h2 className="text-xl font-bold text-slate-950">{form.title || "Tên khóa học"}</h2>
                <p className="mt-3 text-sm leading-6 text-slate-500">
                  {form.summary || "Tóm tắt khóa học sẽ hiển thị trong catalog learner."}
                </p>
                <p className="mt-4 text-xs font-semibold text-slate-500">
                  /courses/{form.slug || "course-slug"}
                </p>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Checklist sẵn sàng" />
            <div className="space-y-3 p-4">
              {readyChecks.map((check) => (
                <div key={check.label} className="flex items-center gap-3 rounded-md border border-slate-200 p-3">
                  <span className={cn(
                    "grid size-7 place-items-center rounded-full",
                    check.done ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                  )}>
                    <CheckCircle2 size={15} />
                  </span>
                  <span className="text-sm font-semibold text-slate-800">{check.label}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Thông tin vận hành" />
            <dl className="grid grid-cols-[110px_1fr] gap-y-3 p-4 text-sm">
              <dt className="text-slate-500">Department</dt>
              <dd className="font-semibold text-slate-900">{selectedDepartment?.label ?? "—"}</dd>
              <dt className="text-slate-500">Next step</dt>
              <dd className="font-semibold text-slate-900">Thêm module và bài học</dd>
              <dt className="text-slate-500">Learner</dt>
              <dd className="font-semibold text-slate-900">
                <span className="inline-flex items-center gap-1">
                  <BookOpenCheck size={15} />
                  Ẩn cho tới khi publish
                </span>
              </dd>
            </dl>
          </Card>
        </aside>
      </div>
    </div>
  );
}
