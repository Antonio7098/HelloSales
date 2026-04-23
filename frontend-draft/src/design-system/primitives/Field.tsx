import { forwardRef, useId } from "react";
import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";
import { cn } from "@/shared/lib/cn";

type FieldProps = {
  label?: ReactNode;
  hint?: ReactNode;
  children: (props: { id: string }) => ReactNode;
  className?: string;
};

export function Field({ label, hint, children, className }: FieldProps) {
  const id = useId();
  return (
    <div className={cn("field", className)}>
      {label ? (
        <label htmlFor={id} className="field-label">
          {label}
        </label>
      ) : null}
      {children({ id })}
      {hint ? <span className="text-body-muted text-mono">{hint}</span> : null}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn("input", className)} {...props} />;
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, rows, ...props }, ref) {
  return <textarea ref={ref} rows={rows ?? 2} className={cn("textarea", className)} {...props} />;
});
