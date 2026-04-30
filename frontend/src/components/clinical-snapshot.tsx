import {MissingValue} from '@/components/missing-value';
import {ResourceRef} from '@/components/resource-ref';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {Separator} from '@/components/ui/separator';
import type {ClinicalSnapshot as Snapshot} from '@/lib/types';

interface ClinicalSnapshotProps {
  snapshot: Snapshot;
}

interface FactRowProps {
  label: string;
  children: React.ReactNode;
  evidenceId?: string | null;
}

function FactRow({label, children, evidenceId}: FactRowProps) {
  return (
    <div className="flex items-baseline gap-3 text-sm">
      <span className="text-muted-foreground w-32 shrink-0">{label}</span>
      <span className="flex-1">{children}</span>
      {evidenceId && <ResourceRef id={evidenceId} />}
    </div>
  );
}

function PatientName({
  givenName,
  familyName,
}: {
  givenName: string | null;
  familyName: string | null;
}) {
  if (!givenName && !familyName) {
    return <MissingValue reason="No name recorded on the Patient resource." />;
  }
  return <span>{[givenName, familyName].filter(Boolean).join(' ')}</span>;
}

export function ClinicalSnapshotCard({snapshot}: ClinicalSnapshotProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Clinical Snapshot</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <FactRow label="Patient" evidenceId={snapshot.patient_id}>
            <PatientName
              givenName={snapshot.given_name}
              familyName={snapshot.family_name}
            />
          </FactRow>
          <FactRow label="Age">
            {snapshot.age ?? (
              <MissingValue reason="No birth date recorded; age cannot be computed." />
            )}
          </FactRow>
          {/* No evidence ID on this row: gender comes from the Patient
              resource itself, already cited on the Patient row above. */}
          <FactRow label="Sex">
            {snapshot.sex ?? (
              <MissingValue reason="No gender recorded on the Patient resource." />
            )}
          </FactRow>
          <FactRow label="Latest BMI" evidenceId={snapshot.latest_bmi_evidence_id}>
            {snapshot.latest_bmi != null ? (
              `${snapshot.latest_bmi.toFixed(1)} kg/m²`
            ) : (
              <MissingValue reason="No BMI observation (LOINC 39156-5) found for this patient." />
            )}
          </FactRow>
        </div>

        <Separator />

        <div>
          <div className="text-sm font-medium mb-2">Active conditions</div>
          {snapshot.active_conditions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No active conditions documented.
            </p>
          ) : (
            <ul className="space-y-1 pl-5 list-disc text-sm marker:text-foreground/60">
              {snapshot.active_conditions.map((condition) => (
                <li key={condition.resource_id}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate">{condition.display}</span>
                    <ResourceRef id={condition.resource_id} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <Separator />

        <div>
          <div className="text-sm font-medium mb-2">Recent procedures</div>
          {snapshot.recent_procedures.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No recent procedures documented.
            </p>
          ) : (
            <ul className="space-y-1 pl-5 list-disc text-sm marker:text-foreground/60">
              {snapshot.recent_procedures.map((procedure) => (
                <li key={procedure.resource_id}>
                  <div className="flex items-baseline gap-3">
                    <span className="flex-1 truncate">{procedure.display}</span>
                    <span className="text-muted-foreground text-xs shrink-0">
                      {procedure.date ?? (
                        <MissingValue reason="Procedure has no effectiveDateTime or period.start." />
                      )}
                    </span>
                    <ResourceRef id={procedure.resource_id} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
