import type { ReactNode } from "react";

import { AppHeader } from "./AppHeader";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      >
        <div className="absolute left-1/2 top-0 h-[28rem] w-[44rem] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(37,99,235,0.09),transparent_70%)] blur-2xl" />
      </div>
      <AppHeader />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
    </div>
  );
}
