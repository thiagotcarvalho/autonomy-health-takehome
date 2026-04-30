"""JSON Schema for the structured-output tool the model uses.

Forcing the model to invoke a tool with a strict input schema turns
"please return JSON" into a structural guarantee — malformed output
becomes impossible at the API layer, so failure modes simplify to
network errors and refusal-to-use-the-tool.
"""

from typing import Any

ASSESSMENT_TOOL_NAME = "report_eligibility_assessment"


ASSESSMENT_TOOL: dict[str, Any] = {
    "name": ASSESSMENT_TOOL_NAME,
    "description": (
        "Report your assessment of the patient's eligibility for "
        "bariatric surgery. You MUST invoke this tool exactly once."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["eligible", "not_eligible", "unknown"],
                "description": (
                    "Overall eligibility verdict. Use 'unknown' when any "
                    "required item is missing — never guess."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "1-3 sentence rationale in plain clinical language."
                ),
            },
            "checks": {
                "type": "array",
                "description": (
                    "Per-criterion breakdown matching the four policy "
                    "checks: BMI threshold, comorbidity, psychological "
                    "evaluation, prior weight-loss attempts."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "requirement": {
                            "type": "string",
                            "description": (
                                "The criterion name (e.g., 'BMI threshold')."
                            ),
                        },
                        "status": {
                            "type": "string",
                            "enum": ["met", "not_met", "unknown"],
                        },
                        "reason": {
                            "type": "string",
                            "description": (
                                "Why this criterion is in this state. "
                                "Cite numeric values when present."
                            ),
                        },
                        "evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "FHIR resource references from the "
                                "provided context that justify this "
                                "finding. Empty list when status is "
                                "'unknown'."
                            ),
                        },
                    },
                    "required": [
                        "requirement",
                        "status",
                        "reason",
                        "evidence",
                    ],
                },
            },
        },
        "required": ["status", "reasoning", "checks"],
    },
}
