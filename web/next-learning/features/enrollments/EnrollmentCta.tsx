"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, LogIn, PlayCircle, TicketPercent, UserPlus, XCircle } from "lucide-react";
import {
  checkoutEnrollment,
  getEnrollmentPromotionApplication,
  listMyEnrollments,
  previewEnrollmentPromotion,
  type EnrollmentPromotionApplication,
  type PromotionEffect,
  type PromotionPreview
} from "@/features/enrollments/api";
import { getLearnerCouponWallet, type LearnerCoupon } from "@/features/promotions/api";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, TextInput, cn } from "@/shared/ui";

type EnrollmentCtaProps = {
  courseId: string;
  courseSlug: string;
  className?: string;
  inverse?: boolean;
};

function isActiveEnrollment(status?: string) {
  return status === "ACTIVE" || status === "COMPLETED";
}

function operationId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const reasonLabels: Record<string, string> = {
  COUPON_REQUIRED: "Nhập mã ưu đãi để kiểm tra.",
  PROMOTION_UNAVAILABLE: "Chưa kiểm tra được ưu đãi.",
  PROMOTION_REJECTED: "Mã này chưa áp dụng được cho khóa học này.",
  COUPON_NOT_FOUND: "Không tìm thấy mã ưu đãi.",
  COUPON_EXPIRED: "Mã ưu đãi đã hết hạn.",
  COUPON_EXHAUSTED: "Mã ưu đãi đã hết lượt sử dụng.",
  COUPON_HOLDER_MISMATCH: "Mã ưu đãi không dành cho tài khoản này.",
  COUPON_REQUIRED_BUT_MISSING: "Khóa học cần mã ưu đãi hợp lệ.",
  MIN_ORDER_AMOUNT_NOT_MET: "Chưa đạt điều kiện tối thiểu.",
  CAMPAIGN_NOT_ACTIVE: "Ưu đãi chưa hoạt động.",
  NO_MATCHING_CAMPAIGN: "Không có ưu đãi phù hợp.",
  PROMOTION_COMMIT_UNAVAILABLE: "Ưu đãi đang chờ hệ thống xác nhận.",
  PROMOTION_COMMIT_REJECTED: "Ưu đãi cần được hỗ trợ kiểm tra lại.",
  RESERVATION_EXPIRED: "Phiên giữ ưu đãi đã hết hạn.",
  RESERVATION_CANCELLED: "Phiên giữ ưu đãi đã được hủy."
};

function reasonText(reasonCodes?: string[]) {
  const codes = reasonCodes?.length ? reasonCodes : ["PROMOTION_REJECTED"];
  return codes.map((code) => reasonLabels[code] ?? code).join(" ");
}

function numeric(value: number | string | null | undefined) {
  const parsed = typeof value === "number" ? value : Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function money(value: number | string | null | undefined, currency?: string | null) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: currency || "USD",
    maximumFractionDigits: 0
  }).format(numeric(value));
}

function pointsEffect(effects?: PromotionEffect[]) {
  return effects?.find((effect) => effect.benefitType === "POINTS_EARN_INTENT");
}

function PreviewSummary({ preview, inverse }: { preview: PromotionPreview; inverse?: boolean }) {
  const points = pointsEffect(preview.effects);
  const textTone = inverse ? "text-white/80" : "text-ink-500";
  if (preview.promotionUnavailable) {
    return (
      <div className={cn("rounded-md border px-3 py-2 text-sm", inverse ? "border-white/20 bg-white/10 text-white" : "border-accent-100 bg-accent-50 text-accent-700")}>
        {preview.message ?? reasonText(preview.reasonCodes)}
      </div>
    );
  }
  if (!preview.eligible) {
    return (
      <div className={cn("flex items-start gap-2 rounded-md border px-3 py-2 text-sm", inverse ? "border-white/20 bg-white/10 text-white" : "border-coral-100 bg-coral-50 text-coral-700")}>
        <XCircle className="mt-0.5 size-4 shrink-0" />
        <span>{reasonText(preview.reasonCodes)}</span>
      </div>
    );
  }
  return (
    <div className={cn("rounded-md border px-3 py-2 text-sm", inverse ? "border-white/20 bg-white/10 text-white" : "border-brand-100 bg-brand-50 text-brand-800")}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={inverse ? "dark" : "brand"}>
          <CheckCircle2 className="mr-1 size-3.5" />
          Áp dụng được
        </Badge>
        <span className={textTone}>
          Giá gốc {money(preview.originalAmount, preview.currency)} · giảm {money(preview.discountAmount, preview.currency)} · còn {money(preview.finalAmount, preview.currency)}
        </span>
      </div>
      {points && (
        <p className={cn("mt-2", textTone)}>
          Nhận {numeric(points.quantity ?? points.amount).toLocaleString("vi-VN")} điểm sau khi ghi danh thành công.
        </p>
      )}
    </div>
  );
}

