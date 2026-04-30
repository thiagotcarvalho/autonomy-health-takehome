import {Badge} from '@/components/ui/badge';
import type {CheckStatus, EligibilityStatus} from '@/lib/types';
import {cn} from '@/lib/utils';

export const STATUS_LABELS: Record<EligibilityStatus, string> = {
  eligible: 'Eligible',
  not_eligible: 'Not Eligible',
  unknown: 'Unknown',
};

export const CHECK_STATUS_LABELS: Record<CheckStatus, string> = {
  met: 'Met',
  not_met: 'Not Met',
  unknown: 'Unknown',
};

// Shared between EligibilityStatus and CheckStatus — values are
// disjoint except `unknown`, which intentionally maps to the same style.
const STATUS_CLASSES: Record<EligibilityStatus | CheckStatus, string> = {
  eligible:
    'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200',
  met: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200',
  not_eligible: 'bg-destructive/10 text-destructive dark:bg-destructive/20',
  not_met: 'bg-destructive/10 text-destructive dark:bg-destructive/20',
  unknown: 'bg-muted text-muted-foreground',
};

interface StatusBadgeProps {
  status: EligibilityStatus | CheckStatus;
  label: string;
  className?: string;
}

export function StatusBadge({status, label, className}: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn('border-transparent', STATUS_CLASSES[status], className)}
    >
      {label}
    </Badge>
  );
}
