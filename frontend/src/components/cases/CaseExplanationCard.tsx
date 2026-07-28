import React from 'react';
import type { ExplanationDto } from '@/lib/api/types';
import { ShieldAlert, ShieldCheck, AlertCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

interface CaseExplanationCardProps {
  explanation: ExplanationDto;
}

export function CaseExplanationCard({ explanation }: CaseExplanationCardProps) {
  const { score, threshold, isCase, summary, reasons = [] } = explanation;

  const scoreColor =
    score >= 70
      ? 'text-rose-400 bg-rose-500/10 border-rose-500/30'
      : score >= 40
      ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
      : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';

  return (
    <div
      data-testid="explanation-card"
      className="p-6 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl space-y-6"
    >
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2 text-cyan-400">
          <ShieldAlert className="w-5 h-5" />
          <h3 className="text-base font-semibold text-slate-100">Explicación del Caso & Scoring</h3>
        </div>
        <div className="flex items-center space-x-3">
          {/* Badge isCase */}
          <span
            data-testid="is-case-badge"
            className={cn(
              'px-3 py-1 text-xs font-bold rounded-full border shadow-sm flex items-center space-x-1.5',
              isCase
                ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
            )}
          >
            {isCase ? <ShieldAlert className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
            <span>{isCase ? 'Caso Fraudulento Confirmado' : 'Sin Alerta Crítica'}</span>
          </span>
        </div>
      </div>

      {/* Score & Summary Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Gauge Score */}
        <div className={cn('p-5 rounded-xl border flex flex-col justify-center items-center text-center space-y-2', scoreColor)}>
          <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
            Score de Riesgo
          </span>
          <div className="text-4xl font-extrabold font-mono tracking-tight">
            {score}
            <span className="text-sm font-normal text-slate-400">/100</span>
          </div>
          <span className="text-xs font-medium text-slate-300">
            Umbral de activación: <strong className="text-slate-100">{threshold} pts</strong>
          </span>
        </div>

        {/* Resumen explicativo */}
        <div className="lg:col-span-2 p-5 rounded-xl border border-slate-800 bg-slate-950/40 space-y-2 flex flex-col justify-center">
          <div className="flex items-center space-x-2 text-amber-400 text-xs font-semibold uppercase tracking-wide">
            <Info className="w-4 h-4" />
            <span>Resumen del Análisis</span>
          </div>
          <p data-testid="explanation-summary" className="text-sm text-slate-200 leading-relaxed font-medium">
            {summary || 'El motor de reglas determinó anomalías en la transacción.'}
          </p>
        </div>
      </div>

      {/* Lista de Razones Detalladas */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-slate-300 flex items-center space-x-1.5">
          <AlertCircle className="w-4 h-4 text-cyan-400" />
          <span>Reglas Disparadas ({reasons.length})</span>
        </h4>

        {reasons.length === 0 ? (
          <p className="text-sm text-slate-400 italic">No se registraron reglas con puntaje positivo.</p>
        ) : (
          <div data-testid="reasons-list" className="space-y-3">
            {reasons.map((reason, idx) => (
              <div
                key={reason.ruleId || idx}
                data-testid={`reason-item-${reason.ruleId}`}
                className="p-4 rounded-lg border border-slate-800/80 bg-slate-950/50 hover:border-slate-700 transition-all space-y-2"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                      {reason.ruleId}
                    </span>
                    <h5 className="text-sm font-bold text-slate-100">{reason.title}</h5>
                  </div>
                  <span className="px-2.5 py-0.5 text-xs font-mono font-bold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    +{reason.points} pts
                  </span>
                </div>

                <p className="text-xs text-slate-300">{reason.description}</p>

                {reason.detail && (
                  <p className="text-xs text-slate-400 font-mono bg-slate-900/80 p-2 rounded border border-slate-800">
                    {reason.detail}
                  </p>
                )}

                {/* Datos observados */}
                {reason.observed && Object.keys(reason.observed).length > 0 && (
                  <div className="pt-2 border-t border-slate-800/60 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    {Object.entries(reason.observed).map(([key, val]) => (
                      <div key={key} className="bg-slate-900/40 p-1.5 rounded border border-slate-800/40">
                        <span className="text-slate-400 font-mono block text-[10px]">{key}:</span>
                        <span className="text-slate-200 font-semibold truncate block">
                          {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
