import {
  forwardRef,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TableHTMLAttributes,
  type TdHTMLAttributes,
  type TextareaHTMLAttributes,
  type ThHTMLAttributes
} from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { cn } from "./cn";

// --- Button ----------------------------------------------------------------
type ButtonVariant = "primary" | "secondary" | "outline" | "danger" | "ghost" | "subtle";
type ButtonSize = "xs" | "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

const buttonVariants: Record<ButtonVariant, string> = {
  primary: "bg-brand-600 text-white shadow-sm hover:bg-brand-700 disabled:bg-slate-300",
  secondary:
    "border border-slate-200 bg-white text-slate-700 shadow-sm hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700",
  outline: "border border-slate-300 bg-transparent text-slate-700 hover:border-brand-300 hover:bg-brand-50",
  danger: "bg-red-600 text-white shadow-sm hover:bg-red-700 disabled:bg-red-300",
  ghost: "bg-transparent text-slate-600 hover:bg-slate-100",
  subtle: "bg-slate-100 text-slate-700 hover:bg-slate-200"
};

const buttonSizes: Record<ButtonSize, string> = {
  xs: "h-8 px-2.5 text-xs",
  sm: "h-9 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-5 text-sm"
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", className, type = "button", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition outline-none focus-visible:ring-4 focus-visible:ring-brand-100 disabled:cursor-not-allowed disabled:opacity-70",
        buttonSizes[size],
        buttonVariants[variant],
        className
      )}
      {...props}
    />
  );
});

// --- Input / Textarea / Select ---------------------------------------------
const fieldBase =
  "w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition placeholder:text-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 focus:border-brand-500 focus:ring-4 focus:ring-brand-100";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(fieldBase, className)} {...props} />;
  }
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(fieldBase, "min-h-24", className)} {...props} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, ...props }, ref) {
    return <select ref={ref} className={cn(fieldBase, "pr-9", className)} {...props} />;
  }
);

export function FormField({
  label,
  htmlFor,
  children,
  hint,
  error,
  required,
  className
}: {
  label: string;
  htmlFor?: string;
  children: ReactNode;
  hint?: string;
  error?: string | null;
  required?: boolean;
  className?: string;
}) {
  return (
    <label className={cn("flex flex-col gap-1", className)} htmlFor={htmlFor}>
      <span className="flex items-center gap-1 text-sm font-semibold text-slate-700">
        {label}
        {required && <span className="text-red-500">*</span>}
      </span>
      {children}
      {error ? (
        <span className="text-xs font-medium text-red-600">{error}</span>
      ) : hint ? (
        <span className="text-xs text-slate-400">{hint}</span>
      ) : null}
    </label>
  );
}

// --- Card / Surface ---------------------------------------------------------
type CardVariant = "default" | "elevated" | "muted" | "warning" | "danger" | "success";
type CardPadding = "none" | "sm" | "md" | "lg";

const cardVariants: Record<CardVariant, string> = {
  default: "border-black/10 bg-white shadow-[0_12px_32px_rgba(15,23,42,0.06)]",
  elevated: "border-black/10 bg-white shadow-[0_18px_45px_rgba(15,23,42,0.10)]",
  muted: "border-slate-200 bg-slate-50/80 shadow-none",
  warning: "border-amber-200 bg-amber-50/75 shadow-none",
  danger: "border-red-200 bg-red-50/75 shadow-none",
  success: "border-emerald-200 bg-emerald-50/75 shadow-none"
};

const cardPadding: Record<CardPadding, string> = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-5"
};

type CardProps = HTMLAttributes<HTMLElement> & {
  variant?: CardVariant;
  padding?: CardPadding;
};

