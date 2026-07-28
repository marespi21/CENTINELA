import Link from "next/link";

interface CaseDetailPlaceholderProps {
  params: Promise<{ caseId: string }>;
}

/**
 * Placeholder del detalle (HU posteriores: explicación, documentos, acciones).
 * Cumple el criterio de navegación desde la bandeja.
 */
export default async function CaseDetailPage({
  params,
}: CaseDetailPlaceholderProps) {
  const { caseId } = await params;

  return (
    <div className="animate-fade-up space-y-6">
      <Link
        href="/cases"
        className="inline-flex text-sm font-medium text-[var(--accent-ink)] hover:underline"
      >
        ← Volver a la bandeja
      </Link>

      <header className="space-y-2">
        <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">
          Detalle
        </p>
        <h1 className="font-display text-3xl tracking-tight text-[var(--ink)]">
          Caso {caseId}
        </h1>
        <p className="max-w-2xl text-sm text-[var(--muted)] sm:text-base">
          La pantalla completa de detalle (explicación, documentos y acciones)
          se entrega en las historias siguientes. El BFF{" "}
          <code className="font-mono text-[13px]">/api/cases/{caseId}</code> ya
          está listo para consumir{" "}
          <code className="font-mono text-[13px]">CaseDetailDto</code>.
        </p>
      </header>

      <section className="panel p-6">
        <p className="text-sm text-[var(--muted)]">
          Identificador:{" "}
          <span className="font-mono text-[var(--ink)]">{caseId}</span>
        </p>
      </section>
    </div>
  );
}
