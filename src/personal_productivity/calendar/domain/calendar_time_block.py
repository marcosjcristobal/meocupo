"""Reusable calendar time block value object."""

# Dataclass provides value equality and an explicit immutable structure.
from dataclasses import dataclass

# Datetime represents the exact boundaries of calendar allocations.
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CalendarTimeBlock:
    """Represent one exact interval reserved in the calendar."""

    # The starting instant marks when the calendar allocation begins.
    starts_at: datetime

    # The ending instant marks when the calendar allocation finishes.
    ends_at: datetime

    def __post_init__(self) -> None:
        """Validate interval invariants immediately after construction."""

        # Runtime checks protect the domain from raw API or database values.
        if not isinstance(self.starts_at, datetime) or not isinstance(
            self.ends_at,
            datetime,
        ):
            raise TypeError("Time block boundaries must be datetimes.")

        # Exact schedule boundaries must identify globally comparable instants.
        if (
            self.starts_at.tzinfo is None
            or self.starts_at.utcoffset() is None
            or self.ends_at.tzinfo is None
            or self.ends_at.utcoffset() is None
        ):
            raise ValueError(
                "Time block boundaries must include a timezone."
            )

        # A calendar allocation must contain a strictly positive duration.
        if self.ends_at <= self.starts_at:
            raise ValueError(
                "Time block end must be later than its start."
            )

    def contains(self, instant: datetime) -> bool:
        """Return whether an instant belongs to this calendar allocation."""

        # Runtime validation prevents raw values from entering comparison.
        if not isinstance(instant, datetime):
            raise TypeError("Calendar instant must be a datetime.")

        # Membership requires an absolute and globally comparable moment.
        if (
            instant.tzinfo is None
            or instant.utcoffset() is None
        ):
            raise ValueError(
                "Calendar instant must include a timezone."
            )

        # Half-open boundaries include the start and exclude the end.
        return self.starts_at <= instant < self.ends_at

    def overlaps(self, other: "CalendarTimeBlock") -> bool:
        """Return whether two blocks share a positive amount of time."""

        # Runtime validation prevents arbitrary values from entering comparison.
        if not isinstance(other, CalendarTimeBlock):
            raise TypeError(
                "Other value must be a CalendarTimeBlock."
            )

        # Strict comparisons make touching boundaries non-overlapping.
        return (
            self.starts_at < other.ends_at
            and other.starts_at < self.ends_at
        )
