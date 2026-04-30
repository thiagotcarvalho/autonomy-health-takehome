import type {
  AIAssistResponse,
  CohortReport,
  PatientListItem,
  PatientView,
} from '@/lib/types';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (body && typeof body.detail === 'string') {
      return body.detail;
    }
  } catch {
    // Fall through to status text if the body is not JSON.
  }
  return response.statusText || `HTTP ${response.status}`;
}

async function request<T>(
  path: string,
  signal?: AbortSignal,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {...init, signal});
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

export function formatErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.status}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unknown error';
}

export function listPatients(signal?: AbortSignal): Promise<PatientListItem[]> {
  return request<PatientListItem[]>('/api/patients', signal);
}

export function getPatient(
  patientId: string,
  signal?: AbortSignal,
): Promise<PatientView> {
  return request<PatientView>(
    `/api/patients/${encodeURIComponent(patientId)}`,
    signal,
  );
}

export function getCohortReport(signal?: AbortSignal): Promise<CohortReport> {
  return request<CohortReport>('/api/cohort/report', signal);
}

export function requestAIAssist(
  patientId: string,
  signal?: AbortSignal,
): Promise<AIAssistResponse> {
  return request<AIAssistResponse>(
    `/api/patients/${encodeURIComponent(patientId)}/ai-assist`,
    signal,
    {method: 'POST'},
  );
}
