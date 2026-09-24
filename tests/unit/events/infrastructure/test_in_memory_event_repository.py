"""Unit tests for the in-memory event repository adapter."""

# Datetime builds one deterministic calendar allocation.
from datetime import UTC, datetime

# UUID creates one valid identity absent from storage.
from uuid import uuid4

# Pytest verifies runtime validation at the repository boundary.
import pytest

# CalendarTimeBlock represents the interval occupied by the event.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Tests persist and retrieve real event domain entities.
from personal_productivity.events.domain.event import Event

# Duplicate creation uses one storage-independent repository outcome.
from personal_productivity.events.application.ports.event_repository import (
    EventAlreadyExistsError,
)

# Import the local adapter exercised by these tests.
from personal_productivity.events.infrastructure.repositories.in_memory_event_repository import (
    InMemoryEventRepository,
)


def test_added_event_can_be_retrieved_by_identity() -> None:
    """Verify that an added event remains available under its UUID."""

    # Arrange: create isolated in-memory storage and one event.
    repository = InMemoryEventRepository()
    event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 15, 19, 30, tzinfo=UTC),
        ),
    )

    # Act: persist and retrieve the event through the adapter contract.
    repository.add(event)
    retrieved_event = repository.get_by_id(event.id)

    # Assert: in-memory persistence preserves the authoritative entity.
    assert retrieved_event is event


def test_unknown_event_identity_returns_none() -> None:
    """Verify that an absent valid UUID produces no stored entity."""

    # Arrange: create isolated storage with no events.
    repository = InMemoryEventRepository()

    # Act: query one well-formed identity that was never added.
    retrieved_event = repository.get_by_id(uuid4())

    # Assert: repository absence uses the optional return contract.
    assert retrieved_event is None


@pytest.mark.parametrize(
    "invalid_event",
    [
        None,
        42,
        "not-an-event",
    ],
    ids=[
        "none",
        "integer",
        "text",
    ],
)
def test_add_rejects_non_event_values(
    invalid_event: object,
) -> None:
    """Ensure that only domain events can enter repository storage."""

    # Arrange: create isolated empty storage.
    repository = InMemoryEventRepository()

    # Act and Assert: arbitrary values fail with a stable boundary error.
    with pytest.raises(
        TypeError,
        match="Event must be an Event",
    ):
        repository.add(invalid_event)


@pytest.mark.parametrize(
    "invalid_event_id",
    [
        None,
        42,
        "not-a-uuid",
    ],
    ids=[
        "none",
        "integer",
        "text",
    ],
)
def test_get_by_id_rejects_non_uuid_values(
    invalid_event_id: object,
) -> None:
    """Ensure that malformed identities cannot enter storage lookup."""

    # Arrange: create an empty adapter for the invalid query.
    repository = InMemoryEventRepository()

    # Act and Assert: repository keys must use the domain identity type.
    with pytest.raises(
        TypeError,
        match="Event identifier must be a UUID",
    ):
        repository.get_by_id(invalid_event_id)


def test_add_rejects_duplicate_event_identity() -> None:
    """Ensure that add semantics never overwrite an existing event."""

    # Arrange: persist one event under its generated identity.
    repository = InMemoryEventRepository()
    existing_event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 15, 19, 30, tzinfo=UTC),
        ),
    )
    duplicate_event = Event(
        id=existing_event.id,
        title="Replacement event.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 16, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 16, 19, 30, tzinfo=UTC),
        ),
    )
    repository.add(existing_event)

    # Act and Assert: creation rejects an occupied identity.
    with pytest.raises(
        EventAlreadyExistsError,
        match=f"Event '{existing_event.id}' already exists",
    ):
        repository.add(duplicate_event)

    # Assert: the original authoritative entity remains stored.
    assert repository.get_by_id(existing_event.id) is existing_event


def test_list_all_returns_immutable_event_snapshot() -> None:
    """Verify that collection retrieval does not expose mutable storage."""

    # Arrange: store two independent events in a known order.
    repository = InMemoryEventRepository()
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
    repository.add(first_event)
    repository.add(second_event)

    # Act: request a snapshot of every stored event.
    event_snapshot = repository.list_all()

    # Assert: callers receive an immutable collection in insertion order.
    assert isinstance(event_snapshot, tuple)
    assert event_snapshot == (first_event, second_event)
