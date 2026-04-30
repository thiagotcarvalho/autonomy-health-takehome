"""AI Assist subsystem.

Wraps the Anthropic API to produce a structured, grounded eligibility
review for one patient. Output is reconciled against the deterministic
verdict before reaching the caller — the AI may explain or
contextualize, never override.
"""
