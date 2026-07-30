"""Unit tests for the task domain entity."""

# UUID is the public type used to identify entities across system boundaries.
from uuid import UUID

# Pytest provides readable assertions for expected domain errors.
import pytest

# Import the entity and its domain types through absolute package paths.
from personal_productivity.tasks.domain.task import Task
from personal_productivity.tasks.domain.task_priority import TaskPriority
from personal_productivity.tasks.domain.task_status import TaskStatus


def test_new_task_uses_safe_lifecycle_defaults() -> None:
    """Verify that a new task starts pending and with normal priority."""

    # Arrange and Act: create the smallest useful task.
    task = Task(title="Buy soil for the pitaya.")

    # Assert: callers receive predictable defaults without supplying them.
    assert task.status is TaskStatus.PENDING
    assert task.priority is TaskPriority.NORMAL


def test_new_tasks_receive_distinct_identifiers() -> None:
    """Verify that every task receives an independent UUID identity."""

    # Arrange and Act: create two tasks without manually assigning identifiers.
    first_task = Task(title="Buy soil for the pitaya.")
    second_task = Task(title="Renew the insurance.")

    # Assert: both identifiers use the expected type and cannot be shared.
    assert isinstance(first_task.id, UUID)
    assert isinstance(second_task.id, UUID)
    assert first_task.id != second_task.id

def test_task_rejects_blank_title() -> None:
    """Ensure that whitespace alone cannot describe a task."""

    # Act and Assert: construction must stop when the title has no content.
    with pytest.raises(ValueError, match="Task title cannot be empty"):
        Task(title="   ")
