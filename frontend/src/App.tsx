import {useEffect, useState} from 'react';

import {PatientSelector} from '@/components/patient-selector';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {ApiError, getPatient, listPatients} from '@/lib/api';
import type {PatientListItem, PatientView} from '@/lib/types';

type LoadState<T> =
  | {status: 'loading'}
  | {status: 'error'; message: string}
  | {status: 'ready'; data: T};

function formatErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.status}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unknown error';
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function EmptyState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Select a patient</CardTitle>
        <CardDescription>
          Pick a patient from the selector above to review their snapshot,
          timeline, and eligibility verdict.
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

function LoadingView() {
  return (
    <Card>
      <CardContent className="py-8 text-muted-foreground text-sm">
        Loading patient...
      </CardContent>
    </Card>
  );
}

function ErrorView({message}: {message: string}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-destructive">
          Failed to load patient
        </CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
    </Card>
  );
}

function PatientPlaceholder({view}: {view: PatientView}) {
  const {snapshot, timeline, eligibility} = view;
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {snapshot.given_name} {snapshot.family_name}
        </CardTitle>
        <CardDescription className="font-mono text-xs">
          {snapshot.patient_id}
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        <p>
          Eligibility:{' '}
          <span className="font-medium text-foreground">
            {eligibility.status}
          </span>{' '}
          ({eligibility.checks.length} checks)
        </p>
        <p>
          Active conditions: {snapshot.active_conditions.length} · Recent
          procedures: {snapshot.recent_procedures.length} · Timeline entries:{' '}
          {timeline.length}
        </p>
      </CardContent>
    </Card>
  );
}

function App() {
  const [patients, setPatients] = useState<LoadState<PatientListItem[]>>({
    status: 'loading',
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [patientView, setPatientView] =
    useState<LoadState<PatientView> | null>(null);

  useEffect(() => {
    const abortController = new AbortController();
    listPatients(abortController.signal)
      .then((data) => setPatients({status: 'ready', data}))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        setPatients({status: 'error', message: formatErrorMessage(error)});
      });
    return () => abortController.abort();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setPatientView(null);
      return;
    }
    setPatientView({status: 'loading'});
    const abortController = new AbortController();
    getPatient(selectedId, abortController.signal)
      .then((data) => setPatientView({status: 'ready', data}))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        setPatientView({status: 'error', message: formatErrorMessage(error)});
      });
    return () => abortController.abort();
  }, [selectedId]);

  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto max-w-5xl px-6 py-4 flex items-center gap-4">
          <h1 className="text-lg font-semibold tracking-tight">
            FHIR Prior Authorization Review
          </h1>
          <div className="ml-auto">
            {patients.status === 'loading' && (
              <span className="text-muted-foreground text-sm">
                Loading patients...
              </span>
            )}
            {patients.status === 'error' && (
              <span className="text-destructive text-sm">
                Failed to load patients: {patients.message}
              </span>
            )}
            {patients.status === 'ready' && (
              <PatientSelector
                patients={patients.data}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {!selectedId && <EmptyState />}
        {selectedId && patientView?.status === 'loading' && <LoadingView />}
        {selectedId && patientView?.status === 'error' && (
          <ErrorView message={patientView.message} />
        )}
        {patientView?.status === 'ready' && (
          <PatientPlaceholder view={patientView.data} />
        )}
      </main>
    </div>
  );
}

export default App;
