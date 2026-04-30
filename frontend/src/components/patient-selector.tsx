import {Check, ChevronsUpDown} from 'lucide-react';
import {useState} from 'react';

import {Button} from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import type {PatientListItem} from '@/lib/types';
import {cn} from '@/lib/utils';

interface PatientSelectorProps {
  patients: PatientListItem[];
  selectedId: string | null;
  onSelect: (patientId: string) => void;
  disabled?: boolean;
}

function findSelected(
  patients: PatientListItem[],
  selectedId: string | null,
): PatientListItem | undefined {
  if (!selectedId) return undefined;
  return patients.find((patient) => patient.id === selectedId);
}

export function PatientSelector({
  patients,
  selectedId,
  onSelect,
  disabled,
}: PatientSelectorProps) {
  const [open, setOpen] = useState(false);
  const selected = findSelected(patients, selectedId);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label="Select patient"
          disabled={disabled}
          className="w-[360px] justify-between font-normal"
        >
          <span className="truncate">
            {selected ? selected.display_name : 'Select patient...'}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[360px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search by name or ID..." />
          <CommandList>
            <CommandEmpty>No patient found.</CommandEmpty>
            <CommandGroup>
              {patients.map((patient) => (
                <CommandItem
                  key={patient.id}
                  value={`${patient.display_name} ${patient.id}`}
                  onSelect={() => {
                    onSelect(patient.id);
                    setOpen(false);
                  }}
                  className="flex items-center justify-between gap-2"
                >
                  <span className="truncate">{patient.display_name}</span>
                  <span className="text-muted-foreground font-mono text-[11px] shrink-0">
                    {patient.id.slice(0, 8)}
                  </span>
                  <Check
                    className={cn(
                      'h-4 w-4 shrink-0',
                      patient.id === selectedId
                        ? 'opacity-100'
                        : 'opacity-0',
                    )}
                  />
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
