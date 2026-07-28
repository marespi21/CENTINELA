import Link from "next/link";

interface CaseDetailPlaceholderProps {
  params: Promise<{ caseId: string }>;
}

export default async function CaseDetailPage({
  params,
}: CaseDetailPlaceholderProps) {
  const { caseId } = await params;

  return (
    <div className="animate-fade-up space-y-6">
      <Link
        href="/cases"
        className="inline-flex text-sm font-semibold text-[var(--accent)] hover:underline"
      >
        ← Volver a la bandeja
      </Link>

      <header className="space-y-2">
        <p className="text-sm font-medium text-[var(--accent)]">Detalle</p>
        <h1 className="font-display text-4xl font-semibold text-[var(--ink)]">
          Caso en revisión
        </h1>
        <p className="max-w-2xl text-[15px] text-[var(--muted)]">
          La vista completa llega en las siguientes historias. El BFF de detalle
          ya está listo.
        </p>
      </header>

      <section className="panel p-6">
        <p className="text-xs font-medium text-[var(--muted)]">Identificador</p>
        <p className="mt-1 font-mono text-lg font-medium text-[var(--ink)]">{caseId}</p>
      </section>
    </div>
  );
}
