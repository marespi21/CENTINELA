"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { CaseSummaryDto } from "@/lib/api/types";
import { formatDateTime, truncateId } from "@/lib/utils/format";

interface CasesTableProps {
  items: CaseSummaryDto[];
}

export function CasesTable({ items }: CasesTableProps) {
  const router = useRouter();

  const columns: DataTableColumn<CaseSummaryDto>[] = [
    {
      key: "caseId",
      header: "Caso",
      render: (row) => (
        <Link
          href={`/cases/${row.caseId}`}
          className="font-mono text-[13px] font-medium text-[var(--accent-ink)] underline-offset-2 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {truncateId(row.caseId, 10)}
        </Link>
      ),
    },
    {
      key: "accountId",
      header: "Cuenta",
      render: (row) => (
        <span className="font-mono text-[13px] text-[var(--ink)]">{row.accountId}</span>
      ),
    },
    {
      key: "status",
      header: "Estado",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "score",
      header: "Score",
      render: (row) => (
        <span
          className={
            row.score >= 70
              ? "font-mono text-sm font-semibold text-rose-700"
              : "font-mono text-sm text-[var(--ink)]"
          }
        >
          {row.score}
        </span>
      ),
    },
    {
      key: "openedAt",
      header: "Apertura",
      render: (row) => (
        <span className="text-[var(--muted)]">{formatDateTime(row.openedAt)}</span>
      ),
    },
    {
      key: "assignedTo",
      header: "Asignado",
      render: (row) => (
        <span className="text-[var(--muted)]">{row.assignedTo ?? "—"}</span>
      ),
    },
    {
      key: "summary",
      header: "Resumen",
      className: "max-w-[18rem]",
      render: (row) => (
        <span className="line-clamp-2 text-[var(--muted)]" title={row.summary}>
          {row.summary}
        </span>
      ),
    },
  ];

  return (
    <div data-testid="cases-table">
      <DataTable
        columns={columns}
        rows={items}
        rowKey={(row) => row.caseId}
        onRowClick={(row) => router.push(`/cases/${row.caseId}`)}
      />
    </div>
  );
}
