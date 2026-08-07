"""Unit tests for the task creation application use case."""

# Date and datetime build deterministic planning values for the test.
from datetime import UTC, date, datetime

# Pytest verifies that domain validation crosses the application boundary.
import pytest

# Import the use case that coordinates creation and persistence.
from personal_productivity.tasks.application.create_task import CreateTask

# The recording repository stores real domain entities for verification.
from personal_productivity.tasks.domain.task import Task

# Priority is an explicit domain value rather than an arbitrary string.
from personal_productivity.tasks.domain.task_priority import TaskPriority

# CalendarTimeBlock represents reserved work in the shared calendar.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# TaskDeadline preserves either calendar-date or exact-instant intent.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


class RecordingTaskRepository:
    """Record added tasks without requiring a real database."""

    def __init__(self) -> None:
        """Start with no recorded persistence operations."""

        # A list preserves both the saved entities and their insertion order.
        self.added_tasks: list[Task] = []

    def add(self, task: Task) -> None:
        """Record the entity that the use case attempted to persist."""

        # This test double replaces a future SQLite adapter.
        self.added_tasks.append(task)


def test_create_task_builds_and_persists_domain_entity() -> None:
    """Verify that creation saves and returns the same valid task."""

    # Arrange: inject an observable repository into the use case.
    repository = RecordingTaskRepository()
    use_case = CreateTask(repository=repository)

    # Act: request task creation through the application boundary.
    created_task = use_case.execute(
        title="Buy soil for the pitaya.",
    )

    # Assert: the use case returns the normalized domain entity.
    assert isinstance(created_task, Task)
    assert created_task.title == "Buy soil for the pitaya."

    # Assert: persistence receives exactly the entity returned to the caller.
    assert repository.added_tasks == [created_task]


def test_create_task_does_not_persist_invalid_entity() -> None:
    """Ensure that domain validation happens before persistence."""

    # Arrange: inject a repository whose writes can be inspected.
    repository = RecordingTaskRepository()
    use_case = CreateTask(repository=repository)

    # Act and Assert: an invalid title propagates the domain error.
    with pytest.raises(
        ValueError,
        match="Task title cannot be empty",
    ):
        use_case.execute(title="   ")

    # Assert: failed construction never reaches persistent storage.
    assert repository.added_tasks == []


def test_create_task_forwards_optional_description() -> None:
    """Verify that the use case passes optional details to the domain."""

    # Arrange: prepare the use case with an observable repository.
    repository = RecordingTaskRepository()
    use_case = CreateTask(repository=repository)

    # Act: create a task containing unnormalized external input.
    created_task = use_case.execute(
        title="Study Docker.",
        description="   Complete the networking chapter.   ",
    )

    # Assert: the domain, not the use case, normalizes the description.
    assert created_task.description == "Complete the networking chapter."

    # Assert: the normalized entity is the value sent to persistence.
    assert repository.added_tasks == [created_task]


def test_create_task_forwards_estimate_and_priority() -> None:
    """Verify that task planning values reach the domain entity."""

    # Arrange: prepare an observable persistence boundary.
    repository = RecordingTaskRepository()
    use_case = CreateTask(repository=repository)

    # Act: create a task with explicit effort and importance.
    created_task = use_case.execute(
        title="Prepare the investor presentation.",
        estimated_minutes=90,
        priority=TaskPriority.HIGH,
    )

    # Assert: the domain entity preserves both validated planning values.
    assert created_task.estimated_minutes == 90
    assert created_task.priority is TaskPriority.HIGH

    # Assert: persistence receives the complete configured entity.
    assert repository.added_tasks == [created_task]


def test_create_task_forwards_initial_temporal_planning() -> None:
    """Verify that deadlines and work allocations remain separate concepts."""

    # Arrange: define when work is planned and when it must be finished.
    repository = RecordingTaskRepository()
    use_case = CreateTask(repository=repository)
    deadline = TaskDeadline(
        due_on=date(2026, 8, 10),
    )
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 8, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 8, 19, 30, tzinfo=UTC),
    )

    # Act: create a task containing both temporal planning decisions.
    created_task = use_case.execute(
        title="Prepare the investor presentation.",
        deadline=deadline,
        time_block=time_block,
    )

    # Assert: neither temporal concept replaces or modifies the other.
    assert created_task.deadline is deadline
    assert created_task.time_block is time_block

    # Assert: persistence receives the fully planned entity.
    assert repository.added_tasks == [created_task]
