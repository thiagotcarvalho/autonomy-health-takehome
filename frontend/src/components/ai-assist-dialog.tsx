import {AlertTriangle, Loader2, Sparkles} from 'lucide-react';
import {useEffect, useState} from 'react';

import {
  CHECK_STATUS_LABELS,
  STATUS_LABELS,
  StatusBadge,
} from '@/components/eligibility-status';
import {ResourceRef} from '@/components/resource-ref';
import {Button} from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {Separator} from '@/components/ui/separator';
import {
  formatErrorMessage,
  isAbortError,
  requestAIAssist,
} from '@/lib/api';
import type {
  AICheckResult,
  AIAssistResponse,
  LoadState,
  Reconciliation,
} from '@/lib/types';

interface AIAssistDialogProps {
  patientId: string;
}

function ReconciliationBanner({
  reconciliation,
}: {
  reconciliation: Reconciliation;
}) {
  const hasIssue =
    !reconciliation.verdict_agrees ||
    reconciliation.check_disagreements.length > 0 ||
    reconciliation.hallucinated_evidence.length > 0;
  if (!hasIssue) return null;

  return (
    <div className="rounded-md border border-amber-500/40 bg-amber-50 dark:bg-amber-900/20 p-3 text-sm space-y-2">
      <div className="flex items-center gap-2 font-medium text-amber-900 dark:text-amber-200">
        <AlertTriangle className="h-4 w-4" />
        AI assessment differs from the deterministic verdict
      </div>
      {!reconciliation.verdict_agrees && (
        <p className="text-amber-900 dark:text-amber-200">
          AI suggested{' '}
          <span className="font-semibold">
            {STATUS_LABELS[reconciliation.ai_status]}
          </span>
          ; deterministic says{' '}
          <span className="font-semibold">
            {STATUS_LABELS[reconciliation.deterministic_status]}
          </span>
          . The deterministic verdict is authoritative.
        </p>
      )}
      {reconciliation.check_disagreements.length > 0 && (
        <div>
          <p className="font-medium">Per-check mismatches:</p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            {reconciliation.check_disagreements.map((disagreement) => (
              <li key={disagreement.requirement}>
                <span className="font-medium">{disagreement.requirement}:</span>{' '}
                AI said{' '}
                {CHECK_STATUS_LABELS[disagreement.ai_status].toLowerCase()},
                deterministic says{' '}
                {CHECK_STATUS_LABELS[
                  disagreement.deterministic_status
                ].toLowerCase()}
                .
              </li>
            ))}
          </ul>
        </div>
      )}
      {reconciliation.hallucinated_evidence.length > 0 && (
        <div>
          <p className="font-medium">
            Cited resources not in the patient's data:
          </p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5 font-mono text-xs">
            {reconciliation.hallucinated_evidence.map((evidenceId) => (
              <li key={evidenceId}>{evidenceId}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AICheckRow({check}: {check: AICheckResult}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">{check.requirement}</span>
        <StatusBadge
          status={check.status}
          label={CHECK_STATUS_LABELS[check.status]}
        />
      </div>
      <p className="text-sm text-muted-foreground">{check.reason}</p>
      {check.evidence.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {check.evidence.map((evidenceId) => (
            <ResourceRef
              key={evidenceId}
              id={evidenceId}
              showType
              className="bg-muted/50 px-1.5 py-0.5"
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ResultPanel({result}: {result: AIAssistResponse}) {
  const {ai, reconciliation} = result;
  return (
    <div className="space-y-4">
      <ReconciliationBanner reconciliation={reconciliation} />

      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">AI verdict</span>
        <StatusBadge
          status={ai.status}
          label={STATUS_LABELS[ai.status]}
          className="text-sm h-6 px-3"
        />
      </div>
      <p className="text-sm text-muted-foreground">{ai.reasoning}</p>

      <Separator />

      <div className="space-y-4">
        {ai.checks.map((check, index) => (
          <div key={`${index}-${check.requirement}`} className="space-y-4">
            {index > 0 && <Separator />}
            <AICheckRow check={check} />
          </div>
        ))}
      </div>
    </div>
  );
}

function LoadingPanel() {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground text-sm">
      <Loader2 className="h-4 w-4 animate-spin" />
      Generating AI review...
    </div>
  );
}

function ErrorPanel({message}: {message: string}) {
  return (
    <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm space-y-2">
      <div className="flex items-center gap-2 font-medium text-destructive">
        <AlertTriangle className="h-4 w-4" />
        AI Assist failed
      </div>
      <p className="text-destructive">{message}</p>
      <p className="text-muted-foreground">
        The deterministic verdict on the main page is still authoritative.
      </p>
    </div>
  );
}

export function AIAssistDialog({patientId}: AIAssistDialogProps) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<LoadState<AIAssistResponse> | null>(null);

  useEffect(() => {
    if (!open) {
      setState(null);
      return;
    }
    setState({status: 'loading'});
    const abortController = new AbortController();
    requestAIAssist(patientId, abortController.signal)
      .then((data) => setState({status: 'ready', data}))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        setState({status: 'error', message: formatErrorMessage(error)});
      });
    return () => abortController.abort();
  }, [open, patientId]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Sparkles className="h-3.5 w-3.5" />
          AI Assist
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>AI Eligibility Review</DialogTitle>
          <DialogDescription>
            Model-grounded review of this patient's eligibility, reconciled
            against the deterministic verdict.
          </DialogDescription>
        </DialogHeader>
        <div role="status" aria-live="polite" aria-busy={state?.status === 'loading'}>
          {state?.status === 'loading' && <LoadingPanel />}
          {state?.status === 'error' && <ErrorPanel message={state.message} />}
          {state?.status === 'ready' && <ResultPanel result={state.data} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}
