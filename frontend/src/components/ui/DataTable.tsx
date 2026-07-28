import type { ReactNode } from "react";

import { cn } from "@/lib/utils/cn";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  className?: string;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  className,
}: DataTableProps<T>) {
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-xs font-semibold text-[var(--muted)]">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn("px-4 py-3.5 first:pl-5 last:pr-5", col.className)}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                "border-b border-[var(--border)]/70 transition-colors duration-150 last:border-0",
                onRowClick && "cursor-pointer hover:bg-[var(--accent-soft)]",
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn("px-4 py-4 align-middle first:pl-5 last:pr-5", col.className)}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
