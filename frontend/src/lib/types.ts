export type CheckStatus = 'met' | 'not_met' | 'unknown';

export type EligibilityStatus = 'eligible' | 'not_eligible' | 'unknown';

export interface CheckResult {
  requirement: string;
  status: CheckStatus;
  reason: string;
  evidence: string[];
}

export interface EligibilityResult {
  status: EligibilityStatus;
  checks: CheckResult[];
  unknown_reasons: string[];
}

export interface PatientListItem {
  id: string;
  display_name: string;
}

export interface TimelineEntry {
  resource_id: string;
  type: string;
  display: string;
  date: string | null;
}

export interface ConditionEntry {
  resource_id: string;
  display: string;
}

export interface ProcedureEntry {
  resource_id: string;
  display: string;
  date: string | null;
}

export interface ClinicalSnapshot {
  patient_id: string;
  given_name: string | null;
  family_name: string | null;
  age: number | null;
  sex: string | null;
  latest_bmi: number | null;
  latest_bmi_evidence_id: string | null;
  active_conditions: ConditionEntry[];
  recent_procedures: ProcedureEntry[];
}

export interface PatientView {
  snapshot: ClinicalSnapshot;
  timeline: TimelineEntry[];
  eligibility: EligibilityResult;
}

export interface CohortReason {
  reason: string;
  count: number;
}

export interface CohortReport {
  total: number;
  counts: Record<EligibilityStatus, number>;
  percentages: Record<EligibilityStatus, number>;
  top_unknown_reasons: CohortReason[];
}
