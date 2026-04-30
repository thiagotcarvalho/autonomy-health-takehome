import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {cn} from '@/lib/utils';

interface ResourceRefProps {
  id: string;
  showType?: boolean;
  full?: boolean;
  className?: string;
}

const SHORT_HASH_LENGTH = 8;
const TRUNCATE_THRESHOLD = 12;

function splitReference(id: string): {type: string | null; bareId: string} {
  const slashIndex = id.indexOf('/');
  if (slashIndex < 0) {
    return {type: null, bareId: id};
  }
  return {
    type: id.slice(0, slashIndex),
    bareId: id.slice(slashIndex + 1),
  };
}

function formatDisplay(id: string, showType: boolean, full: boolean): string {
  const {type, bareId} = splitReference(id);
  const visibleId =
    full || bareId.length <= TRUNCATE_THRESHOLD
      ? bareId
      : bareId.slice(0, SHORT_HASH_LENGTH);
  if (showType && type) {
    return `${type}/${visibleId}`;
  }
  return visibleId;
}

export function ResourceRef({
  id,
  showType = false,
  full = false,
  className,
}: ResourceRefProps) {
  const display = formatDisplay(id, showType, full);
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          aria-label={`Resource reference ${id}`}
          className={cn(
            'font-mono text-[11px] text-muted-foreground cursor-help rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            className,
          )}
        >
          {display}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs font-mono text-xs">
        {id}
      </TooltipContent>
    </Tooltip>
  );
}
