import { cn } from "@/lib/utils/cn";
import type { CaseStatus } from "@/lib/api/types";

const STATUS_STYLES: Record<string, string> = {
  Abierto: "bg-amber-50 text-amber-700",
  Asignado: "bg-sky-50 text-sky-700",
  Resuelto: "bg-emerald-50 text-emerald-700",
};

interface StatusBadgeProps {
  status: CaseStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const tone = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold",
        tone,
        className,
      )}
    >
      {status}
    </span>
  );
}
