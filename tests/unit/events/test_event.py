"""Unit tests for the calendar event entity."""

# Datetime provides a deterministic event interval.
from datetime import UTC, datetime

# UUID verifies the portable identity assigned to each event.
from uuid import UUID

# Pytest executes the same title rule against several blank inputs.
import pytest

# Import shared calendar and event domain types.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)
from personal_productivity.events.domain.event import (
    Event,
    InvalidEventTransitionError,
)
from personal_productivity.events.domain.event_status import EventStatus


def test_new_event_uses_safe_defaults() -> None:
    """Verify the identity and lifecycle of a newly scheduled event."""

    # Arrange: create the exact interval occupied by the event.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act: create the smallest valid calendar event.
    event = Event(
        title="Boxing training.",
        time_block=time_block,
    )

    # Assert: preserve required event data and safe lifecycle defaults.
    assert isinstance(event.id, UUID)
    assert event.title == "Boxing training."
    assert event.time_block == time_block
    assert event.status is EventStatus.SCHEDULED

def test_new_events_receive_distinct_identifiers() -> None:
    """Verify that independent events cannot accidentally share identity."""

    # Arrange and Act: create two events with equivalent calendar data.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )
    first_event = Event(
        title="Boxing training.",
        time_block=time_block,
    )
    second_event = Event(
        title="Boxing training.",
        time_block=time_block,
    )

    # Assert: identity distinguishes otherwise similar event entities.
    assert first_event.id != second_event.id


def test_event_normalizes_surrounding_title_whitespace() -> None:
    """Ensure that accidental surrounding whitespace is not persisted."""

    # Arrange: create one valid calendar allocation.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act: construct an event from noisy user input.
    event = Event(
        title="   Boxing training.   ",
        time_block=time_block,
    )

    # Assert: preserve meaningful content in canonical form.
    assert event.title == "Boxing training."


@pytest.mark.parametrize(
    "blank_title",
    [
        "",
        "   ",
        "\t\n",
    ],
    ids=[
        "empty",
        "spaces",
        "control_whitespace",
    ],
)
def test_event_rejects_blank_title(
    blank_title: str,
) -> None:
    """Ensure that an event always communicates its purpose."""

    # Arrange: create one otherwise valid calendar allocation.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act and Assert: blank input cannot create a calendar entity.
    with pytest.raises(
        ValueError,
        match="Event title cannot be empty",
    ):
        Event(
            title=blank_title,
            time_block=time_block,
        )


@pytest.mark.parametrize(
    "invalid_title",
    [
        None,
        42,
        True,
    ],
    ids=[
        "none",
        "integer",
        "boolean",
    ],
)
def test_event_rejects_non_string_title(
    invalid_title: object,
) -> None:
    """Ensure that arbitrary values cannot bypass title semantics."""

    # Arrange: create one valid interval so only the title is invalid.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act and Assert: title normalization requires an actual string.
    with pytest.raises(
        TypeError,
        match="Event title must be a string",
    ):
        Event(
            title=invalid_title,
            time_block=time_block,
        )


@pytest.mark.parametrize(
    "invalid_time_block",
    [
        None,
        datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        (
            datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
            datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
        ),
    ],
    ids=[
        "none",
        "raw_datetime",
        "tuple",
    ],
)
def test_event_rejects_raw_time_block_values(
    invalid_time_block: object,
) -> None:
    """Ensure that every event uses a validated calendar interval."""

    # Act and Assert: raw scheduling values cannot create an event.
    with pytest.raises(
        TypeError,
        match="Event time block must be a CalendarTimeBlock",
    ):
        Event(
            title="Boxing training.",
            time_block=invalid_time_block,
        )

def test_event_description_is_optional() -> None:
    """Verify that an event does not require additional details."""

    # Arrange: create the mandatory calendar interval.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act: create an event without supplying a description.
    event = Event(
        title="Boxing training.",
        time_block=time_block,
    )

    # Assert: absence is represented explicitly instead of by blank text.
    assert event.description is None


def test_event_normalizes_surrounding_description_whitespace() -> None:
    """Ensure that accidental whitespace is removed from event details."""

    # Arrange: create the mandatory calendar interval.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act: create an event with meaningful but unclean description text.
    event = Event(
        title="Boxing training.",
        time_block=time_block,
        description="   Bring gloves and water.   ",
    )

    # Assert: only the meaningful content is persisted.
    assert event.description == "Bring gloves and water."


def test_event_converts_blank_description_to_none() -> None:
    """Ensure that blank event details have one canonical representation."""

    # Arrange: create the mandatory calendar interval.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act: provide description text containing only whitespace.
    event = Event(
        title="Boxing training.",
        time_block=time_block,
        description="   \t\n   ",
    )

    # Assert: blank text becomes the same value as an omitted description.
    assert event.description is None


