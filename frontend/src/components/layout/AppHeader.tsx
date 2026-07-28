import Link from "next/link";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/cases" className="group flex items-center gap-3">
          <span
            aria-hidden
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent)] text-sm font-bold text-white shadow-[0_8px_20px_rgba(37,99,235,0.35)] transition-transform duration-200 group-hover:scale-105"
          >
            C
          </span>
          <div className="leading-none">
            <p className="font-display text-[1.15rem] font-semibold text-[var(--ink)]">
              Centinela
            </p>
            <p className="mt-1 text-[11px] font-medium text-[var(--muted)]">
              Fraud desk
            </p>
          </div>
        </Link>

        <nav className="flex items-center gap-2">
          <Link
            href="/cases"
            className="rounded-full bg-[var(--accent-soft)] px-3.5 py-1.5 text-sm font-semibold text-[var(--accent-ink)]"
          >
            Casos
          </Link>
          <div className="hidden items-center gap-2 rounded-full border border-[var(--border)] bg-white px-3 py-1.5 sm:flex">
            <span className="live-dot" />
            <span className="text-xs font-medium text-[var(--muted)]">En línea</span>
          </div>
        </nav>
      </div>
    </header>
  );
}
