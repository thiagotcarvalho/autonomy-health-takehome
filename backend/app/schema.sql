CREATE TABLE IF NOT EXISTS resources (
  id             TEXT PRIMARY KEY,
  type           TEXT NOT NULL,
  patient_id     TEXT,
  effective_date TEXT,
  json           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_resources_patient_type
  ON resources (patient_id, type);
CREATE INDEX IF NOT EXISTS idx_resources_patient_date
  ON resources (patient_id, effective_date);

CREATE TABLE IF NOT EXISTS patient_summary (
  patient_id               TEXT PRIMARY KEY,
  given_name               TEXT,
  family_name              TEXT,
  birth_date               TEXT,
  sex                      TEXT,
  latest_bmi               REAL,
  latest_bmi_date          TEXT,
  latest_bmi_obs_id        TEXT,
  has_hypertension         INTEGER,
  hypertension_cond_id     TEXT,
  has_type2_diabetes       INTEGER,
  type2_diabetes_cond_id   TEXT,
  has_psych_eval           INTEGER,
  psych_eval_doc_id        TEXT,
  has_weight_loss_evidence INTEGER,
  weight_loss_doc_id       TEXT
);
