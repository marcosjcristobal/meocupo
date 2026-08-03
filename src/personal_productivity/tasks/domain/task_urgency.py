"""Urgency levels calculated from task deadlines."""

# StrEnum combines enum safety with values suitable for external serialization.
from enum import StrEnum


class TaskUrgency(StrEnum):
    """Represent temporal pressure derived automatically by the domain."""

    # Tasks without near temporal pressure do not require urgent attention.
    NOT_URGENT = "not_urgent"

    # Upcoming tasks are approaching but do not require immediate action.
    UPCOMING = "upcoming"

    # Imminent tasks require attention within a short period.
    IMMINENT = "imminent"

    # Overdue tasks have already passed their temporal commitment.
    OVERDUE = "overdue"