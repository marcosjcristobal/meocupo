"""Deadline value object for a task."""

# Dataclass provides value-based equality and an explicit immutable structure.
from dataclasses import dataclass

# Date and datetime preserve date-only and exact-instant semantics separately.
from datetime import date, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDeadline:
    """Represent either a calendar date or an exact deadline instant."""

    # A date-only deadline preserves that the user supplied no specific time.
    due_on: date | None = None

    # An exact deadline includes both time and timezone information.
    due_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate that the deadline has one unambiguous representation."""

        # Equal presence means either both values exist or both are missing.
        has_due_on = self.due_on is not None
        has_due_at = self.due_at is not None
        if has_due_on == has_due_at:
            raise ValueError(
                "Deadline requires exactly one of due_on or due_at."
            )

        # Datetime inherits from date, so reject it explicitly for due_on.
        if self.due_on is not None and (
            isinstance(self.due_on, datetime)
            or not isinstance(self.due_on, date)
        ):
            raise TypeError("due_on must be a date without time.")

        # Exact deadlines require the richer datetime type.
        if self.due_at is not None and not isinstance(
            self.due_at,
            datetime,
        ):
            raise TypeError("due_at must be a datetime.")

        # Exact instants must be comparable across users and system boundaries.
        if (
            self.due_at is not None
            and (
                self.due_at.tzinfo is None
                or self.due_at.utcoffset() is None
            )
        ):
            raise ValueError("Exact deadline must include a timezone.")
