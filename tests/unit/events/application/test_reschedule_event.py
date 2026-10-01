"""Unit tests for the event-rescheduling application use case."""

# Datetime creates deterministic original and replacement intervals.
from datetime import UTC, datetime

# UUID creates and types portable event identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application-boundary failures.
import pytest

# CalendarTimeBlock represents exact event allocations.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Import the use case that will coordinate event rescheduling.
from personal_productivity.events.application.reschedule_event import (
    RescheduleEvent,
)

# Missing identities use one storage-independent application outcome.
from personal_productivity.events.application.ports.event_repository import (
    EventNotFoundError,
)

# Tests exercise the real entity and its lifecycle error.
from personal_productivity.events.domain.event import (
    Event,
    InvalidEventTransitionError,
)

# Status verifies that rescheduling does not cancel an event.
from personal_productivity.events.domain.event_status import EventStatus


class RecordingEventRepository:
    """Provide one event while recording retrieval and persistence."""

    def __init__(self, *, event: Event | None) -> None:
        """Configure the event returned by identity lookup."""

        # None represents an identity absent from storage.
        self.event = event

        # Recorded calls make orchestration observable.
        self.requested_ids: list[UUID] = []
        self.saved_events: list[Event] = []

    def get_by_id(self, event_id: UUID) -> Event | None:
        """Return the configured event and record its requested UUID."""

        self.requested_ids.append(event_id)
        return self.event

    def save(self, event: Event) -> None:
        """Record the event selected for persistence."""

        self.saved_events.append(event)


def test_reschedule_event_changes_interval_and_persists_entity() -> None:
    """Verify that rescheduling coordinates lookup, domain, and storage."""

    # Arrange: create a scheduled event with its original allocation.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 29, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 29, 19, 30, tzinfo=UTC),
    )
    replacement_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 30, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 30, 19, 30, tzinfo=UTC),
    )
    event = Event(
        title="Boxing training.",
        time_block=original_time_block,
    )
    repository = RecordingEventRepository(event=event)
    use_case = RescheduleEvent(repository=repository)

    # Act: request a new allocation through the application boundary.
    updated_event = use_case.execute(
        event_id=event.id,
        time_block=replacement_time_block,
    )

    # Assert: the domain moved the same authoritative event.
    assert updated_event is event
    assert updated_event.time_block == replacement_time_block
    assert updated_event.status is EventStatus.SCHEDULED

    # Assert: one lookup and one persistence write occurred.
    assert repository.requested_ids == [event.id]
    assert repository.saved_events == [event]


@pytest.mark.parametrize(
    "invalid_event_id",
    [None, 42, "not-a-uuid"],
    ids=["none", "integer", "text"],
)
def test_reschedule_event_rejects_non_uuid_identifiers(
    invalid_event_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare a valid replacement and observable repository.
    replacement_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 30, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 30, 19, 30, tzinfo=UTC),
    )
    repository = RecordingEventRepository(event=None)
    use_case = RescheduleEvent(repository=repository)

    # Act and Assert: event identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Event identifier must be a UUID",
    ):
        use_case.execute(
            event_id=invalid_event_id,
            time_block=replacement_time_block,
        )

    # Assert: invalid input triggers no lookup or write.
    assert repository.requested_ids == []
    assert repository.saved_events == []


def test_reschedule_event_reports_missing_identity() -> None:
    """Ensure that an absent event cannot be reprogrammed."""

    # Arrange: configure one valid but missing identity.
    event_id = uuid4()
    replacement_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 30, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 30, 19, 30, tzinfo=UTC),
    )
    repository = RecordingEventRepository(event=None)
    use_case = RescheduleEvent(repository=repository)

    # Act and Assert: absence becomes an application-level error.
    with pytest.raises(
        EventNotFoundError,
        match=f"Event '{event_id}' was not found",
    ):
        use_case.execute(
            event_id=event_id,
            time_block=replacement_time_block,
        )

    # Assert: lookup occurred once, but no update was saved.
    assert repository.requested_ids == [event_id]
    assert repository.saved_events == []


@pytest.mark.parametrize(
    "invalid_time_block",
    [
        None,
        datetime(2026, 9, 30, 18, 0, tzinfo=UTC),
        (
            datetime(2026, 9, 30, 18, 0, tzinfo=UTC),
            datetime(2026, 9, 30, 19, 30, tzinfo=UTC),
        ),
    ],
    ids=["none", "raw_datetime", "tuple"],
)
def test_reschedule_event_does_not_save_raw_time_block_values(
    invalid_time_block: object,
) -> None:
    """Ensure that only validated calendar intervals can be stored."""

    # Arrange: keep one event's original allocation observable.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 29, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 29, 19, 30, tzinfo=UTC),
    )
    event = Event(
        title="Boxing training.",
        time_block=original_time_block,
    )
    repository = RecordingEventRepository(event=event)
    use_case = RescheduleEvent(repository=repository)

    # Act and Assert: the domain rejects raw temporal values.
    with pytest.raises(
        TypeError,
        match="Event time block must be a CalendarTimeBlock",
    ):
        use_case.execute(
            event_id=event.id,
            time_block=invalid_time_block,
        )

    # Assert: invalid input preserves planning and skips persistence.
    assert event.time_block is original_time_block
    assert repository.requested_ids == [event.id]
    assert repository.saved_events == []


def test_reschedule_event_does_not_save_cancelled_event_changes() -> None:
    """Ensure that a cancelled event retains its historical interval."""

    # Arrange: cancel an event before requesting a new allocation.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 29, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 29, 19, 30, tzinfo=UTC),
    )
    replacement_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 30, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 30, 19, 30, tzinfo=UTC),
    )
    event = Event(
        title="Boxing training.",
        time_block=original_time_block,
    )
    event.cancel()
    repository = RecordingEventRepository(event=event)
    use_case = RescheduleEvent(repository=repository)

    # Act and Assert: terminal events reject further planning changes.
    with pytest.raises(
        InvalidEventTransitionError,
        match="Cannot reschedule an event from 'cancelled'",
    ):
        use_case.execute(
            event_id=event.id,
            time_block=replacement_time_block,
        )

    # Assert: rejection preserves historical state and skips persistence.
    assert event.status is EventStatus.CANCELLED
    assert event.time_block is original_time_block
    assert repository.requested_ids == [event.id]
    assert repository.saved_events == []
