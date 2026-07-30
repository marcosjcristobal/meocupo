"""Unit tests for the task domain entity."""

# UUID is the public type used to identify entities across system boundaries.
from uuid import UUID

# Pytest provides readable assertions for expected domain errors.
import pytest

# Import the entity and its domain types through absolute package paths.
from personal_productivity.tasks.domain.task import InvalidTaskTransitionError, Task
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


def test_task_status_cannot_be_reassigned_directly() -> None:
    """Ensure that lifecycle changes must use explicit domain methods."""

    # Arrange: create a valid pending task.
    task = Task(title="Study Docker.")

    # Act and Assert: public assignment must not bypass transition rules.
    with pytest.raises(AttributeError):
        task.status = TaskStatus.COMPLETED


def test_pending_task_can_start() -> None:
    """Verify the valid transition from pending to in progress."""

    # Arrange: every new task begins in the pending state.
    task = Task(title="Study Docker.")

    # Act: express the user's intention through a domain method.
    task.start()

    # Assert: the entity applies the expected lifecycle transition.
    assert task.status is TaskStatus.IN_PROGRESS


def test_in_progress_task_cannot_start_again() -> None:
    """Ensure that starting an already active task is rejected."""

    # Arrange: move a new task into active work.
    task = Task(title="Study Docker.")
    task.start()

    # Act and Assert: the same transition cannot be applied twice.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot start a task from 'in_progress'",
    ):
        task.start()

    # Assert: a rejected transition must leave the entity unchanged.
    assert task.status is TaskStatus.IN_PROGRESS


def test_in_progress_task_can_pause() -> None:
    """Verify the valid transition from in progress to paused."""

    # Arrange: only active work can be paused.
    task = Task(title="Study Docker.")
    task.start()

    # Act: temporarily stop active work.
    task.pause()

    # Assert: the task remains unfinished but is no longer active.
    assert task.status is TaskStatus.PAUSED


def test_pending_task_cannot_pause() -> None:
    """Ensure that work cannot be paused before it has started."""

    # Arrange: a newly created task is still pending.
    task = Task(title="Study Docker.")

    # Act and Assert: pausing requires an in-progress origin state.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot pause a task from 'pending'",
    ):
        task.pause()

    # Assert: rejection must preserve the original state.
    assert task.status is TaskStatus.PENDING


def test_paused_task_can_resume() -> None:
    """Verify the valid transition from paused back to in progress."""

    # Arrange: create an active task and pause it.
    task = Task(title="Study Docker.")
    task.start()
    task.pause()

    # Act: continue the previously paused work.
    task.resume()

    # Assert: resumed work becomes active again.
    assert task.status is TaskStatus.IN_PROGRESS


def test_pending_task_cannot_resume() -> None:
    """Ensure that work cannot resume when it has never started."""

    # Arrange: a new task has no paused work to continue.
    task = Task(title="Study Docker.")

    # Act and Assert: resuming requires a paused origin state.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot resume a task from 'pending'",
    ):
        task.resume()

    # Assert: rejection must preserve the pending state.
    assert task.status is TaskStatus.PENDING
