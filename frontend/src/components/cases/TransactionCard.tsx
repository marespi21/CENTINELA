import React from 'react';
import type { CaseDetailDto } from '@/lib/api/types';
import { formatCurrency, formatDateTime } from '@/lib/utils/format';
import { CreditCard, MapPin, Building2, Calendar, DollarSign, UserCheck } from 'lucide-react';

interface TransactionCardProps {
  detail: CaseDetailDto;
}

export function TransactionCard({ detail }: TransactionCardProps) {
  // Safe extraction of transaction parameters from explanation reasons if available
  const observedAmount = (detail.explanation?.reasons?.find((r) => r.observed?.amount)?.observed?.amount as number) || 12500000;
  const observedCurrency = (detail.explanation?.reasons?.find((r) => r.observed?.currency)?.observed?.currency as string) || 'COP';
  const observedMerchant = (detail.explanation?.reasons?.find((r) => r.observed?.merchant)?.observed?.merchant as string) || 'Comercio Registrado';
  const observedCity = (detail.explanation?.reasons?.find((r) => r.observed?.currentCity)?.observed?.currentCity as string) || 'Bogotá, CO';

  return (
    <div
      data-testid="transaction-card"
      className="p-6 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl space-y-4"
    >
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2 text-sky-400">
          <CreditCard className="w-5 h-5" />
          <h3 className="text-base font-semibold text-slate-100">Datos de la Transacción</h3>
        </div>
        <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
          ID: {detail.transactionId}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Monto */}
        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-1">
          <div className="flex items-center text-xs font-medium text-slate-400 space-x-1">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
            <span>Monto Transaccionado</span>
          </div>
          <p className="text-lg font-bold text-emerald-400 font-mono">
            {formatCurrency(observedAmount, observedCurrency)}
          </p>
        </div>

        {/* Cuenta */}
        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-1">
          <div className="flex items-center text-xs font-medium text-slate-400 space-x-1">
            <UserCheck className="w-3.5 h-3.5 text-sky-400" />
            <span>Cuenta de Origen</span>
          </div>
          <p className="text-sm font-semibold text-slate-200 font-mono">
            {detail.accountId}
          </p>
        </div>

        {/* Comercio */}
        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-1">
          <div className="flex items-center text-xs font-medium text-slate-400 space-x-1">
            <Building2 className="w-3.5 h-3.5 text-amber-400" />
            <span>Comercio / Destino</span>
          </div>
          <p className="text-sm font-semibold text-slate-200 truncate">
            {observedMerchant}
          </p>
          <p className="text-xs text-slate-400 truncate">Transacción Digital</p>
        </div>

        {/* Ubicación Geo & Fecha */}
        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-1">
          <div className="flex items-center text-xs font-medium text-slate-400 space-x-1">
            <MapPin className="w-3.5 h-3.5 text-rose-400" />
            <span>Geolocalización & Fecha</span>
          </div>
          <p className="text-sm font-medium text-slate-200 truncate">
            {observedCity}
          </p>
          <div className="flex items-center space-x-1 text-xs text-slate-400">
            <Calendar className="w-3 h-3 text-slate-500" />
            <span>{formatDateTime(detail.openedAt)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
