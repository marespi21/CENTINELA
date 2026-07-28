import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CaseDetailView } from './CaseDetailView';
import * as client from '@/lib/api/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { CaseDetailDto } from '@/lib/api/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return {
    ...actual,
    getCase: vi.fn(),
    assignCase: vi.fn(),
    resolveCase: vi.fn(),
  };
});

const mockDetail: CaseDetailDto = {
  caseId: 'CAS-2026-0042',
  transactionId: 'TX-998811',
  accountId: 'ACC-55102',
  status: 'Abierto',
  openedAt: '2026-07-28T10:15:00Z',
  assignedTo: null,
  explanation: {
    transactionId: 'TX-998811',
    accountId: 'ACC-55102',
    score: 85,
    threshold: 70,
    isCase: true,
    summary: 'Riesgo Alto: Múltiples transacciones en comercios inusuales.',
    generatedAt: '2026-07-28T10:15:00Z',
    reasons: [
      {
        ruleId: 'GEO_IMPOSSIBLE',
        title: 'Ubicación Geográfica Imposible',
        description: 'Dos transacciones registradas en ciudades distintas.',
        detail: 'Distancia: 11,000 km en 15 minutos.',
        points: 50,
        observed: { lastCity: 'Bogotá', currentCity: 'Tokyo', amount: 12500000 },
      },
    ],
  },
  auditTrail: [
    {
      id: 1,
      entidad: 'casos',
      caso_id: 'CAS-2026-0042',
      accion: 'CREACION_CASO',
      usuario_accion: 'SISTEMA_SCORING',
      fecha_registro: '2026-07-28T10:15:00Z',
    },
  ],
};

const mockAssignedDetail: CaseDetailDto = {
  ...mockDetail,
  status: 'En Investigacion',
  assignedTo: 'analista.juanjo',
};

const mockResolvedDetail: CaseDetailDto = {
  ...mockDetail,
  status: 'Resuelto',
  assignedTo: 'analista.juanjo',
};

function renderWithClient(ui: React.ReactElement) {
  const testQueryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={testQueryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('CaseDetailView (HU-03 / Camila Base Integration)', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders case detail with transaction data, explanation, score, reasons and audit trail', async () => {
    vi.mocked(client.getCase).mockResolvedValue(mockDetail);

    renderWithClient(<CaseDetailView caseId="CAS-2026-0042" initialData={mockDetail} />);

    expect(screen.getByText(/Caso: CAS-2026-0042/i)).toBeInTheDocument();
    expect(screen.getByTestId('transaction-card')).toBeInTheDocument();
    expect(screen.getByText(/ACC-55102/i)).toBeInTheDocument();

    expect(screen.getByTestId('explanation-card')).toBeInTheDocument();
    expect(screen.getByTestId('is-case-badge')).toHaveTextContent(/Caso Fraudulento Confirmado/i);
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByTestId('explanation-summary')).toHaveTextContent(
      /Riesgo Alto: Múltiples transacciones/i
    );

    expect(screen.getByTestId('reasons-list')).toBeInTheDocument();
    expect(screen.getByText('GEO_IMPOSSIBLE')).toBeInTheDocument();
    expect(screen.getByText('Ubicación Geográfica Imposible')).toBeInTheDocument();

    expect(screen.getByTestId('audit-trail-card')).toBeInTheDocument();
    expect(screen.getByText('CREACION_CASO')).toBeInTheDocument();
  });

  it('executes "asignarme" action and calls BFF API endpoint', async () => {
    vi.mocked(client.getCase).mockResolvedValue(mockDetail);
    vi.mocked(client.assignCase).mockResolvedValue(mockAssignedDetail);

    renderWithClient(<CaseDetailView caseId="CAS-2026-0042" initialData={mockDetail} />);

    const assignBtn = screen.getAllByTestId('btn-asignarme')[0];
    expect(assignBtn).not.toBeDisabled();

    fireEvent.click(assignBtn);

    await waitFor(() => {
      expect(client.assignCase).toHaveBeenCalledWith('CAS-2026-0042', { assigneeId: 'analista.juanjo' });
    });

    await waitFor(() => {
      expect(screen.getByTestId('action-feedback')).toHaveTextContent(/Caso asignado con éxito/i);
    });
  });

  it('executes "resolver" action with modal input and calls BFF API endpoint', async () => {
    vi.mocked(client.getCase).mockResolvedValue(mockAssignedDetail);
    vi.mocked(client.resolveCase).mockResolvedValue(mockResolvedDetail);

    renderWithClient(<CaseDetailView caseId="CAS-2026-0042" initialData={mockAssignedDetail} />);

    const resolveBtn = screen.getAllByTestId('btn-resolver')[0];
    fireEvent.click(resolveBtn);

    expect(screen.getByTestId('resolve-modal')).toBeInTheDocument();

    const noteInput = screen.getByTestId('input-note');
    fireEvent.change(noteInput, { target: { value: 'Confirmado por patrón geo e historial.' } });

    const submitBtn = screen.getByTestId('btn-submit-resolve');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(client.resolveCase).toHaveBeenCalledWith('CAS-2026-0042', {
        resolution: 'FRAUDE_CONFIRMADO',
        note: 'Confirmado por patrón geo e historial.',
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('action-feedback')).toHaveTextContent(/Caso resuelto con éxito/i);
    });
  });

  it('disables actions when user role is AUDITOR', async () => {
    vi.mocked(client.getCase).mockResolvedValue(mockDetail);

    renderWithClient(<CaseDetailView caseId="CAS-2026-0042" initialData={mockDetail} />);

    const auditorBtn = screen.getAllByTestId('role-btn-auditor')[0];
    fireEvent.click(auditorBtn);

    expect(screen.getByTestId('auditor-notice')).toBeInTheDocument();
    expect(screen.getAllByTestId('btn-asignarme')[0]).toBeDisabled();
    expect(screen.getAllByTestId('btn-resolver')[0]).toBeDisabled();
  });

  it('disables actions when case status is Resuelto', async () => {
    vi.mocked(client.getCase).mockResolvedValue(mockResolvedDetail);

    renderWithClient(<CaseDetailView caseId="CAS-2026-0042" initialData={mockResolvedDetail} />);

    expect(screen.getByTestId('resolved-notice')).toBeInTheDocument();
    expect(screen.getAllByTestId('btn-asignarme')[0]).toBeDisabled();
    expect(screen.getAllByTestId('btn-resolver')[0]).toBeDisabled();
  });
});
