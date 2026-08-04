"""Calendar time block value object for planned task work."""

# Dataclass provides value equality and an explicit immutable structure.
from dataclasses import dataclass

# Datetime represents the exact boundaries of planned calendar work.
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskTimeBlock:
    """Represent one exact calendar interval reserved for a task."""

    # The starting instant marks when planned work should begin.
    starts_at: datetime

    # The ending instant marks when the reserved work period finishes.
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