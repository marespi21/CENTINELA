'use client';

import React, { useState } from 'react';
import type { CaseDetailDto } from '@/lib/api/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { UserCheck, CheckCircle2, AlertCircle, X, Loader2, ArrowLeft, Shield } from 'lucide-react';
import Link from 'next/link';

export type UserRole = 'ANALISTA' | 'AUDITOR' | 'ADMINISTRADOR';

interface CaseActionsHeaderProps {
  detail: CaseDetailDto;
  userRole?: UserRole;
  onAssign: () => Promise<void>;
  onResolve: (resolution: string, note?: string) => Promise<void>;
  isAssigning?: boolean;
  isResolving?: boolean;
}

export function CaseActionsHeader({
  detail,
  userRole = 'ANALISTA',
  onAssign,
  onResolve,
  isAssigning = false,
  isResolving = false,
}: CaseActionsHeaderProps) {
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [resolution, setResolution] = useState('FRAUDE_CONFIRMADO');
  const [note, setNote] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const statusNormalized = (detail.status || '').toLowerCase();
  const isResolved = statusNormalized === 'resuelto' || statusNormalized === 'cerrado';
  const isAuditor = userRole === 'AUDITOR';
  const canAct = !isResolved && !isAuditor;

  const handleAssignClick = async () => {
    try {
      setFeedback(null);
      await onAssign();
      setFeedback({ type: 'success', message: '¡Caso asignado con éxito!' });
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Ocurrió un error al procesar la solicitud.',
      });
    }
  };

  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolution) return;

    try {
      setFeedback(null);
      await onResolve(resolution, note);
      setShowResolveModal(false);
      setFeedback({ type: 'success', message: '¡Caso resuelto con éxito!' });
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Ocurrió un error al resolver el caso.',
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Navigation & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-xl border border-slate-800 bg-slate-900/80 backdrop-blur-md shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <Link
              href="/cases"
              aria-label="Volver a la bandeja"
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h1 className="text-xl font-extrabold text-slate-100 font-mono tracking-tight">
              Caso: {detail.caseId}
            </h1>
            <StatusBadge status={detail.status} />
          </div>
          <p className="text-xs text-slate-400">
            Asignado a: {' '}
            <strong className="text-slate-200 font-mono">
              {detail.assignedTo || 'Sin asignar'}
            </strong>{' '}
            | Rol activo: <span className="text-sky-400 font-semibold">{userRole}</span>
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center space-x-3">
          {/* Asignarme Button */}
          <button
            data-testid="btn-asignarme"
            onClick={handleAssignClick}
            disabled={!canAct || isAssigning}
            className="inline-flex items-center space-x-2 px-4 py-2 text-sm font-semibold rounded-lg border transition-all duration-200 shadow-md disabled:opacity-50 disabled:cursor-not-allowed bg-sky-600 hover:bg-sky-500 text-white border-sky-500 shadow-sky-950/40"
          >
            {isAssigning ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <UserCheck className="w-4 h-4" />
            )}
            <span>Asignarme</span>
          </button>

          {/* Resolver Button */}
          <button
            data-testid="btn-resolver"
            onClick={() => setShowResolveModal(true)}
            disabled={!canAct || isResolving}
            className="inline-flex items-center space-x-2 px-4 py-2 text-sm font-semibold rounded-lg border transition-all duration-200 shadow-md disabled:opacity-50 disabled:cursor-not-allowed bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500 shadow-emerald-950/40"
          >
            {isResolving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            <span>Resolver</span>
          </button>
        </div>
      </div>

      {/* Disabling notice for Auditor role */}
      {isAuditor && (
        <div data-testid="auditor-notice" className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/10 text-amber-300 text-xs flex items-center space-x-2">
          <Shield className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            Tu usuario posee el rol de <strong>Auditor (Solo Lectura)</strong>. Las acciones de asignar y resolver se encuentran deshabilitadas.
          </span>
        </div>
      )}

      {/* Disabling notice for Resolved status */}
      {isResolved && !isAuditor && (
        <div data-testid="resolved-notice" className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>
            Este caso ya se encuentra <strong>RESUELTO</strong>. No es posible realizar modificaciones adicionales.
          </span>
        </div>
      )}

      {/* Toast Feedback */}
      {feedback && (
        <div
          data-testid="action-feedback"
          className={`p-3 rounded-lg border text-sm flex items-center justify-between transition-all ${
            feedback.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center space-x-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="p-1 text-slate-400 hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Resolution Modal */}
      {showResolveModal && (
        <div
          data-testid="resolve-modal"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in"
        >
          <div className="w-full max-w-md p-6 rounded-xl border border-slate-800 bg-slate-900 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span>Resolver Caso {detail.caseId}</span>
              </h3>
              <button
                onClick={() => setShowResolveModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleResolveSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Dictamen / Resolución <span className="text-rose-400">*</span>
                </label>
                <select
                  data-testid="select-resolution"
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-100 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                >
                  <option value="FRAUDE_CONFIRMADO">FRAUDE CONFIRMADO</option>
                  <option value="FALSO_POSITIVO">FALSO POSITIVO</option>
                  <option value="TRANSACCION_CERRADA">TRANSACCIÓN CERRADA</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Nota / Justificación (Opcional)
                </label>
                <textarea
                  data-testid="input-note"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Escriba aquí los detalles del hallazgo o justificación de la decisión..."
                  rows={3}
                  className="w-full p-2.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-100 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowResolveModal(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  data-testid="btn-submit-resolve"
                  disabled={isResolving}
                  className="inline-flex items-center space-x-2 px-4 py-2 text-sm font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-lg shadow-emerald-950/40"
                >
                  {isResolving && <Loader2 className="w-4 h-4 animate-spin" />}
                  <span>Confirmar Resolución</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
