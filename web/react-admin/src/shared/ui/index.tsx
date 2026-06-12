import {
  forwardRef,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes
} from "react";
import { cn } from "./cn";

// --- Button ----------------------------------------------------------------
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
};

const buttonVariants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: "bg-brand-600 text-white shadow-sm hover:bg-brand-700 disabled:bg-slate-300",
  secondary: "border border-slate-200 bg-white text-slate-700 shadow-sm hover:bg-brand-50 hover:text-brand-700",
  danger: "bg-red-600 text-white shadow-sm hover:bg-red-700 disabled:bg-red-300",
  ghost: "bg-transparent text-slate-600 hover:bg-slate-100"
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
        "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition outline-none focus-visible:ring-4 focus-visible:ring-brand-100 disabled:cursor-not-allowed",
        size === "sm" ? "px-3 py-1.5 text-sm" : "px-4 py-2 text-sm",
        buttonVariants[variant],
        className
      )}
      {...props}
    />
  );
});

// --- Input / Textarea / Select ---------------------------------------------
const fieldBase =
  "w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-4 focus:ring-brand-100";

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
    return <select ref={ref} className={cn(fieldBase, className)} {...props} />;
  }
);

export function FormField({
  label,
  htmlFor,
  children,
  hint
}: {
  label: string;
  htmlFor?: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="flex flex-col gap-1" htmlFor={htmlFor}>
      <span className="text-sm font-semibold text-slate-700">{label}</span>
      {children}
      {hint && <span className="text-xs text-slate-400">{hint}</span>}
    </label>
  );
}

// --- Card ------------------------------------------------------------------
export function Card({ children, className, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn("rounded-md border border-black/10 bg-white shadow-[0_12px_32px_rgba(15,23,42,0.06)]", className)}
      {...props}
    >
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  actions,
  subtitle
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-black/10 px-5 py-4">
      <div>
        <h3 className="text-base font-bold text-slate-900">{title}</h3>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions}
    </header>
  );
}

// --- Badge -----------------------------------------------------------------
const badgeTones: Record<string, string> = {
  PUBLISHED: "bg-emerald-100 text-emerald-700",
  READY: "bg-emerald-100 text-emerald-700",
  ACTIVE: "bg-emerald-100 text-emerald-700",
  UPLOADED: "bg-sky-100 text-sky-700",
  LESSON: "bg-brand-100 text-brand-700",
  VIDEO: "bg-sky-100 text-sky-700",
  DOCUMENT: "bg-indigo-100 text-indigo-700",
  MATERIAL: "bg-indigo-100 text-indigo-700",
  PDF: "bg-indigo-100 text-indigo-700",
  LINK: "bg-cyan-100 text-cyan-700",
  REQUIRED: "bg-emerald-100 text-emerald-700",
  TRANSCODING: "bg-indigo-100 text-indigo-700",
  DRAFT: "bg-amber-100 text-amber-700",
  ARCHIVED: "bg-slate-200 text-slate-600",
  REVOKED: "bg-red-100 text-red-700",
  SUSPENDED: "bg-red-100 text-red-700",
  default: "bg-slate-100 text-slate-600"
};

export function Badge({ value, label }: { value?: string; label?: ReactNode }) {
  const tone = badgeTones[value ?? ""] ?? badgeTones.default;
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold", tone)}>
      {label ?? value ?? "—"}
    </span>
  );
}

// --- Table -----------------------------------------------------------------
export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-md border border-slate-100">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  );
}

export function Th({ children }: { children?: ReactNode }) {
  return (
    <th className="border-b border-slate-200 bg-slate-50 px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
      {children}
    </th>
  );
}

export function Td({ children, className }: { children?: ReactNode; className?: string }) {
  return <td className={cn("border-b border-slate-100 px-4 py-2.5", className)}>{children}</td>;
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

export function EmptyState({ message }: { message: string }) {
  return <div className="p-8 text-center text-sm text-slate-500">{message}</div>;
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "Đã xảy ra lỗi";
  return (
    <div className="m-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      {message}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-black/10 pb-5">
      <div>
        <h1 className="text-2xl font-bold tracking-normal text-slate-950 md:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{description}</p>}
      </div>
      {actions}
    </div>
  );
}
