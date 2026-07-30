"""Unit tests for the task priority levels."""

# Import the domain type through its absolute application package path.
from personal_productivity.tasks.domain.task_priority import TaskPriority


def test_normal_priority_has_stable_serializable_value() -> None:
    """Verify that normal priority keeps its external representation stable."""

    # The value may cross JSON and database boundaries, so it must remain stable.
    assert TaskPriority.NORMAL.value == "normal"


def test_enum_contains_only_explicit_priority_levels() -> None:
    """Ensure that urgency is not represented as a manually assigned priority."""

    # Arrange: define every priority that a user may explicitly assign.
    expected_values = {
        "critical",
        "high",
        "normal",
        "low",
    }

    # Act: extract the external value of every declared priority.
    actual_values = {priority.value for priority in TaskPriority}

    # Assert: no required or unexpected priority may be present.
    assert actual_values == expected_values
