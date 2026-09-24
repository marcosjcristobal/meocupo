"""Unit tests for restoring persisted event domain state."""

# Datetime builds one deterministic calendar allocation.
from datetime import UTC, datetime

# UUID provides a stable identity for the restored entity.
from uuid import uuid4

# Pytest verifies rejection of malformed persisted state.
import pytest

# CalendarTimeBlock validates the restored temporal allocation.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Rehydration belongs to the event domain entity.
from personal_productivity.events.domain.event import Event

# EventStatus defines the valid persisted lifecycle vocabulary.
from personal_productivity.events.domain.event_status import EventStatus


def test_cancelled_event_can_be_rehydrated() -> None:
    """Verify that historical cancellation is restored directly."""

    # Arrange: define the persisted identity and interval explicitly.
    event_id = uuid4()
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
    )

    # Act: reconstruct the entity without replaying cancellation.
    event = Event.rehydrate(
        id=event_id,
        title="   Boxing training.   ",
        description="   Bring the red gloves.   ",
        time_block=time_block,
        status=EventStatus.CANCELLED,
    )

    # Assert: both historical state and regular normalization survive.
    assert event.id == event_id
    assert event.title == "Boxing training."
    assert event.description == "Bring the red gloves."
    assert event.time_block == time_block
    assert event.status is EventStatus.CANCELLED


@pytest.mark.parametrize(
    "invalid_status",
    [None, "cancelled", 42],
    ids=["none", "text", "integer"],
)
def test_rehydration_rejects_non_status_values(
    invalid_status: object,
) -> None:
    """Ensure that persisted lifecycle state uses EventStatus."""

    # Arrange: supply every other required field in valid form.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
    )

    # Act and Assert: raw persistence values cannot replace the enum.
    with pytest.raises(
        TypeError,
        match="Rehydrated status must be an EventStatus",
    ):
        Event.rehydrate(
            id=uuid4(),
            title="Boxing training.",
            time_block=time_block,
            status=invalid_status,
        )


@pytest.mark.parametrize(
    "invalid_event_id",
    [None, "not-a-uuid", 42],
    ids=["none", "text", "integer"],
)
def test_rehydration_rejects_non_uuid_identifiers(
    invalid_event_id: object,
) -> None:
    """Ensure that restored identities retain their UUID type."""

    # Arrange: supply valid lifecycle and calendar state.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
    )

    # Act and Assert: malformed identities cannot enter the domain.
    with pytest.raises(
        TypeError,
        match="Rehydrated event identifier must be a UUID",
    ):
        Event.rehydrate(
            id=invalid_event_id,
            title="Boxing training.",
            time_block=time_block,
            status=EventStatus.SCHEDULED,
        )
