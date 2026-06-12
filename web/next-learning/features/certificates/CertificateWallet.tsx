"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Award,
  CalendarDays,
  CheckCircle2,
  Download,
  ExternalLink,
  LockKeyhole,
  Search,
  ShieldCheck,
  Trophy
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import { listCatalogCourses } from "@/features/course-catalog/client-api";
import { listMyCertificates, type CertificateVerification } from "./api";
import { Badge, Button, Card, EmptyState, MetricCard, cn } from "@/shared/ui";

function formatDate(value?: string) {
  if (!value) return "Chưa rõ";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa rõ";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(date);
}

function formatGrade(value: CertificateVerification["finalGrade"]) {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${numeric.toFixed(numeric % 1 === 0 ? 0 : 1)}%`;
}

function statusTone(status: string): "brand" | "coral" | "neutral" {
  if (status === "ISSUED") return "brand";
  if (status === "REVOKED") return "coral";
  return "neutral";
}

function CertificateCard({
  certificate,
  courseTitle
}: {
  certificate: CertificateVerification;
  courseTitle: string;
}) {
  return (
    <Card className="overflow-hidden" padding="none">
      <div className="bg-gradient-to-br from-brand-600 to-signal-500 p-5 text-white">
        <div className="flex items-center justify-between gap-3">
          <Badge tone="dark">{certificate.status}</Badge>
          <Award className="size-6 text-white/75" />
        </div>
        <h3 className="mt-10 text-xl font-bold leading-7">{courseTitle}</h3>
        <p className="mt-2 text-sm font-semibold text-white/70">{certificate.verificationCode}</p>
      </div>
      <div className="space-y-4 p-5">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border border-black/10 bg-[#fbfaf7] p-3">
            <p className="text-xs font-bold uppercase text-ink-500">Điểm cuối</p>
            <p className="mt-1 text-2xl font-bold text-ink-900">{formatGrade(certificate.finalGrade)}</p>
          </div>
          <div className="rounded-md border border-black/10 bg-[#fbfaf7] p-3">
            <p className="text-xs font-bold uppercase text-ink-500">Ngày cấp</p>
            <p className="mt-2 text-sm font-bold text-ink-900">{formatDate(certificate.issuedAt)}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge tone={statusTone(certificate.status)}>
            <CheckCircle2 className="mr-1 size-3.5" />
            {certificate.status === "ISSUED" ? "Hợp lệ" : certificate.status}
          </Badge>
          <Badge tone="neutral">CourseFlow</Badge>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button asChild>
            <Link href={`/certificates/verify/${encodeURIComponent(certificate.verificationCode)}`}>
              <ShieldCheck className="size-4" />
              Xác minh
            </Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href={`/certificates/verify/${encodeURIComponent(certificate.verificationCode)}`} target="_blank">
              <ExternalLink className="size-4" />
              Public view
            </Link>
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function CertificateWallet() {
  const { session, hydrated } = useLearnerSession();
  const certificatesQuery = useQuery({
    queryKey: ["my-certificates", session?.user.id],
    queryFn: listMyCertificates,
    enabled: Boolean(session?.accessToken)
  });
  const coursesQuery = useQuery({
    queryKey: ["catalog-courses"],
    queryFn: listCatalogCourses,
    enabled: hydrated
  });

  const certificates = certificatesQuery.data ?? [];
  const courseById = useMemo(
    () => new Map((coursesQuery.data ?? []).filter((course) => course.id).map((course) => [course.id!, course])),
    [coursesQuery.data]
  );
  const issued = certificates.filter((certificate) => certificate.status === "ISSUED");
  const averageGrade = issued.length
    ? Math.round(
        issued.reduce((sum, certificate) => sum + (Number(certificate.finalGrade) || 0), 0) / issued.length
      )
    : 0;

  if (!hydrated) {
    return <Card className="h-72 animate-pulse"><span className="sr-only">Đang tải ví chứng chỉ</span></Card>;
  }

  if (!session) {
    return (
      <Card padding="lg" className="text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-md bg-brand-50 text-brand-700">
          <LockKeyhole className="size-7" />
        </span>
        <h2 className="mt-5 text-2xl font-bold text-ink-900">Đăng nhập để xem chứng chỉ</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-ink-500">
          Ví chứng chỉ chỉ hiển thị các chứng chỉ thuộc tài khoản hiện tại.
        </p>
        <Button asChild className="mt-6">
          <Link href="/login?next=/certificates">Đăng nhập</Link>
        </Button>
      </Card>
    );
  }

  if (certificatesQuery.isLoading) {
    return <Card className="h-72 animate-pulse"><span className="sr-only">Đang tải chứng chỉ</span></Card>;
  }

  if (certificates.length === 0) {
    return (
      <EmptyState
        title="Chưa có chứng chỉ"
        description="Hoàn thành khóa học và đạt điều kiện điểm cuối để chứng chỉ xuất hiện trong ví này."
        action={
          <Button asChild>
            <Link href="/search">
              <Search className="size-4" />
              Tìm khóa học
            </Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-3 md:grid-cols-3">
        <MetricCard
          label="Chứng chỉ"
          value={String(certificates.length).padStart(2, "0")}
          tone="brand"
          stateLabel="Wallet"
          icon={<Award className="size-5" />}
        />
        <MetricCard
          label="Đang hợp lệ"
          value={String(issued.length).padStart(2, "0")}
          tone="sky"
          stateLabel="Issued"
          icon={<ShieldCheck className="size-5" />}
        />
        <MetricCard
          label="Điểm TB"
          value={`${averageGrade}%`}
          tone="coral"
          stateLabel="Final grade"
          icon={<Trophy className="size-5" />}
        />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {certificates.map((certificate) => {
          const course = courseById.get(certificate.courseId);
          return (
            <CertificateCard
              key={certificate.certificateId}
              certificate={certificate}
              courseTitle={course?.title ?? `Khóa học ${certificate.courseId.slice(0, 8)}`}
            />
          );
        })}
      </section>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-accent-50 text-accent-600">
              <CalendarDays className="size-5" />
            </span>
            <div>
              <p className="font-bold text-ink-900">Chia sẻ chứng chỉ</p>
              <p className="mt-1 text-sm leading-6 text-ink-500">
                Mỗi chứng chỉ có mã xác minh riêng. Public verifier chỉ thấy trạng thái hợp lệ, khóa học và ngày cấp.
              </p>
            </div>
          </div>
          <Button asChild variant="secondary" className={cn("shrink-0")}>
            <Link href="/certificates/verify">
              <Download className="size-4" />
              Kiểm tra mã
            </Link>
          </Button>
        </div>
      </Card>
    </div>
  );
}
