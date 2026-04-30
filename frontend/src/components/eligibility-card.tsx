// Deterministic eligibility verdict for one patient. Renders the overall
// status as a prominent badge and each policy check as its own row with
// status pill, evidence IDs, and a tooltip on every `unknown` carrying
// the reason from the backend.

import {Badge} from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {Separator} from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
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

function CheckStatusBadge({check}: {check: CheckResult}) {
  const label =
    check.status === 'met'
      ? 'Met'
      : check.status === 'not_met'
        ? 'Not Met'
        : 'Unknown';
  if (check.status !== 'unknown') {
    return <StatusBadge status={check.status} label={label} />;
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          role="button"
          aria-label={`unknown — ${check.reason}`}
          className="cursor-help rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <StatusBadge status="unknown" label={label} />
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">{check.reason}</TooltipContent>
    </Tooltip>
  );
}

function CheckRow({check}: {check: CheckResult}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">{check.requirement}</span>
        <CheckStatusBadge check={check} />
      </div>
      {check.status !== 'unknown' && (
        <p className="text-sm text-muted-foreground">{check.reason}</p>
      )}
      {check.evidence.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {check.evidence.map((evidenceId) => (
            <span
              key={evidenceId}
              className="font-mono text-[11px] text-muted-foreground bg-muted/50 rounded px-1.5 py-0.5"
            >
              {evidenceId}
            </span>
          ))}
        </div>
      )}
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
        {eligibility.checks.map((check, index) => (
          <div key={check.requirement} className="space-y-4">
            {index > 0 && <Separator />}
            <CheckRow check={check} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
