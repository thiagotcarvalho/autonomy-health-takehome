import {AIAssistDialog} from '@/components/ai-assist-dialog';
import {
  CHECK_STATUS_LABELS,
  STATUS_LABELS,
  StatusBadge,
} from '@/components/eligibility-status';
import {ResourceRef} from '@/components/resource-ref';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {Separator} from '@/components/ui/separator';
import type {CheckResult, EligibilityResult} from '@/lib/types';

interface EligibilityCardProps {
  eligibility: EligibilityResult;
  patientId: string;
}

function CheckRow({check}: {check: CheckResult}) {
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

function UnknownVerdictExplanation({reasons}: {reasons: string[]}) {
  if (reasons.length === 0) return null;
  return (
    <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">
      <p className="font-medium mb-1.5">
        Classified as <span className="italic">Unknown</span> because:
      </p>
      <ul className="list-disc pl-5 space-y-0.5 text-muted-foreground">
        {reasons.map((reason, index) => (
          <li key={`${index}-${reason}`}>{reason}</li>
        ))}
      </ul>
    </div>
  );
}

export function EligibilityCard({eligibility, patientId}: EligibilityCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle>Eligibility</CardTitle>
        <div className="flex items-center gap-3">
          <AIAssistDialog patientId={patientId} />
          <StatusBadge
            status={eligibility.status}
            label={STATUS_LABELS[eligibility.status]}
            className="text-sm h-6 px-3"
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {eligibility.status === 'unknown' && (
          <UnknownVerdictExplanation reasons={eligibility.unknown_reasons} />
        )}
        {eligibility.checks.map((check, index) => (
          <div
            key={`${index}-${check.requirement}`}
            className="space-y-4"
          >
            {index > 0 && <Separator />}
            <CheckRow check={check} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
