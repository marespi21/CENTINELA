import React from 'react';
import Link from 'next/link';
import { SearchX, ArrowLeft } from 'lucide-react';

export function NotFoundState({ caseId }: { caseId?: string }) {
  return (
    <div
      data-testid="not-found-state"
      className="flex flex-col items-center justify-center p-12 min-h-[400px] text-center space-y-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md"
    >
      <div className="p-4 bg-amber-500/10 rounded-full border border-amber-500/20 text-amber-400">
        <SearchX className="w-10 h-10" />
      </div>
      <div className="space-y-2 max-w-md">
        <h2 className="text-xl font-bold text-slate-100">Caso No Encontrado (404)</h2>
        <p className="text-sm text-slate-400">
          No se encontró ningún caso registrado con el identificador{' '}
          <code className="text-amber-300 font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">
            {caseId || 'solicitado'}
          </code>
          .
        </p>
      </div>
      <Link
        href="/cases"
        className="inline-flex items-center space-x-2 px-4 py-2 text-sm font-medium text-slate-100 bg-sky-600 hover:bg-sky-500 rounded-lg transition-colors shadow-lg shadow-sky-950/40"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Volver a la Bandeja de Casos</span>
      </Link>
    </div>
  );
}
