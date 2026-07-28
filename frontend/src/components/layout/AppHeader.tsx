import Link from "next/link";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)]/80 bg-[var(--surface)]/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/cases" className="group flex items-center gap-3">
          <span
            aria-hidden
            className="relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-lg bg-[var(--ink)] shadow-sm transition-transform duration-300 group-hover:scale-[1.03]"
          >
            <span className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(45,212,191,0.45),transparent_55%)]" />
            <span className="relative font-mono text-[11px] font-semibold tracking-widest text-teal-100">
              CT
            </span>
          </span>
          <div className="leading-tight">
            <p className="font-display text-lg tracking-tight text-[var(--ink)]">
              CENTINELA
            </p>
            <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">
              Consola del analista
            </p>
          </div>
        </Link>

        <nav className="flex items-center gap-1 text-sm">
          <Link
            href="/cases"
            className="rounded-md px-3 py-1.5 font-medium text-[var(--ink)] transition-colors hover:bg-[var(--surface-muted)]"
          >
            Casos
          </Link>
          <span
            className="hidden rounded-md px-3 py-1.5 text-[var(--muted)] sm:inline"
            title="Autenticación de usuario fuera de alcance en esta historia"
          >
            Analista
          </span>
        </nav>
      </div>
    </header>
  );
}