function AppliedPromotion({
  promotion,
  attemptId,
  inverse
}: {
  promotion?: EnrollmentPromotionApplication | null;
  attemptId?: string | null;
  inverse?: boolean;
}) {
  if (!promotion || promotion.status === "SKIPPED") return null;
  const status = promotion.status;
  const success = status === "APPLIED";
  const pending = status === "COMMIT_FAILED" || status === "RESERVED";
  const manualReview = status === "MANUAL_REVIEW";
  const nextRetry = promotion.nextRetryAt ? new Date(promotion.nextRetryAt).toLocaleString("vi-VN") : null;
  const message = success
    ? "Ưu đãi đã được ghi nhận cho lượt ghi danh."
    : pending
      ? "Bạn đã được ghi danh. Ưu đãi đang chờ xác nhận tự động, hệ thống sẽ cập nhật lại sau."
      : manualReview
        ? "Bạn đã được ghi danh. Ưu đãi cần bộ phận hỗ trợ kiểm tra lại."
        : promotion.message ?? reasonText(promotion.reasonCodes);
  const toneClass = inverse
    ? "border-white/20 bg-white/10 text-white"
    : success
      ? "border-brand-100 bg-brand-50 text-brand-800"
      : pending || manualReview
        ? "border-accent-100 bg-accent-50 text-accent-700"
        : "border-slate-200 bg-slate-50 text-slate-700";
  return (
    <div className={cn("rounded-md border px-3 py-2 text-sm", toneClass)}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={success ? "brand" : inverse ? "dark" : "neutral"}>{status}</Badge>
        <span>{message}</span>
      </div>
      {attemptId && (pending || manualReview) && (
        <p className={cn("mt-1 text-xs", inverse ? "text-white/70" : "text-ink-500")}>
          Mã xử lý: {attemptId.slice(0, 8)}
        </p>
      )}
      {(pending || manualReview) && (nextRetry || promotion.lastRetryError) && (
        <p className={cn("mt-1 text-xs", inverse ? "text-white/70" : "text-ink-500")}>
          {nextRetry ? `Hệ thống sẽ thử lại: ${nextRetry}` : promotion.lastRetryError}
        </p>
      )}
    </div>
  );
}

