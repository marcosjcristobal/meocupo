"""Unit tests for the task lifecycle states."""

# Import the domain type through its absolute application package path.
from personal_productivity.tasks.domain.task_status import TaskStatus


def test_pending_status_has_stable_serializable_value() -> None:
    """Verify that the pending state keeps its external representation stable."""

    # The value may be stored in JSON or PostgreSQL, so changing it could break data.
    assert TaskStatus.PENDING.value == "pending"


def test_enum_contains_only_persisted_lifecycle_states() -> None:
    """Ensure that calculated properties are not added as lifecycle states."""

    # Arrange: define the complete set of states allowed by the domain design.
    expected_values = {
        "pending",
        "in_progress",
        "paused",
        "completed",
        "cancelled",
    }

    # Act: extract the external value of every member declared in TaskStatus.
    actual_values = {status.value for status in TaskStatus}

    # Assert: both sets must contain exactly the same values.
    assert actual_values == expected_values