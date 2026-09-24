"""Integration tests for event creation and retrieval workflows."""

# Datetime builds one deterministic calendar allocation.
from datetime import UTC, datetime

# CalendarTimeBlock represents the interval occupied by the event.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Application use cases collaborate without knowing the storage technology.
from personal_productivity.events.application.create_event import CreateEvent
from personal_productivity.events.application.get_event import GetEvent
from personal_productivity.events.application.list_events import ListEvents

# Status verifies that persistence preserves event lifecycle state.
from personal_productivity.events.domain.event_status import EventStatus

# The in-memory adapter provides shared persistence for the workflow.
from personal_productivity.events.infrastructure.repositories.in_memory_event_repository import (
    InMemoryEventRepository,
)


def test_created_event_can_be_retrieved_through_shared_repository() -> None:
    """Verify that event use cases collaborate through one repository."""

    # Arrange: share one adapter between independent application services.
    repository = InMemoryEventRepository()
    create_event = CreateEvent(repository=repository)
    get_event = GetEvent(repository=repository)
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 15, 19, 30, tzinfo=UTC),
    )

    # Act: create an event and retrieve it through a separate use case.
    created_event = create_event.execute(
        title="Boxing training.",
        time_block=time_block,
        description="Bring the red gloves.",
    )
    retrieved_event = get_event.execute(event_id=created_event.id)

    # Assert: both operations refer to the same authoritative entity.
    assert retrieved_event is created_event
    assert retrieved_event.title == "Boxing training."
    assert retrieved_event.time_block == time_block
    assert retrieved_event.description == "Bring the red gloves."
    assert retrieved_event.status is EventStatus.SCHEDULED


def test_created_events_appear_in_application_listing() -> None:
    """Verify that separately created events appear in one listing."""

    # Arrange: share one adapter between creation and collection retrieval.
    repository = InMemoryEventRepository()
    create_event = CreateEvent(repository=repository)
    list_events = ListEvents(repository=repository)

    # Act: create two events and request the complete collection.
    first_event = create_event.execute(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
        ),
    )
    second_event = create_event.execute(
        title="Dentist appointment.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 26, 9, 30, tzinfo=UTC),
        ),
    )
    listed_events = list_events.execute()

    # Assert: listing retains both identities and their insertion order.
    assert listed_events == (first_event, second_event)
    assert isinstance(listed_events, tuple)
