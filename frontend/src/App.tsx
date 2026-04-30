import {ArrowLeft} from 'lucide-react';
import {useEffect, useState} from 'react';

import {ClinicalSnapshotCard} from '@/components/clinical-snapshot';
import {CohortReportCard} from '@/components/cohort-report';
import {EligibilityCard} from '@/components/eligibility-card';
import {PatientSelector} from '@/components/patient-selector';
import {TimelineCard} from '@/components/timeline';
import {Button} from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  ApiError,
  getCohortReport,
  getPatient,
  listPatients,
} from '@/lib/api';
import type {
  CohortReport,
  PatientListItem,
  PatientView,
} from '@/lib/types';

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

function CohortLoadingView() {
  return (
    <Card>
      <CardContent className="py-8 text-muted-foreground text-sm">
        Loading cohort report...
      </CardContent>
    </Card>
  );
}

function CohortErrorView({message}: {message: string}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-destructive">
          Failed to load cohort report
        </CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
    </Card>
  );
}

function PatientLoadingView() {
  return (
    <Card>
      <CardContent className="py-8 text-muted-foreground text-sm">
        Loading patient...
      </CardContent>
    </Card>
  );
}

function PatientErrorView({message}: {message: string}) {
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

function PatientReview({view}: {view: PatientView}) {
  return (
    <div className="space-y-6">
      <ClinicalSnapshotCard snapshot={view.snapshot} />
      <EligibilityCard eligibility={view.eligibility} />
      <TimelineCard entries={view.timeline} />
    </div>
  );
}

function App() {
  const [patients, setPatients] = useState<LoadState<PatientListItem[]>>({
    status: 'loading',
  });
  const [cohort, setCohort] = useState<LoadState<CohortReport>>({
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
    const abortController = new AbortController();
    getCohortReport(abortController.signal)
      .then((data) => setCohort({status: 'ready', data}))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        setCohort({status: 'error', message: formatErrorMessage(error)});
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
          <div className="ml-auto flex items-center gap-3">
            {selectedId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedId(null)}
              >
                <ArrowLeft className="mr-1 h-4 w-4" />
                Cohort report
              </Button>
            )}
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
        {!selectedId && cohort.status === 'loading' && <CohortLoadingView />}
        {!selectedId && cohort.status === 'error' && (
          <CohortErrorView message={cohort.message} />
        )}
        {!selectedId && cohort.status === 'ready' && (
          <CohortReportCard report={cohort.data} />
        )}
        {selectedId && patientView?.status === 'loading' && (
          <PatientLoadingView />
        )}
        {selectedId && patientView?.status === 'error' && (
          <PatientErrorView message={patientView.message} />
        )}
        {selectedId && patientView?.status === 'ready' && (
          <PatientReview view={patientView.data} />
        )}
      </main>
    </div>
  );
}

export default App;
