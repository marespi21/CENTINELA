import React from 'react';
import { CaseDetailView } from '@/components/cases/CaseDetailView';

interface CasePageProps {
  params: Promise<{ caseId: string }>;
}

export default async function CaseDetailPage({ params }: CasePageProps) {
  const resolvedParams = await params;
  return <CaseDetailView caseId={resolvedParams.caseId} />;
}
