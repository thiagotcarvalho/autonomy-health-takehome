// Chronological view of every Observation and Procedure for one patient.
// Reversed to descending order (newest first) so the most recent care —
// which is typically what a prior-auth review hinges on — appears at the
// top. The backend orders ascending; reversing here keeps the backend
// contract untouched.

import {MissingValue} from '@/components/missing-value';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {ScrollArea} from '@/components/ui/scroll-area';
import type {TimelineEntry} from '@/lib/types';

interface TimelineProps {
  entries: TimelineEntry[];
}

const DATE_FORMATTER = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
});

function formatDate(isoDate: string): string {
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) {
    return isoDate;
  }
  return DATE_FORMATTER.format(parsed);
}

function TimelineRow({entry}: {entry: TimelineEntry}) {
  return (
    <div className="flex items-baseline gap-3 py-2 text-sm">
      <span className="w-28 shrink-0 text-muted-foreground tabular-nums">
        {entry.date ? (
          formatDate(entry.date)
        ) : (
          <MissingValue reason="Resource has no effectiveDateTime or period.start." />
        )}
      </span>
      <span className="w-24 shrink-0 text-muted-foreground text-xs uppercase tracking-wide">
        {entry.type}
      </span>
      <span className="flex-1 truncate">{entry.display}</span>
      <span className="font-mono text-[11px] text-muted-foreground shrink-0">
        {entry.resource_id}
      </span>
    </div>
  );
}

export function TimelineCard({entries}: TimelineProps) {
  const orderedEntries = [...entries].reverse();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle>Timeline</CardTitle>
        <span className="text-sm text-muted-foreground">
          {entries.length} {entries.length === 1 ? 'entry' : 'entries'}
        </span>
      </CardHeader>
      <CardContent>
        {orderedEntries.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">
            No Observations or Procedures recorded for this patient.
          </p>
        ) : (
          <ScrollArea className="h-[480px] pr-3">
            <div className="divide-y divide-border">
              {orderedEntries.map((entry) => (
                <TimelineRow key={entry.resource_id} entry={entry} />
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
