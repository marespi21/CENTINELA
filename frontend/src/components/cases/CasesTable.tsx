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

function ScoreCell({ score }: { score: number }) {
  const tone =
    score >= 70
      ? "text-[var(--danger)]"
      : score >= 50
        ? "text-[var(--warning)]"
        : "text-[var(--success)]";
  const bar =
    score >= 70
      ? "bg-[var(--danger)]"
      : score >= 50
        ? "bg-[var(--warning)]"
        : "bg-[var(--success)]";

  return (
    <span className={`score-pill ${tone}`}>
      <span className="font-mono text-sm font-semibold">{score}</span>
      <span className="score-bar" aria-hidden>
        <span style={{ width: `${Math.min(100, Math.max(8, score))}%` }} className={bar} />
      </span>
    </span>
  );
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
          className="font-mono text-[13px] font-semibold text-[var(--accent)] hover:underline"
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
      render: (row) => <ScoreCell score={row.score} />,
    },
    {
      key: "openedAt",
      header: "Apertura",
      render: (row) => (
        <span className="text-[13px] text-[var(--muted)]">{formatDateTime(row.openedAt)}</span>
      ),
    },
    {
      key: "assignedTo",
      header: "Asignado",
      render: (row) => (
        <span className="text-[13px] text-[var(--muted)]">{row.assignedTo ?? "—"}</span>
      ),
    },
    {
      key: "summary",
      header: "Resumen",
      className: "max-w-[18rem]",
      render: (row) => (
        <span className="line-clamp-2 text-[13px] text-[var(--muted)]" title={row.summary}>
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