@pytest.mark.parametrize(
    "invalid_description",
    [
        42,
        True,
        ["Bring gloves."],
    ],
    ids=[
        "integer",
        "boolean",
        "list",
    ],
)
def test_event_rejects_non_string_description(
    invalid_description: object,
) -> None:
    """Ensure that optional event details remain textual when present."""

    # Arrange: create one valid interval so only the description is invalid.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act and Assert: present descriptions must be actual strings.
    with pytest.raises(
        TypeError,
        match="Event description must be a string",
    ):
        Event(
            title="Boxing training.",
            time_block=time_block,
            description=invalid_description,
        )


def test_event_status_cannot_be_reassigned_directly() -> None:
    """Ensure that lifecycle changes require explicit domain operations."""

    # Arrange: create a normally scheduled event.
    event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
        ),
    )

    # Act and Assert: public assignment cannot bypass lifecycle rules.
    with pytest.raises(AttributeError):
        event.status = EventStatus.CANCELLED  # type: ignore[misc]

    # Assert: the rejected assignment leaves the event unchanged.
    assert event.status is EventStatus.SCHEDULED


def test_scheduled_event_can_be_cancelled() -> None:
    """Verify the valid transition from scheduled to cancelled."""

    # Arrange: create an event that is still expected to take place.
    event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
        ),
    )

    # Act: express cancellation through an explicit domain operation.
    event.cancel()

    # Assert: the durable lifecycle state records the cancellation.
    assert event.status is EventStatus.CANCELLED

def test_cancelled_event_cannot_be_cancelled_again() -> None:
    """Ensure that event cancellation cannot be applied repeatedly."""

    # Arrange: move a scheduled event into its terminal cancelled state.
    event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
        ),
    )
    event.cancel()

    # Act and Assert: the terminal transition cannot be repeated.
    with pytest.raises(
        InvalidEventTransitionError,
        match="Cannot cancel an event from 'cancelled'",
    ):
        event.cancel()

    # Assert: rejection preserves the authoritative terminal state.
    assert event.status is EventStatus.CANCELLED

def test_scheduled_event_can_be_rescheduled() -> None:
    """Verify that an active event may move to another calendar interval."""

    # Arrange: create an event with its original calendar allocation.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )
    replacement_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 7, 19, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 7, 20, 30, tzinfo=UTC),
    )
    event = Event(
        title="Boxing training.",
        time_block=original_time_block,
    )

    # Act: replace the calendar allocation through a domain operation.
    event.reschedule(time_block=replacement_time_block)

    # Assert: scheduling changes without inventing a lifecycle state.
    assert event.time_block is replacement_time_block
    assert event.status is EventStatus.SCHEDULED


@pytest.mark.parametrize(
    "invalid_time_block",
    [
        None,
        datetime(2026, 8, 7, 19, 0, tzinfo=UTC),
        (
            datetime(2026, 8, 7, 19, 0, tzinfo=UTC),
            datetime(2026, 8, 7, 20, 30, tzinfo=UTC),
        ),
    ],
    ids=[
        "none",
        "raw_datetime",
        "tuple",
    ],
)
def test_reschedule_rejects_raw_time_block_values(
    invalid_time_block: object,
) -> None:
    """Ensure that rescheduling cannot bypass the calendar value object."""

    # Arrange: preserve the valid allocation so rejection can be verified.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )
    event = Event(
        title="Boxing training.",
        time_block=original_time_block,
    )

    # Act and Assert: raw interval data cannot cross the domain boundary.
    with pytest.raises(
        TypeError,
        match="Event time block must be a CalendarTimeBlock",
    ):
        event.reschedule(time_block=invalid_time_block)

    # Assert: rejection leaves the previous allocation untouched.
    assert event.time_block is original_time_block


def test_cancelled_event_cannot_be_rescheduled() -> None:
    """Ensure that cancelled event scheduling remains historical."""

    # Arrange: cancel an event while preserving its original allocation.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )
    replacement_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 7, 19, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 7, 20, 30, tzinfo=UTC),
    )
    event = Event(
        title="Boxing training.",
        time_block=original_time_block,
    )
    event.cancel()

    # Act and Assert: terminal events cannot receive new planning decisions.
    with pytest.raises(
        InvalidEventTransitionError,
        match="Cannot reschedule an event from 'cancelled'",
    ):
        event.reschedule(time_block=replacement_time_block)

    # Assert: rejection preserves both scheduling and lifecycle state.
    assert event.time_block is original_time_block
    assert event.status is EventStatus.CANCELLED