export function EnrollmentCta({ courseId, courseSlug, className, inverse = false }: EnrollmentCtaProps) {
  const qc = useQueryClient();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [couponCode, setCouponCode] = useState("");
  const [selectedCoupon, setSelectedCoupon] = useState<LearnerCoupon | null>(null);
  const [preview, setPreview] = useState<PromotionPreview | null>(null);
  const [appliedPromotion, setAppliedPromotion] = useState<EnrollmentPromotionApplication | null>(null);
  const [lastAttemptId, setLastAttemptId] = useState<string | null>(null);
  const [checkoutAttemptKey, setCheckoutAttemptKey] = useState(() => operationId("enrollment"));
  const moduleHref = `/courses/${courseSlug}/modules`;
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
  const persistedPromotion = useQuery({
    queryKey: ["enrollment-promotion-application", current?.id],
    queryFn: () => getEnrollmentPromotionApplication(current!.id),
    enabled: Boolean(session?.accessToken && current?.id),
    retry: 1
  });
  const couponWallet = useQuery({
    queryKey: ["learner", "promotions", "coupons", session?.user.id],
    queryFn: getLearnerCouponWallet,
    enabled: Boolean(session?.accessToken),
    retry: 1
  });
  const availableCoupons = couponWallet.data?.items.filter((coupon) => coupon.walletStatus === "AVAILABLE") ?? [];
  const normalizedCoupon = couponCode.trim().toUpperCase();
  const selectedCouponId = selectedCoupon?.couponId;
  const previewMatchesCoupon = Boolean(
    selectedCouponId
      ? preview?.couponId === selectedCouponId
      : preview?.couponCode && preview.couponCode.toUpperCase() === normalizedCoupon
  );
  const hasCouponSelector = Boolean(selectedCouponId || normalizedCoupon);
  const canSubmitCoupon = Boolean(hasCouponSelector && previewMatchesCoupon && preview?.eligible);
  const couponBlocksEnrollment = Boolean(hasCouponSelector && !canSubmitCoupon);

  const previewMutation = useMutation({
    mutationFn: () => previewEnrollmentPromotion({
      courseId,
      couponCode: selectedCouponId ? undefined : couponCode.trim(),
      couponId: selectedCouponId
    }),
    onSuccess: (result) => {
      setPreview(result);
      setAppliedPromotion(null);
      setLastAttemptId(null);
      setCheckoutAttemptKey(operationId("enrollment"));
    }
  });

  const checkout = useMutation({
    mutationFn: () => checkoutEnrollment({
      courseId,
      couponCode: canSubmitCoupon && !selectedCouponId ? couponCode.trim() : undefined,
      couponId: canSubmitCoupon ? selectedCouponId : undefined,
      promotionPreviewId: preview?.previewId,
      idempotencyKey: checkoutAttemptKey
    }),
    onSuccess: (result) => {
      setAppliedPromotion(result.promotion ?? null);
      setLastAttemptId(result.attemptId ?? null);
      setCheckoutAttemptKey(operationId("enrollment"));
      qc.invalidateQueries({ queryKey: ["my-enrollment", courseId, session?.user.id] });
      qc.invalidateQueries({ queryKey: ["course-modules", courseId] });
      qc.invalidateQueries({ queryKey: ["course-progress", courseId] });
      qc.invalidateQueries({ queryKey: ["enrollment-promotion-application", result.enrollment.id] });
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
    const visiblePromotion = appliedPromotion ?? persistedPromotion.data ?? null;
    const visibleAttemptId = lastAttemptId ?? visiblePromotion?.id ?? null;
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
        <AppliedPromotion promotion={visiblePromotion} attemptId={visibleAttemptId} inverse={inverse} />
      </div>
    );
  }

  const enrollLabel = current?.status === "DROPPED"
    ? checkout.isPending ? "Đang ghi danh lại" : "Ghi danh lại"
    : checkout.isPending ? "Đang tham gia" : "Tham gia khóa học";

  return (
    <div className={cn("flex w-full max-w-xl flex-col items-start gap-3", className)}>
      <div className="flex w-full flex-col gap-2 sm:flex-row">
        <TextInput
          value={couponCode}
          onChange={(event) => {
            setCouponCode(event.target.value);
            setSelectedCoupon(null);
            setPreview(null);
            setAppliedPromotion(null);
            setLastAttemptId(null);
            setCheckoutAttemptKey(operationId("enrollment"));
          }}
          placeholder="Mã ưu đãi"
          className={cn("min-h-10 py-2", inverse && "border-white/30 bg-white/10 text-white placeholder:text-white/60")}
        />
        <Button
          variant={inverse ? "inverse" : "secondary"}
          onClick={() => previewMutation.mutate()}
          disabled={!hasCouponSelector || previewMutation.isPending}
          className="shrink-0"
        >
          <TicketPercent className="size-4" />
          {previewMutation.isPending ? "Đang kiểm tra" : "Áp dụng"}
        </Button>
      </div>

      {availableCoupons.length > 0 && (
        <div className="flex max-w-full flex-wrap gap-2">
          {availableCoupons.slice(0, 4).map((coupon) => (
            <button
              key={coupon.couponId}
              type="button"
              onClick={() => {
                setSelectedCoupon(coupon);
                setCouponCode(coupon.codeMask || coupon.campaignCode);
                setPreview(null);
                setAppliedPromotion(null);
                setLastAttemptId(null);
                setCheckoutAttemptKey(operationId("enrollment"));
              }}
              className={cn(
                "rounded-md border px-2.5 py-1.5 text-xs font-semibold transition",
                selectedCouponId === coupon.couponId
                  ? inverse
                    ? "border-white/40 bg-white/20 text-white"
                    : "border-brand-200 bg-brand-50 text-brand-700"
                  : inverse
                    ? "border-white/20 bg-white/10 text-white/80 hover:bg-white/15"
                    : "border-slate-200 bg-white text-ink-600 hover:border-brand-200"
              )}
            >
              {coupon.codeMask || coupon.campaignName}
            </button>
          ))}
        </div>
      )}

      {preview && <PreviewSummary preview={preview} inverse={inverse} />}
      <AppliedPromotion promotion={appliedPromotion} attemptId={lastAttemptId} inverse={inverse} />

      <Button onClick={() => checkout.mutate()} disabled={checkout.isPending || couponBlocksEnrollment}>
        <UserPlus className="size-4" />
        {enrollLabel}
      </Button>
      {couponBlocksEnrollment && (
        <p className={cn("max-w-md text-sm", inverse ? "text-white/75" : "text-ink-500")}>
          Kiểm tra mã ưu đãi trước khi ghi danh, hoặc xóa mã để tiếp tục không dùng ưu đãi.
        </p>
      )}
      {(checkout.isError || previewMutation.isError || enrollments.isError) && (
        <p className={cn("max-w-md text-sm", inverse ? "text-white/75" : "text-red-600")}>
          {(checkout.error ?? previewMutation.error ?? enrollments.error)?.message ?? "Không thể ghi danh khóa học này."}
        </p>
      )}
    </div>
  );
}
