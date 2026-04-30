import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {cn} from '@/lib/utils';

interface ResourceRefProps {
  id: string;
  showType?: boolean;
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

function formatDisplay(id: string, showType: boolean): string {
  const {type, bareId} = splitReference(id);
  const truncated =
    bareId.length > TRUNCATE_THRESHOLD
      ? bareId.slice(0, SHORT_HASH_LENGTH)
      : bareId;
  if (showType && type) {
    return `${type}/${truncated}`;
  }
  return truncated;
}

export function ResourceRef({
  id,
  showType = false,
  className,
}: ResourceRefProps) {
  const display = formatDisplay(id, showType);
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
