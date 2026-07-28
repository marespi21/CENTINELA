'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCase, assignCase, resolveCase } from '@/lib/api/client';
import { queryKeys } from '@/lib/query/keys';
import type { CaseDetailDto } from '@/lib/api/types';
import { TransactionCard } from './TransactionCard';
import { CaseExplanationCard } from './CaseExplanationCard';
import { AuditTrailCard } from './AuditTrailCard';
import { CaseActionsHeader, UserRole } from './CaseActionsHeader';
import { NotFoundState } from '@/components/ui/NotFoundState';
import { Shield } from 'lucide-react';

interface CaseDetailViewProps {
  caseId: string;
  initialData?: CaseDetailDto;
}

export function CaseDetailView({ caseId, initialData }: CaseDetailViewProps) {
  const queryClient = useQueryClient();
  const [activeRole, setActiveRole] = useState<UserRole>('ANALISTA');

  // Fetch case detail using React Query
  const {
    data: caseDetail,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<CaseDetailDto>({
    queryKey: queryKeys.cases.detail(caseId),
    queryFn: () => getCase(caseId),
    initialData,
    staleTime: Infinity,
    retry: false,
  });

  // Asignarme Mutation
  const assignMutation = useMutation({
    mutationFn: async () => {
      return assignCase(caseId, { assigneeId: 'analista.juanjo' });
    },
    onSuccess: (updatedCase) => {
      queryClient.setQueryData(queryKeys.cases.detail(caseId), updatedCase);
      queryClient.invalidateQueries({ queryKey: queryKeys.cases.all });
    },
  });

  // Resolver Mutation
  const resolveMutation = useMutation({
    mutationFn: async ({ resolution, note }: { resolution: string; note?: string }) => {
      return resolveCase(caseId, { resolution, note });
    },
    onSuccess: (updatedCase) => {
      queryClient.setQueryData(queryKeys.cases.detail(caseId), updatedCase);
      queryClient.invalidateQueries({ queryKey: queryKeys.cases.all });
    },
  });

  if (isLoading) {
    return (
      <div data-testid="loading-state" className="flex items-center justify-center p-12 text-slate-400">
        Cargando detalle del caso {caseId}...
      </div>
    );
  }

  if (isError) {
    const status = (error as any)?.status;
    if (status === 404) {
      return <NotFoundState caseId={caseId} />;
    }
    return (
      <div className="p-6 rounded-xl border border-rose-800 bg-rose-950/40 text-rose-300 space-y-3">
        <h3 className="font-bold text-lg">Error al cargar el caso</h3>
        <p className="text-sm">{error instanceof Error ? error.message : 'No fue posible obtener los detalles.'}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 text-xs font-semibold bg-rose-700 hover:bg-rose-600 text-white rounded-lg transition-colors"
        >
          Reintentar
        </button>
      </div>
    );
  }

  if (!caseDetail) {
    return <NotFoundState caseId={caseId} />;
  }

  return (
    <div data-testid="case-detail-container" className="space-y-6 max-w-7xl mx-auto p-4 sm:p-6">
      {/* Role Switcher Toolbar */}
      <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/40 text-xs">
        <div className="flex items-center space-x-2 text-slate-400">
          <Shield className="w-4 h-4 text-sky-400" />
          <span>Simulación de Rol Operativo:</span>
        </div>
        <div className="flex items-center space-x-2">
          {(['ANALISTA', 'AUDITOR', 'ADMINISTRADOR'] as UserRole[]).map((r) => (
            <button
              key={r}
              data-testid={`role-btn-${r.toLowerCase()}`}
              onClick={() => setActiveRole(r)}
              className={`px-2.5 py-1 rounded font-semibold transition-colors ${
                activeRole === r
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-800/40'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Header Actions */}
      <CaseActionsHeader
        detail={caseDetail}
        userRole={activeRole}
        onAssign={async () => {
          await assignMutation.mutateAsync();
        }}
        onResolve={async (resolution, note) => {
          await resolveMutation.mutateAsync({ resolution, note });
        }}
        isAssigning={assignMutation.isPending}
        isResolving={resolveMutation.isPending}
      />

      {/* Main Grid: Transaction & Explanation */}
      <div className="grid grid-cols-1 gap-6">
        {/* Transaction Data */}
        <TransactionCard detail={caseDetail} />

        {/* Case Explanation */}
        {caseDetail.explanation && (
          <CaseExplanationCard explanation={caseDetail.explanation} />
        )}

        {/* Audit Trail */}
        <AuditTrailCard events={caseDetail.auditTrail || []} />
      </div>
    </div>
  );
}
