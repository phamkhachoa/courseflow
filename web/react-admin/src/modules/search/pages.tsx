import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpen, ClipboardCheck, ListTree, Search as SearchIcon } from "lucide-react";
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
  Spinner,
} from "@/shared/ui";
import { searchCourses } from "./api";

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

const suggestions = ["spring boot", "microservices", "data", "security"];

export function SearchPage() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: queryKeys.search.courses(submitted),
    queryFn: () => searchCourses(submitted),
    enabled: submitted.length > 0
  });

  return (
    <div className="space-y-4">
      <PageHeader title="Tìm kiếm" description="Tìm khóa học trong read-model và mở nhanh các màn vận hành liên quan." />
      <Card>
        <CardHeader title="Command search" subtitle={submitted ? `Đang tìm: ${submitted}` : "Nhập tên, mã hoặc chủ đề khóa học"} />
        <form
          className="grid gap-3 p-4 lg:grid-cols-[1fr_auto]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setSubmitted(q.trim());
          }}
        >
          <FormField label="Từ khóa" htmlFor="search-q">
            <Input
              id="search-q"
              placeholder="VD: Spring Boot, security, microservices"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </FormField>
          <div className="flex items-end">
            <Button type="submit" disabled={!q.trim()}>
              <SearchIcon size={16} /> Tìm
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 lg:col-span-2">
            {suggestions.map((item) => (
              <Button
                key={item}
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => {
                  setQ(item);
                  setSubmitted(item);
                }}
              >
                {item}
              </Button>
            ))}
          </div>
        </form>
      </Card>

      {(isLoading || isFetching) && submitted && <Spinner />}
      {isError && <ErrorState error={error} />}
      {data && data.length === 0 && <EmptyState message="Không tìm thấy kết quả" />}
      {data && data.length > 0 && (
        <Card>
          <CardHeader title={`Kết quả (${data.length})`} subtitle="Mở nhanh course detail, curriculum hoặc bài thi." />
          <div className="grid gap-3 p-4">
            {data.map((r) => (
              <article key={r.id} className="rounded-md border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {r.code && <Badge value="PUBLISHED" label={r.code} />}
                      {r.slug && <span className="text-xs font-semibold text-slate-400">{r.slug}</span>}
                    </div>
                    <h3 className="mt-2 text-base font-bold text-slate-950">{r.title}</h3>
                    <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-500">
                      {r.summary ?? "Chưa có mô tả trong read-model."}
                    </p>
                    <p className="mt-2 text-xs text-slate-400">ID {compactId(r.id)}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link to={`/courses/${r.id}`}>
                      <Button size="sm">
                        <BookOpen size={14} /> Chi tiết
                      </Button>
                    </Link>
                    <Link to={`/course-modules?courseId=${r.id}`}>
                      <Button size="sm" variant="secondary">
                        <ListTree size={14} /> Module
                      </Button>
                    </Link>
                    <Link to={`/quizzes?courseId=${r.id}`}>
                      <Button size="sm" variant="secondary">
                        <ClipboardCheck size={14} /> Bài thi
                      </Button>
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </Card>
      )}
      {!submitted && (
        <Card>
          <div className="flex items-center justify-between gap-4 p-4 text-sm text-slate-500">
            <span>Dùng search để nhảy nhanh tới khóa học thay vì đi qua nhiều menu.</span>
            <ArrowRight size={16} />
          </div>
        </Card>
      )}
    </div>
  );
}
