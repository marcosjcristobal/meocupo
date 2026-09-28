"""Unit tests for the event-cancelling application use case."""

# Datetime creates one valid fixed calendar interval.
from datetime import UTC, datetime

# UUID creates and types portable event identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application-boundary failures.
import pytest

# CalendarTimeBlock represents the interval originally occupied by the event.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Import the use case that will coordinate event cancellation.
from personal_productivity.events.application.cancel_event import CancelEvent

# Missing identities use one storage-independent application outcome.
from personal_productivity.events.application.ports.event_repository import (
    EventNotFoundError,
)

# Tests exercise the real entity and its lifecycle error.
from personal_productivity.events.domain.event import (
    Event,
    InvalidEventTransitionError,
)

# Status verifies the resulting lifecycle explicitly.
from personal_productivity.events.domain.event_status import EventStatus


class RecordingEventRepository:
    """Provide one event while recording retrieval and persistence."""

    def __init__(self, *, event: Event | None) -> None:
        """Configure the event returned by identity lookup."""

        # None represents an event absent from persistence.
        self.event = event

        # Recorded calls make the application's orchestration observable.
        self.requested_ids: list[UUID] = []
        self.saved_events: list[Event] = []

    def get_by_id(self, event_id: UUID) -> Event | None:
        """Return the configured event and record its requested UUID."""

        self.requested_ids.append(event_id)
        return self.event

    def save(self, event: Event) -> None:
        """Record the event selected for persistence."""

        self.saved_events.append(event)


def test_cancel_event_transitions_and_persists_entity() -> None:
    """Verify that cancellation coordinates retrieval, domain, and storage."""

    # Arrange: create one scheduled event available for cancellation.
    event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 29, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 29, 19, 30, tzinfo=UTC),
        ),
    )
    repository = RecordingEventRepository(event=event)
    use_case = CancelEvent(repository=repository)

    # Act: request cancellation through the application boundary.
    cancelled_event = use_case.execute(event_id=event.id)

    # Assert: the domain changed the same authoritative entity.
    assert cancelled_event is event
    assert cancelled_event.status is EventStatus.CANCELLED

    # Assert: exactly one lookup and one persistence write occurred.
    assert repository.requested_ids == [event.id]
    assert repository.saved_events == [event]


@pytest.mark.parametrize(
    "invalid_event_id",
    [None, 42, "not-a-uuid"],
    ids=["none", "integer", "text"],
)
def test_cancel_event_rejects_non_uuid_identifiers(
    invalid_event_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: record all interactions with the repository boundary.
    repository = RecordingEventRepository(event=None)
    use_case = CancelEvent(repository=repository)

    # Act and Assert: only UUID objects may identify an event.
    with pytest.raises(
        TypeError,
        match="Event identifier must be a UUID",
    ):
        use_case.execute(event_id=invalid_event_id)

    # Assert: invalid input never triggers a lookup or write.
    assert repository.requested_ids == []
    assert repository.saved_events == []


def test_cancel_event_reports_missing_identity() -> None:
    """Ensure that an absent event cannot be cancelled."""

    # Arrange: configure persistence to return no matching event.
    event_id = uuid4()
    repository = RecordingEventRepository(event=None)
    use_case = CancelEvent(repository=repository)

    # Act and Assert: absence becomes an application-level error.
    with pytest.raises(
        EventNotFoundError,
        match=f"Event '{event_id}' was not found",
    ):
        use_case.execute(event_id=event_id)

    # Assert: the valid UUID was queried once, with no write afterward.
    assert repository.requested_ids == [event_id]
    assert repository.saved_events == []


def test_cancel_event_does_not_save_rejected_transition() -> None:
    """Ensure that a second cancellation does not reach persistence."""

    # Arrange: provide an event already in its terminal cancelled state.
    event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 29, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 29, 19, 30, tzinfo=UTC),
        ),
    )
    event.cancel()
    repository = RecordingEventRepository(event=event)
    use_case = CancelEvent(repository=repository)

    # Act and Assert: the domain rejects repeating a terminal transition.
    with pytest.raises(
        InvalidEventTransitionError,
        match="Cannot cancel an event from 'cancelled'",
    ):
        use_case.execute(event_id=event.id)

    # Assert: the event remains cancelled and no write was requested.
    assert event.status is EventStatus.CANCELLED
    assert repository.requested_ids == [event.id]
    assert repository.saved_events == []
