"""Unit tests for listing events through the application layer."""

# Datetime builds deterministic calendar allocations for existing events.
from datetime import UTC, datetime

# CalendarTimeBlock defines each event's occupied interval.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Import the use case responsible for retrieving event collections.
from personal_productivity.events.application.list_events import ListEvents

# Listing tests use complete event domain entities.
from personal_productivity.events.domain.event import Event


class ReturningEventCollectionRepository:
    """Return a configured immutable collection of events."""

    def __init__(self, events: tuple[Event, ...]) -> None:
        """Configure the snapshot returned by the repository."""

        # The test controls the exact collection available to the use case.
        self.events = events

        # Count collection queries to detect missing or repeated lookups.
        self.list_call_count = 0

    def list_all(self) -> tuple[Event, ...]:
        """Return the configured events and record the interaction."""

        # Listing should request one snapshot from persistence.
        self.list_call_count += 1
        return self.events


def test_list_events_returns_repository_snapshot() -> None:
    """Verify that listing returns every event supplied by persistence."""

    # Arrange: configure two separate calendar events.
    first_event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
        ),
    )
    second_event = Event(
        title="Dentist appointment.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 26, 9, 30, tzinfo=UTC),
        ),
    )
    expected_events = (first_event, second_event)
    repository = ReturningEventCollectionRepository(events=expected_events)
    use_case = ListEvents(repository=repository)

    # Act: request the complete event collection.
    listed_events = use_case.execute()

    # Assert: the application returns the same immutable snapshot.
    assert listed_events is expected_events
    assert repository.list_call_count == 1
