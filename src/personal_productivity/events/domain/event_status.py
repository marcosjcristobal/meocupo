"""Persisted lifecycle states available to calendar events."""

# StrEnum combines enum safety with string values suitable for serialization.
from enum import StrEnum


class EventStatus(StrEnum):
    """Represent durable lifecycle outcomes of an event."""

    # Scheduled is the active state of an event expected to occupy calendar time.
    SCHEDULED = "scheduled"

    # Cancelled preserves that the event existed but will no longer take place.
    CANCELLED = "cancelled"