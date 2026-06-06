// Primitive UI bám DESIGN.md (mục 5). Trạng thái loading/disabled/empty bắt buộc có.
import type { ButtonHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`spin ${className}`}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  loading?: boolean;
};

export function Button({
  variant = "secondary",
  loading = false,
  disabled,
  children,
  className = "",
  ...rest
}: BtnProps) {
  const base =
    "inline-flex items-center justify-center gap-2 h-10 px-4 rounded-btn text-base font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40";
  const styles = {
    primary: "bg-brand-600 text-white hover:bg-brand-500",
    secondary: "bg-surface text-ink-900 border border-line hover:bg-canvas",
    ghost: "bg-transparent text-ink-600 hover:bg-canvas",
  }[variant];
  return (
    <button className={`${base} ${styles} ${className}`} disabled={disabled || loading} {...rest}>
      {loading && <Spinner />}
      {children}
    </button>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block mb-1.5 text-sm font-medium text-ink-600">{label}</span>
      {children}
    </label>
  );
}

const inputBase =
  "w-full rounded-btn border border-line bg-surface px-3 py-2.5 text-base text-ink-900 placeholder:text-ink-400 focus:outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-500/20";

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={inputBase} {...props} />;
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={inputBase} {...props} />;
}

export function Select({ children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={`${inputBase} cursor-pointer`} {...rest}>
      {children}
    </select>
  );
}

type Tone = "trust" | "warn" | "danger" | "neutral" | "brand";
const toneStyle: Record<Tone, string> = {
  trust: "bg-trust/10 text-trust border-trust/20",
  warn: "bg-warn/10 text-warn border-warn/20",
  danger: "bg-danger/10 text-danger border-danger/20",
  brand: "bg-brand-50 text-brand-700 border-brand-600/15",
  neutral: "bg-canvas text-ink-600 border-line",
};

export function Chip({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${toneStyle[tone]}`}
    >
      {children}
    </span>
  );
}
