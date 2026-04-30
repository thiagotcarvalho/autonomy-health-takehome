import {ResourceRef} from '@/components/resource-ref';
import {Badge} from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {Separator} from '@/components/ui/separator';
import type {
  CheckResult,
  CheckStatus,
  EligibilityResult,
  EligibilityStatus,
} from '@/lib/types';
import {cn} from '@/lib/utils';

interface EligibilityCardProps {
  eligibility: EligibilityResult;
}

interface StatusBadgeProps {
  status: EligibilityStatus | CheckStatus;
  label: string;
  className?: string;
}

const STATUS_LABELS: Record<EligibilityStatus, string> = {
  eligible: 'Eligible',
  not_eligible: 'Not Eligible',
  unknown: 'Unknown',
};

const CHECK_STATUS_LABELS: Record<CheckStatus, string> = {
  met: 'Met',
  not_met: 'Not Met',
  unknown: 'Unknown',
};

// Shared between EligibilityStatus and CheckStatus — their values are
// disjoint except for `unknown`, which intentionally maps to the same style.
const STATUS_CLASSES: Record<EligibilityStatus | CheckStatus, string> = {
  eligible:
    'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200',
  met:
    'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200',
  not_eligible:
    'bg-destructive/10 text-destructive dark:bg-destructive/20',
  not_met:
    'bg-destructive/10 text-destructive dark:bg-destructive/20',
  unknown: 'bg-muted text-muted-foreground',
};

function StatusBadge({status, label, className}: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn('border-transparent', STATUS_CLASSES[status], className)}
    >
      {label}
    </Badge>
  );
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

export function EligibilityCard({eligibility}: EligibilityCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle>Eligibility</CardTitle>
        <StatusBadge
          status={eligibility.status}
          label={STATUS_LABELS[eligibility.status]}
          className="text-sm h-6 px-3"
        />
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
