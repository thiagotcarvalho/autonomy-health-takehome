"""Cross-cutting utilities shared across feature modules."""

from datetime import date


def compute_age(birth_date: str | None) -> int | None:
    """Computes a patient's current age from their ISO `birthDate`.

    Args:
        birth_date: ISO-8601 date string from the FHIR Patient
          resource (e.g., `"1972-05-10"`), or `None` when not
          recorded.

    Returns:
        Integer age in years, or `None` when `birth_date` is missing
        or unparseable.
    """
    if not birth_date:
        return None
    try:
        parsed_birth_date = date.fromisoformat(birth_date)
    except ValueError:
        return None
    today = date.today()
    had_birthday = (today.month, today.day) >= (
        parsed_birth_date.month,
        parsed_birth_date.day,
    )
    return today.year - parsed_birth_date.year - (0 if had_birthday else 1)
