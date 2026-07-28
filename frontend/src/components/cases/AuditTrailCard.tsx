import React from 'react';
import { formatDateTime } from '@/lib/utils/format';
import { History, User, Clock } from 'lucide-react';

interface AuditTrailCardProps {
  events: Record<string, unknown>[];
}

export function AuditTrailCard({ events = [] }: AuditTrailCardProps) {
  // Ensure events are sorted in chronological order
  const sortedEvents = [...events].sort((a: Record<string, unknown>, b: Record<string, unknown>) => {
    const timeA = new Date(String(a.fecha_registro || a.timestamp || a.created_at || 0)).getTime();
    const timeB = new Date(String(b.fecha_registro || b.timestamp || b.created_at || 0)).getTime();
    return timeA - timeB;
  });

  return (
    <div
      data-testid="audit-trail-card"
      className="p-6 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl space-y-4"
    >
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2 text-indigo-400">
          <History className="w-5 h-5" />
          <h3 className="text-base font-semibold text-slate-100">Traza de Auditoría Inmutable</h3>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          {events.length} Eventos Registrados
        </span>
      </div>

      {sortedEvents.length === 0 ? (
        <p className="text-sm text-slate-400 italic p-4 text-center">
          No hay eventos de auditoría registrados.
        </p>
      ) : (
        <div data-testid="audit-trail-list" className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
          {sortedEvents.map((event: Record<string, unknown>, idx) => {
            const timestamp = String(event.fecha_registro || event.timestamp || event.created_at || '');
            const actor = String(event.usuario_accion || event.actor || 'Sistema');
            const action = String(event.accion || event.action || 'EVENTO');
            const details = event.estado_nuevo || event.details || event.data;
            const entidad: string | null = event.entidad ? String(event.entidad) : null;
            const eventId = (event.id as string | number) || idx;

            return (
              <div
                key={eventId}
                data-testid={`audit-event-${idx}`}
                className="relative group space-y-1.5"
              >
                {/* Bullet node */}
                <div className="absolute -left-6 top-1.5 w-3 h-3 rounded-full bg-indigo-500 ring-4 ring-slate-900 group-hover:scale-125 transition-transform" />

                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 text-xs font-mono font-semibold rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {action}
                    </span>
                    <span className="text-xs font-medium text-slate-300 flex items-center space-x-1">
                      <User className="w-3 h-3 text-slate-400" />
                      <span>{actor}</span>
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono flex items-center space-x-1">
                    <Clock className="w-3 h-3 text-slate-500" />
                    <span>{timestamp ? formatDateTime(timestamp) : '-'}</span>
                  </span>
                </div>

                {entidad ? (
                  <p className="text-xs text-slate-400">
                    Entidad afectada: <span className="font-mono text-slate-300">{entidad}</span>
                  </p>
                ) : null}

                {Boolean(details) && typeof details === 'object' && Object.keys(details as object).length > 0 ? (
                  <div className="mt-1 p-2.5 rounded bg-slate-950/60 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto">
                    <pre className="text-[11px] leading-tight">
                      {JSON.stringify(details, null, 2)}
                    </pre>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
