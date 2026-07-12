import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-indigo-600 text-white hover:bg-indigo-500 active:bg-indigo-700 disabled:bg-indigo-600/50",
  secondary:
    "bg-white text-slate-900 border border-slate-300 hover:bg-slate-50 active:bg-slate-100 disabled:text-slate-400 dark:bg-white/5 dark:text-white dark:border-white/15 dark:hover:bg-white/10",
  ghost:
    "text-slate-600 hover:bg-slate-100 active:bg-slate-200 disabled:text-slate-300 dark:text-slate-300 dark:hover:bg-white/10",
};

export function Button({
  variant = "primary",
  className = "",
  disabled,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
