"""Unit tests for listing events through the application layer."""

# Datetime builds deterministic calendar allocations for existing events.
from datetime import UTC, datetime

# Pytest parameterizes invalid filter inputs at the application boundary.
import pytest

# CalendarTimeBlock defines each event's occupied interval.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Import the use case responsible for retrieving event collections.
from personal_productivity.events.application.list_events import ListEvents

# Listing tests use complete event domain entities.
from personal_productivity.events.domain.event import Event
from personal_productivity.events.domain.event_status import EventStatus


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


def test_list_events_filters_by_exact_status() -> None:
    """Verify that callers can select one event lifecycle state."""

    # Arrange: create scheduled and cancelled events in one repository snapshot.
    scheduled_event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
        ),
    )
    cancelled_event = Event(
        title="Dentist appointment.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 26, 9, 30, tzinfo=UTC),
        ),
    )
    cancelled_event.cancel()
    repository = ReturningEventCollectionRepository(
        events=(scheduled_event, cancelled_event),
    )
    use_case = ListEvents(repository=repository)

    # Act: request only events with the cancelled lifecycle state.
    listed_events = use_case.execute(status=EventStatus.CANCELLED)

    # Assert: filtering keeps matching entities and queries storage once.
    assert listed_events == (cancelled_event,)
    assert repository.list_call_count == 1


@pytest.mark.parametrize(
    "invalid_status",
    [
        pytest.param("cancelled", id="text"),
        pytest.param(1, id="integer"),
        pytest.param(True, id="boolean"),
    ],
)
def test_list_events_rejects_non_status_filters(
    invalid_status: object,
) -> None:
    """Ensure that arbitrary values cannot become lifecycle filters."""

    # Arrange: observe whether a rejected request reaches persistence.
    repository = ReturningEventCollectionRepository(events=())
    use_case = ListEvents(repository=repository)

    # Act and Assert: filters require the explicit domain enum.
    with pytest.raises(
        TypeError,
        match="Event status filter must be an EventStatus",
    ):
        use_case.execute(status=invalid_status)

    # Invalid requests must fail before querying the repository.
    assert repository.list_call_count == 0


def test_list_events_filters_by_overlapping_time_block() -> None:
    """Return only events occupying part of a requested calendar window."""

    # Arrange: one event overlaps the search window; another only touches it.
    overlapping_event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 19, 0, tzinfo=UTC),
        ),
    )
    touching_event = Event(
        title="Dentist appointment.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 20, 0, tzinfo=UTC),
        ),
    )
    requested_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 25, 18, 30, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
    )
    repository = ReturningEventCollectionRepository(
        events=(overlapping_event, touching_event),
    )
    use_case = ListEvents(repository=repository)

    # Act: request events sharing positive time with the search window.
    listed_events = use_case.execute(time_block=requested_time_block)

    # Assert: half-open boundaries exclude the event touching at the end.
    assert listed_events == (overlapping_event,)
    assert repository.list_call_count == 1


@pytest.mark.parametrize(
    "invalid_time_block",
    [
        pytest.param(
            datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            id="raw_datetime",
        ),
        pytest.param(("start", "end"), id="tuple"),
        pytest.param("tonight", id="text"),
    ],
)
def test_list_events_rejects_raw_time_block_filters(
    invalid_time_block: object,
) -> None:
    """Require a validated calendar interval before event lookup."""

    # Arrange: observe whether invalid calendar input reaches persistence.
    repository = ReturningEventCollectionRepository(events=())
    use_case = ListEvents(repository=repository)

    # Act and Assert: application queries require the shared value object.
    with pytest.raises(
        TypeError,
        match="Event time block filter must be a CalendarTimeBlock",
    ):
        use_case.execute(time_block=invalid_time_block)

    # Invalid requests must fail before querying the repository.
    assert repository.list_call_count == 0


def test_list_events_combines_status_and_time_block_filters() -> None:
    """Return only events matching both lifecycle and calendar criteria."""

    # Arrange: separate status and time matches from their intersection.
    matching_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 19, 0, tzinfo=UTC),
    )
    other_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 26, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 26, 19, 0, tzinfo=UTC),
    )
    scheduled_overlap = Event(
        title="Boxing training.",
        time_block=matching_time_block,
    )
    cancelled_overlap = Event(
        title="Dentist appointment.",
        time_block=matching_time_block,
    )
    cancelled_elsewhere = Event(
        title="Eye examination.",
        time_block=other_time_block,
    )
    cancelled_overlap.cancel()
    cancelled_elsewhere.cancel()
    repository = ReturningEventCollectionRepository(
        events=(
            scheduled_overlap,
            cancelled_overlap,
            cancelled_elsewhere,
        ),
    )
    use_case = ListEvents(repository=repository)

    # Act: request cancelled events overlapping only the first interval.
    listed_events = use_case.execute(
        status=EventStatus.CANCELLED,
        time_block=matching_time_block,
    )

    # Assert: neither a status-only nor a time-only match is returned.
    assert listed_events == (cancelled_overlap,)
    assert repository.list_call_count == 1
