// Renders the literal word "unknown" with a tooltip explaining why the
// value is missing. Single source of truth for the take-home's
// missing-data UX rule: never blank, never "—", never zero — always the
// word "unknown" plus the reason behind it.

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface MissingValueProps {
  reason: string;
}

export function MissingValue({reason}: MissingValueProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="text-muted-foreground italic underline decoration-dotted underline-offset-2 cursor-help">
          unknown
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">{reason}</TooltipContent>
    </Tooltip>
  );
}
