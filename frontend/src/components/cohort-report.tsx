import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {Separator} from '@/components/ui/separator';
import type {CohortReport, EligibilityStatus} from '@/lib/types';
import {cn} from '@/lib/utils';

interface CohortReportCardProps {
  report: CohortReport;
}

const STATUS_LABELS: Record<EligibilityStatus, string> = {
  eligible: 'Eligible',
  not_eligible: 'Not Eligible',
  unknown: 'Unknown',
};

const STATUS_TILE_CLASSES: Record<EligibilityStatus, string> = {
  eligible:
    'bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-900/40',
  not_eligible: 'bg-destructive/5 border-destructive/30',
  unknown: 'bg-muted/50 border-border',
};

const STATUS_VALUE_CLASSES: Record<EligibilityStatus, string> = {
  eligible: 'text-emerald-900 dark:text-emerald-200',
  not_eligible: 'text-destructive',
  unknown: 'text-foreground',
};

const STATUS_ORDER: EligibilityStatus[] = [
  'eligible',
  'not_eligible',
  'unknown',
];

function StatTile({
  status,
  count,
  percentage,
}: {
  status: EligibilityStatus;
  count: number;
  percentage: number;
}) {
  return (
    <div
      className={cn(
        'rounded-lg border px-4 py-3',
        STATUS_TILE_CLASSES[status],
      )}
    >
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {STATUS_LABELS[status]}
      </p>
      <p
        className={cn(
          'text-2xl font-semibold tabular-nums',
          STATUS_VALUE_CLASSES[status],
        )}
      >
        {count}
      </p>
      <p className="text-xs text-muted-foreground tabular-nums">
        {percentage.toFixed(1)}%
      </p>
    </div>
  );
}

export function CohortReportCard({report}: CohortReportCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle>Cohort Eligibility Report</CardTitle>
        <span className="text-sm text-muted-foreground tabular-nums">
          {report.total} {report.total === 1 ? 'patient' : 'patients'}
        </span>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {STATUS_ORDER.map((status) => (
            <StatTile
              key={status}
              status={status}
              count={report.counts[status]}
              percentage={report.percentages[status]}
            />
          ))}
        </div>

        {report.top_unknown_reasons.length > 0 && (
          <div>
            <Separator className="mb-4" />
            <h3 className="text-sm font-medium mb-2">
              Top reasons for Unknown
            </h3>
            <ul className="space-y-1 pl-5 list-disc text-sm marker:text-foreground/60">
              {report.top_unknown_reasons.map((entry, index) => (
                <li key={`${index}-${entry.reason}`}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="flex-1">{entry.reason}</span>
                    <span className="text-muted-foreground text-xs tabular-nums shrink-0">
                      {entry.count}{' '}
                      {entry.count === 1 ? 'patient' : 'patients'}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
