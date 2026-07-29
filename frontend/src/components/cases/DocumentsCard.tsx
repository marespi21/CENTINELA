"use client";

import { useQuery } from "@tanstack/react-query";
import { ExternalLink, FileText, Paperclip } from "lucide-react";

import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { listCaseDocuments } from "@/lib/api/client";
import { queryKeys } from "@/lib/query/keys";

interface DocumentsCardProps {
  caseId: string;
}

export function DocumentsCard({ caseId }: DocumentsCardProps) {
  const query = useQuery({
    queryKey: queryKeys.cases.documents(caseId),
    queryFn: () => listCaseDocuments(caseId),
    retry: false,
  });

  return (
    <section
      data-testid="documents-card"
      className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur-md"
    >
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2 text-cyan-400">
          <Paperclip className="h-5 w-5" aria-hidden="true" />
          <h3 className="text-base font-semibold text-slate-100">Documentos adjuntos</h3>
        </div>
        {query.data ? (
          <span className="font-mono text-xs text-slate-400">
            {query.data.items.length} documentos
          </span>
        ) : null}
      </div>

      {query.isLoading ? <LoadingState label="Cargando documentos…" className="py-8" /> : null}

      {query.isError ? (
        <ErrorState
          title="No se pudieron cargar los documentos"
          message={query.error instanceof Error ? query.error.message : "Error desconocido."}
          onRetry={() => void query.refetch()}
          className="py-8"
        />
      ) : null}

      {query.isSuccess && query.data.items.length === 0 ? (
        <EmptyState title="Este caso no tiene documentos adjuntos" className="py-8" />
      ) : null}

      {query.isSuccess && query.data.items.length > 0 ? (
        <ul role="list" className="space-y-3">
          {query.data.items.map((document) => (
            <li
              key={document.blobName}
              role="listitem"
              className="flex flex-col gap-3 rounded-lg border border-slate-800/80 bg-slate-950/50 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex min-w-0 items-center gap-3">
                <FileText className="h-5 w-5 shrink-0 text-cyan-400" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-100">{document.filename}</p>
                  <p className="mt-0.5 text-xs text-slate-400">{document.contentType}</p>
                </div>
              </div>
              <a
                href={document.url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Abrir documento ${document.filename} en una nueva pestaña`}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-300 transition-colors hover:bg-cyan-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              >
                Abrir documento
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
