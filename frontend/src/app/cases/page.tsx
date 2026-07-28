import { Suspense } from "react";

import { CasesInbox } from "@/components/cases/CasesInbox";
import { LoadingState } from "@/components/ui/LoadingState";

export const metadata = {
  title: "Bandeja de casos",
};

export default function CasesPage() {
  return (
    <Suspense fallback={<LoadingState label="Preparando bandeja…" />}>
      <CasesInbox />
    </Suspense>
  );
}
