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
        <span
          tabIndex={0}
          role="button"
          aria-label={`unknown — ${reason}`}
          className="text-muted-foreground italic underline decoration-dotted underline-offset-2 cursor-help rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          unknown
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">{reason}</TooltipContent>
    </Tooltip>
  );
}
