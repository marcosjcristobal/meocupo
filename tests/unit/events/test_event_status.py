"""Unit tests for persisted event lifecycle states."""

# Import the domain enum through its absolute package path.
from personal_productivity.events.domain.event_status import EventStatus


def test_scheduled_status_has_stable_serializable_value() -> None:
    """Verify that scheduled events keep a stable external representation."""

    # The value may cross API and database boundaries.
    assert EventStatus.SCHEDULED.value == "scheduled"


def test_enum_contains_only_persisted_event_states() -> None:
    """Ensure that derived time conditions do not become stored states."""

    # Arrange: define only durable event lifecycle outcomes.
    expected_values = {
        "scheduled",
        "cancelled",
    }

    # Act: extract every external value declared by the enum.
    actual_values = {status.value for status in EventStatus}

    # Assert: ongoing, past, and rescheduled remain calculated or historical.
    assert actual_values == expected_values