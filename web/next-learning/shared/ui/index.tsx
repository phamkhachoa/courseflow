import Link from "next/link";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import clsx, { type ClassValue } from "clsx";
import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Search,
  UserRound
} from "lucide-react";
import type {
  ComponentPropsWithoutRef,
  InputHTMLAttributes,
  ReactNode
} from "react";
import { Children } from "react";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const cardVariants = cva(
  "rounded-xl border border-slate-200/80 bg-white shadow-sm",
  {
    variants: {
      padding: {
        none: "p-0",
        sm: "p-4",
        md: "p-5",
        lg: "p-6"
      },
      tone: {
        default: "",
        elevated: "shadow-[0_24px_60px_rgba(23,33,31,0.12)]",
        muted: "bg-white/70"
      }
    },
    defaultVariants: {
      padding: "md",
      tone: "default"
    }
  }
);

export function Card({
  children,
  className,
  padding,
  tone
}: {
  children: ReactNode;
  className?: string;
} & VariantProps<typeof cardVariants>) {
  return <article className={cn(cardVariants({ padding, tone }), className)}>{Children.toArray(children)}</article>;
}

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold",
  {
    variants: {
      tone: {
        neutral: "border-black/10 bg-white/80 text-ink-700",
        brand: "border-brand-100 bg-brand-50 text-brand-700",
        amber: "border-accent-100 bg-accent-50 text-accent-600",
        sky: "border-signal-100 bg-signal-50 text-signal-600",
        coral: "border-coral-50 bg-coral-50 text-coral-600",
        dark: "border-white/20 bg-white/10 text-white"
      }
    },
    defaultVariants: {
      tone: "neutral"
    }
  }
);

export function Badge({
  children,
  tone,
  className
}: {
  children: ReactNode;
  className?: string;
} & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)}>{Children.toArray(children)}</span>;
}

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-60",
  {
    variants: {
      variant: {
        primary:
          "bg-brand-600 text-white shadow-[0_12px_30px_rgba(15,111,95,0.25)] hover:bg-brand-700 focus-visible:ring-brand-100",
        secondary:
          "border border-black/10 bg-white text-ink-700 hover:bg-brand-50 focus-visible:ring-brand-100",
        ghost: "text-ink-700 hover:bg-black/5 focus-visible:ring-brand-100",
        inverse:
          "border border-white/30 bg-white/10 text-white backdrop-blur hover:bg-white/20 focus-visible:ring-white/20"
      },
      size: {
        sm: "h-9 px-3",
        md: "h-10 px-4",
        lg: "h-11 px-5"
      }
    },
    defaultVariants: {
      variant: "primary",
      size: "md"
    }
  }
);

export function Button({
  className,
  variant,
  size,
  asChild = false,
  type = "button",
  ...props
}: ComponentPropsWithoutRef<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(buttonVariants({ variant, size }), className)}
      type={asChild ? undefined : type}
      {...props}
    />
  );
}

export function LinkButton({
  href,
  children,
  variant,
  size,
  className
}: {
  href: string;
  children: ReactNode;
  className?: string;
} & VariantProps<typeof buttonVariants>) {
  return (
    <Button asChild variant={variant} size={size} className={className}>
      <Link href={href}>
        <span className="inline-flex items-center gap-2">{Children.toArray(children)}</span>
      </Link>
    </Button>
  );
}

export function TextInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "min-h-11 w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition placeholder:text-ink-500/60 focus:border-brand-500 focus:ring-4 focus:ring-brand-100",
        className
      )}
      {...props}
    />
  );
}

export function Textarea({
  className,
  ...props
}: ComponentPropsWithoutRef<"textarea">) {
  return (
    <textarea
      className={cn(
        "min-h-28 w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition placeholder:text-ink-500/60 focus:border-brand-500 focus:ring-4 focus:ring-brand-100",
        className
      )}
      {...props}
    />
  );
}

export function SelectInput({
  className,
  ...props
}: ComponentPropsWithoutRef<"select">) {
  return (
    <select
      className={cn(
        "min-h-11 w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100",
        className
      )}
      {...props}
    />
  );
}

export function ProgressBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-black/10">
      <div className="h-full rounded-full bg-accent-500 transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function PageShell({
  eyebrow,
  title,
  description,
  children
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-6 lg:px-8">
      <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-6 shadow-sm backdrop-blur sm:p-8">
        <SectionHeader eyebrow={eyebrow} title={title} description={description} className="mb-7" />
      </div>
      <div className="mt-6">{children}</div>
    </main>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
  className
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex flex-wrap items-end justify-between gap-3", className)}>
      <div>
        {eyebrow && <p className="mb-2 text-sm font-bold text-brand-600">{eyebrow}</p>}
        <h2 className="max-w-3xl text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">{title}</h2>
        {description && <p className="mt-2 max-w-2xl text-ink-500">{description}</p>}
      </div>
      {action}
    </header>
  );
}

const metricTone = {
  brand: "bg-brand-50 text-brand-700",
  sky: "bg-signal-50 text-signal-600",
  amber: "bg-accent-50 text-accent-600",
  coral: "bg-coral-50 text-coral-600"
};

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    PUBLISHED: "Đã công khai",
    DRAFT: "Nháp",
    ARCHIVED: "Lưu trữ",
    ACTIVE: "Đang học",
    COMPLETED: "Hoàn thành"
  };
  return labels[status ?? ""] ?? status ?? "Đã công khai";
}

