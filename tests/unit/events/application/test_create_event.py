"""Unit tests for the event creation application use case."""

# Datetime builds one deterministic calendar allocation.
from datetime import UTC, datetime

# Pytest verifies that domain failures cross the application boundary.
import pytest

# CalendarTimeBlock represents the interval occupied by the event.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Import the use case that will coordinate creation and persistence.
from personal_productivity.events.application.create_event import CreateEvent

# The recording repository stores real domain entities for verification.
from personal_productivity.events.domain.event import Event

# Status verifies the initial event lifecycle.
from personal_productivity.events.domain.event_status import EventStatus


class RecordingEventRepository:
    """Record added events without requiring concrete storage."""

    def __init__(self) -> None:
        """Start with no recorded persistence operations."""

        # A list preserves the entities and their insertion order.
        self.added_events: list[Event] = []

    def add(
        self,
        event: Event,
    ) -> None:
        """Record the event submitted for initial persistence."""

        # This test double keeps storage outside the application test.
        self.added_events.append(event)


def test_create_event_builds_and_persists_domain_entity() -> None:
    """Verify that creation saves and returns the same valid event."""

    # Arrange: define the concrete interval occupied by the event.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 15, 19, 30, tzinfo=UTC),
    )
    repository = RecordingEventRepository()
    use_case = CreateEvent(repository=repository)

    # Act: submit external values through the application boundary.
    created_event = use_case.execute(
        title="   Boxing training.   ",
        time_block=time_block,
        description="   Bring the red gloves.   ",
    )

    # Assert: the domain normalized and initialized the new entity.
    assert isinstance(created_event, Event)
    assert created_event.title == "Boxing training."
    assert created_event.time_block == time_block
    assert created_event.description == "Bring the red gloves."
    assert created_event.status is EventStatus.SCHEDULED

    # Assert: persistence receives exactly the returned entity.
    assert repository.added_events == [created_event]


def test_create_event_does_not_persist_invalid_entity() -> None:
    """Ensure that invalid event construction never reaches storage."""

    # Arrange: define a valid interval so only the title is invalid.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 15, 19, 30, tzinfo=UTC),
    )
    repository = RecordingEventRepository()
    use_case = CreateEvent(repository=repository)

    # Act and Assert: the domain rejects a title without useful text.
    with pytest.raises(
        ValueError,
        match="Event title cannot be empty",
    ):
        use_case.execute(
            title="   ",
            time_block=time_block,
        )

    # Assert: failed construction never reaches persistent storage.
    assert repository.added_events == []


@pytest.mark.parametrize(
    "invalid_time_block",
    [
        None,
        datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
        (
            datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
            datetime(2026, 9, 15, 19, 30, tzinfo=UTC),
        ),
    ],
    ids=[
        "none",
        "raw_datetime",
        "tuple",
    ],
)
def test_create_event_does_not_persist_raw_time_block_values(
    invalid_time_block: object,
) -> None:
    """Ensure that event creation requires the calendar value object."""

    # Arrange: inject storage whose writes remain observable.
    repository = RecordingEventRepository()
    use_case = CreateEvent(repository=repository)

    # Act and Assert: raw temporal values cannot bypass calendar rules.
    with pytest.raises(
        TypeError,
        match="Event time block must be a CalendarTimeBlock",
    ):
        use_case.execute(
            title="Boxing training.",
            time_block=invalid_time_block,
        )

    # Assert: rejected construction performs no persistence operation.
    assert repository.added_events == []

