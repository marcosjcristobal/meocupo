"""Unit tests for retrieving one event through the application layer."""

# Datetime builds one deterministic calendar allocation.
from datetime import UTC, datetime

# UUID creates and types portable event identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application-boundary failures.
import pytest

# CalendarTimeBlock represents the interval occupied by the event.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Import the use case responsible for required event retrieval.
from personal_productivity.events.application.get_event import GetEvent

# Missing identities use one storage-independent application outcome.
from personal_productivity.events.application.ports.event_repository import (
    EventNotFoundError,
)

# Tests return one real event domain entity.
from personal_productivity.events.domain.event import Event


class ReturningEventRepository:
    """Return one configured event while recording identity lookups."""

    def __init__(
        self,
        *,
        event: Event | None,
    ) -> None:
        """Configure the event returned by the repository double."""

        # None represents an identity absent from persistence.
        self.event = event

        # Recorded identities make the application interaction observable.
        self.requested_ids: list[UUID] = []

    def get_by_id(
        self,
        event_id: UUID,
    ) -> Event | None:
        """Return the configured event and record the requested identity."""

        # Preserve the interaction for later assertions.
        self.requested_ids.append(event_id)
        return self.event


def test_get_event_returns_entity_requested_by_identifier() -> None:
    """Verify that retrieval returns the event selected by UUID."""

    # Arrange: create the event exposed by the repository boundary.
    event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 15, 19, 30, tzinfo=UTC),
        ),
    )
    repository = ReturningEventRepository(event=event)
    use_case = GetEvent(repository=repository)

    # Act: request the event through the application boundary.
    retrieved_event = use_case.execute(event_id=event.id)

    # Assert: the exact stored domain entity is returned.
    assert retrieved_event is event

    # Assert: persistence receives the requested portable identity once.
    assert repository.requested_ids == [event.id]


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
def test_get_event_rejects_non_uuid_identifiers(
    invalid_event_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: configure one valid event behind the repository boundary.
    event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 15, 19, 30, tzinfo=UTC),
        ),
    )
    repository = ReturningEventRepository(event=event)
    use_case = GetEvent(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Event identifier must be a UUID",
    ):
        use_case.execute(event_id=invalid_event_id)

    # Assert: rejection occurs before any storage interaction.
    assert repository.requested_ids == []


def test_get_event_reports_missing_identifier() -> None:
    """Ensure that an absent UUID becomes an explicit application error."""

    # Arrange: configure persistence to report no matching event.
    event_id = uuid4()
    repository = ReturningEventRepository(event=None)
    use_case = GetEvent(repository=repository)

    # Act and Assert: absence has one adapter-independent outcome.
    with pytest.raises(
        EventNotFoundError,
        match=f"Event '{event_id}' was not found",
    ):
        use_case.execute(event_id=event_id)

    # Assert: the valid identity was queried exactly once.
    assert repository.requested_ids == [event_id]