export function MetricCard({
  label,
  value,
  tone,
  icon,
  stateLabel = "Sẵn sàng"
}: {
  label: string;
  value: string;
  tone: keyof typeof metricTone;
  icon: ReactNode;
  stateLabel?: string;
}) {
  return (
    <Card className="relative z-10 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-ink-500">{label}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-ink-900">{value}</p>
        </div>
        <span className={cn("grid size-10 place-items-center rounded-md", metricTone[tone])}>
          {icon}
        </span>
      </div>
      <span className={cn("mt-4 inline-flex rounded-md px-2 py-1 text-xs font-bold", metricTone[tone])}>
        {stateLabel}
      </span>
    </Card>
  );
}

export function CourseCard({
  code,
  title,
  summary,
  href,
  status,
  level,
  progress,
  next,
  duration,
  mentor,
  priceLabel,
  tone
}: {
  code: string;
  title: string;
  summary: string;
  href: string;
  status?: string;
  level?: string;
  progress?: number;
  next?: string;
  duration?: string;
  mentor?: string;
  priceLabel?: string | null;
  tone: string;
}) {
  const hasProgress = typeof progress === "number";
  return (
    <Card className="flex min-h-[310px] flex-col overflow-hidden" padding="none">
      <div className={cn("h-28 bg-gradient-to-br p-5 text-white", tone)}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-bold">{code}</span>
          <Badge tone="dark">{level ?? "COURSE"}</Badge>
        </div>
      </div>
      <div className="flex flex-1 flex-col p-5">
        <h3 className="text-lg font-bold leading-6 text-ink-900">{title}</h3>
        <p className="mt-2 line-clamp-3 flex-1 text-sm leading-6 text-ink-500">{summary}</p>
        <div className="mt-5 space-y-3">
          {hasProgress && (
            <>
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-ink-500">Tiến độ</span>
                <span className="font-bold text-ink-900">{progress}%</span>
              </div>
              <ProgressBar value={progress} />
            </>
          )}
          <div className="grid gap-2 text-sm text-ink-500">
            <span className="inline-flex items-center gap-2">
              <BookOpen className="size-4" />
              {next ?? "Phòng học: chương, video, bài thi và tiến độ"}
            </span>
            <span className="inline-flex items-center gap-2">
              <Clock3 className="size-4" />
              {duration ?? "Ghi danh để bắt đầu hoặc học tiếp"}
              {mentor ? ` - ${mentor}` : ""}
            </span>
          </div>
        </div>
        <div className="mt-5 flex items-center justify-between">
          <div className="flex min-w-0 flex-wrap gap-2">
            <Badge tone="neutral">{statusLabel(status)}</Badge>
            {priceLabel && <Badge tone={priceLabel === "Miễn phí" ? "brand" : "amber"}>{priceLabel}</Badge>}
          </div>
          <Link href={href} className="inline-flex items-center gap-1 text-sm font-bold text-brand-700 hover:text-brand-900">
            <span className="inline-flex items-center gap-1">
              <span>Vào học</span>
              <ChevronRight className="size-4" />
            </span>
          </Link>
        </div>
      </div>
    </Card>
  );
}

export function ScheduleItem({
  time,
  title,
  type
}: {
  time: string;
  title: string;
  type: string;
}) {
  return (
    <div className="flex gap-3 rounded-lg border border-black/10 p-3">
      <div className="w-14 shrink-0 text-sm font-bold text-ink-900">{time}</div>
      <div>
        <Badge tone={type === "LIVE" ? "brand" : type === "QUIZ" ? "amber" : "sky"}>{type}</Badge>
        <p className="mt-2 text-sm font-semibold text-ink-900">{title}</p>
      </div>
    </div>
  );
}

export function ProgressMetric({
  title,
  detail,
  value
}: {
  title: string;
  detail: string;
  value: number;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3 text-sm">
        <span className="font-semibold text-ink-900">{title}</span>
        <span className="text-right text-ink-500">{detail}</span>
      </div>
      <ProgressBar value={value} />
    </div>
  );
}

export function NumberedList({ items }: { items: string[] }) {
  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item} className="flex gap-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-md bg-brand-50 text-sm font-bold text-brand-700">
            {index + 1}
          </span>
          <p className="text-sm leading-6 text-ink-700">{item}</p>
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <Card className="grid place-items-center py-12 text-center">
      <Search className="size-10 text-ink-500" />
      <h3 className="mt-4 text-lg font-bold text-ink-900">{title}</h3>
      {description && <p className="mt-2 max-w-md text-sm leading-6 text-ink-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </Card>
  );
}

export function FeatureTile({ title, icon }: { title: string; icon?: ReactNode }) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <div className="mb-3 grid size-9 place-items-center rounded-md bg-brand-50 text-brand-700">
        {icon ?? <CheckCircle2 className="size-5" />}
      </div>
      <p className="text-sm font-bold text-ink-900">{title}</p>
    </div>
  );
}

export function UserLine({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2">
      <UserRound className="size-4" />
      {children}
    </span>
  );
}
