"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, LogIn, PlayCircle, UserPlus } from "lucide-react";
import { enrollInCourse, listMyEnrollments } from "@/features/enrollments/api";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, cn } from "@/shared/ui";

type EnrollmentCtaProps = {
  courseId: string;
  courseSlug: string;
  className?: string;
  inverse?: boolean;
};

function isActiveEnrollment(status?: string) {
  return status === "ACTIVE" || status === "COMPLETED";
}

export function EnrollmentCta({ courseId, courseSlug, className, inverse = false }: EnrollmentCtaProps) {
  const qc = useQueryClient();
  const [session, setSession] = useState<StoredSession | null>(null);
  const moduleHref = `/courses/${courseSlug}/modules?courseId=${courseId}`;
  const loginHref = `/login?next=${encodeURIComponent(moduleHref)}`;

  useEffect(() => {
    setSession(learnerSession.read());
    return learnerSession.subscribe(setSession);
  }, []);

  const enrollments = useQuery({
    queryKey: ["my-enrollment", courseId, session?.user.id],
    queryFn: () => listMyEnrollments(courseId),
    enabled: Boolean(courseId && session?.accessToken)
  });

  const current = enrollments.data?.find((item) => item.courseId === courseId);
  const enrolled = isActiveEnrollment(current?.status);

  const enroll = useMutation({
    mutationFn: () => enrollInCourse(courseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-enrollment", courseId, session?.user.id] });
      qc.invalidateQueries({ queryKey: ["course-modules", courseId] });
      qc.invalidateQueries({ queryKey: ["course-progress", courseId] });
    }
  });

  if (!session) {
    return (
      <Button asChild variant={inverse ? "inverse" : "secondary"} className={className}>
        <Link href={loginHref}>
          <span className="inline-flex items-center gap-2">
            <LogIn className="size-4" />
            <span>Đăng nhập để tham gia</span>
          </span>
        </Link>
      </Button>
    );
  }

  if (enrollments.isLoading) {
    return (
      <Button disabled variant={inverse ? "inverse" : "secondary"} className={className}>
        Đang kiểm tra ghi danh
      </Button>
    );
  }

  if (enrolled) {
    return (
      <div className={cn("flex flex-wrap items-center gap-3", className)}>
        <Button asChild>
          <Link href={moduleHref}>
            <span className="inline-flex items-center gap-2">
              <PlayCircle className="size-4" />
              <span>Vào học</span>
            </span>
          </Link>
        </Button>
        <Badge tone={inverse ? "dark" : "brand"}>
          <CheckCircle2 className="mr-1 size-3.5" />
          {current?.status === "COMPLETED" ? "Đã hoàn thành" : "Đã ghi danh"}
        </Badge>
      </div>
    );
  }

  const enrollLabel = current?.status === "DROPPED"
    ? enroll.isPending ? "Đang ghi danh lại" : "Ghi danh lại"
    : enroll.isPending ? "Đang tham gia" : "Tham gia khóa học";

  return (
    <div className={cn("flex flex-col items-start gap-2", className)}>
      <Button onClick={() => enroll.mutate()} disabled={enroll.isPending}>
        <UserPlus className="size-4" />
        {enrollLabel}
      </Button>
      {(enroll.isError || enrollments.isError) && (
        <p className={cn("max-w-md text-sm", inverse ? "text-white/75" : "text-red-600")}>
          {(enroll.error ?? enrollments.error)?.message ?? "Không thể ghi danh khóa học này."}
        </p>
      )}
    </div>
  );
}
