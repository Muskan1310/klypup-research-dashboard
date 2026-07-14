import type { InputHTMLAttributes } from "react";

export function TextField({
  label,
  id,
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: string; id: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
      </label>
      <input
        id={id}
        name={id}
        className={`rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:border-brand-500 focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-brand-500 disabled:bg-slate-100 dark:border-white/15 dark:bg-white/5 dark:text-white dark:placeholder:text-slate-500 ${className}`}
        {...rest}
      />
    </div>
  );
}