export function Card({ children, className, variant = "default", padding = "none", ...props }: CardProps) {
  return (
    <section
      className={cn("rounded-md border", cardVariants[variant], cardPadding[padding], className)}
      {...props}
    >
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  actions,
  subtitle,
  compact = false
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  compact?: boolean;
}) {
  return (
    <header
      className={cn(
        "flex items-center justify-between gap-4 border-b border-black/10",
        compact ? "px-4 py-3" : "px-5 py-4"
      )}
    >
      <div className="min-w-0">
        <h3 className="truncate text-base font-bold text-slate-900">{title}</h3>
        {subtitle && <p className="mt-0.5 text-sm leading-5 text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </header>
  );
}

// --- Badge -----------------------------------------------------------------
type BadgeTone = "neutral" | "brand" | "success" | "info" | "warning" | "danger" | "slate";

const badgeTones: Record<BadgeTone, string> = {
  neutral: "bg-slate-100 text-slate-600",
  brand: "bg-brand-100 text-brand-700",
  success: "bg-emerald-100 text-emerald-700",
  info: "bg-sky-100 text-sky-700",
  warning: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
  slate: "bg-slate-200 text-slate-700"
};

const semanticBadgeTones: Record<string, BadgeTone> = {
  PUBLISHED: "success",
  READY: "success",
  ACTIVE: "success",
  UPLOADED: "info",
  VIDEO: "info",
  LESSON: "brand",
  DOCUMENT: "brand",
  MATERIAL: "brand",
  PDF: "brand",
  LINK: "info",
  REQUIRED: "success",
  TRANSCODING: "brand",
  DRAFT: "warning",
  ARCHIVED: "slate",
  REVOKED: "danger",
  SUSPENDED: "danger",
  DEACTIVATED: "danger"
};

export function Badge({
  value,
  label,
  tone,
  className
}: {
  value?: string;
  label?: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  const resolvedTone = tone ?? semanticBadgeTones[value ?? ""] ?? "neutral";
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold", badgeTones[resolvedTone], className)}>
      {label ?? value ?? "-"}
    </span>
  );
}

// --- Enterprise patterns ----------------------------------------------------
type NoticeTone = "info" | "success" | "warning" | "danger" | "neutral";

const noticeStyles: Record<
  NoticeTone,
  { box: string; icon: string; defaultIcon: ReactNode }
> = {
  info: {
    box: "border-sky-200 bg-sky-50 text-sky-900",
    icon: "bg-white text-sky-700",
    defaultIcon: <Info size={16} />
  },
  success: {
    box: "border-emerald-200 bg-emerald-50 text-emerald-900",
    icon: "bg-white text-emerald-700",
    defaultIcon: <CheckCircle2 size={16} />
  },
  warning: {
    box: "border-amber-200 bg-amber-50 text-amber-900",
    icon: "bg-white text-amber-700",
    defaultIcon: <AlertTriangle size={16} />
  },
  danger: {
    box: "border-red-200 bg-red-50 text-red-900",
    icon: "bg-white text-red-700",
    defaultIcon: <XCircle size={16} />
  },
  neutral: {
    box: "border-slate-200 bg-slate-50 text-slate-800",
    icon: "bg-white text-slate-600",
    defaultIcon: <Info size={16} />
  }
};

export function Notice({
  tone = "info",
  title,
  children,
  actions,
  icon,
  className
}: {
  tone?: NoticeTone;
  title: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  const styles = noticeStyles[tone];
  return (
    <div className={cn("rounded-md border px-4 py-3", styles.box, className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 gap-3">
          <span className={cn("grid size-8 shrink-0 place-items-center rounded-md shadow-sm", styles.icon)}>
            {icon ?? styles.defaultIcon}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-bold">{title}</p>
            {children && <div className="mt-1 text-sm leading-6 opacity-85">{children}</div>}
          </div>
        </div>
        {actions && <div className="shrink-0">{actions}</div>}
      </div>
    </div>
  );
}

type StatTone = "brand" | "success" | "info" | "warning" | "danger" | "neutral";

const statTones: Record<StatTone, string> = {
  brand: "bg-brand-50 text-brand-700",
  success: "bg-emerald-50 text-emerald-700",
  info: "bg-sky-50 text-sky-700",
  warning: "bg-amber-50 text-amber-700",
  danger: "bg-red-50 text-red-700",
  neutral: "bg-slate-100 text-slate-700"
};

export function StatCard({
  label,
  value,
  detail,
  icon,
  tone = "neutral",
  className
}: {
  label: ReactNode;
  value: ReactNode;
  detail?: ReactNode;
  icon?: ReactNode;
  tone?: StatTone;
  className?: string;
}) {
  return (
    <Card padding="md" className={className}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-2 truncate text-2xl font-bold text-slate-950">{value}</p>
        </div>
        {icon && <span className={cn("grid size-10 shrink-0 place-items-center rounded-md", statTones[tone])}>{icon}</span>}
      </div>
      {detail && <p className="mt-3 text-sm leading-5 text-slate-500">{detail}</p>}
    </Card>
  );
}

export function Toolbar({ children, className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex flex-wrap items-end gap-3 rounded-md border border-slate-200 bg-slate-50/80 p-4", className)}
      {...props}
    >
      {children}
    </div>
  );
}

// --- Table -----------------------------------------------------------------
export function Table({ children, className, ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
      <table className={cn("w-full border-collapse text-sm", className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export function Th({ children, className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("border-b border-slate-200 bg-slate-50 px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500", className)}
      {...props}
    >
      {children}
    </th>
  );
}

export function Td({ children, className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("border-b border-slate-100 px-4 py-2.5 text-slate-700", className)} {...props}>
      {children}
    </td>
  );
}

// --- State helpers ---------------------------------------------------------
export function Spinner({ label = "Đang tải" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 p-6 text-sm text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
      {label}
    </div>
  );
}

export function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div className="p-8 text-center text-sm text-slate-500">
      <p>{message}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "Đã xảy ra lỗi";
  return <Notice tone="danger" title="Không thể tải dữ liệu" className="m-4">{message}</Notice>;
}

export function PageHeader({
  title,
  description,
  actions,
  eyebrow
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-black/10 pb-5">
      <div className="min-w-0">
        {eyebrow && <p className="mb-2 text-xs font-bold uppercase tracking-[0.14em] text-brand-700">{eyebrow}</p>}
        <h1 className="text-2xl font-bold tracking-normal text-slate-950 md:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{description}</p>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
}
