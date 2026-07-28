import { cn } from "@/lib/utils/cn";
import type { CaseStatus } from "@/lib/api/types";

const STATUS_STYLES: Record<string, string> = {
  Abierto: "bg-amber-50 text-amber-900 ring-amber-200/80",
  Asignado: "bg-sky-50 text-sky-900 ring-sky-200/80",
  Resuelto: "bg-emerald-50 text-emerald-900 ring-emerald-200/80",
};

interface StatusBadgeProps {
  status: CaseStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const tone = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-700 ring-slate-200";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium tracking-wide ring-1 ring-inset",
        tone,
        className,
      )}
    >
      {status}
    </span>
  );
}
