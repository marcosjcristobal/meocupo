"""Unit tests for the task domain entity."""

# Datetime provides an explicit, timezone-aware completion instant.
from datetime import UTC, date, datetime
# UUID is the public type used to identify entities across system boundaries.
from uuid import UUID

# Pytest provides readable assertions for expected domain errors.
import pytest

# Import the entity and its domain types through absolute package paths.
from personal_productivity.tasks.domain.task import (
    InvalidTaskTransitionError,
    Task,
    TaskNotEditableError,
    )
from personal_productivity.tasks.domain.task_priority import TaskPriority
from personal_productivity.tasks.domain.task_status import TaskStatus
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


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

def test_pending_task_can_complete_with_timestamp() -> None:
    """Verify that direct completion records state and time together."""

    # Arrange: use a fixed instant so the test never depends on the real clock.
    task = Task(title="Buy soil for the pitaya.")
    completed_at = datetime(2026, 7, 30, 10, 30, tzinfo=UTC)

    # Act: complete the task with an explicit timestamp.
    task.complete(completed_at=completed_at)

    # Assert: lifecycle state and completion time change atomically.
    assert task.status is TaskStatus.COMPLETED
    assert task.completed_at == completed_at

def test_in_progress_task_can_complete() -> None:
    """Verify that active work may be marked as completed."""

    # Arrange: start the task and choose a deterministic completion instant.
    task = Task(title="Study Docker.")
    task.start()
    completed_at = datetime(2026, 7, 30, 11, 0, tzinfo=UTC)

    # Act: finish the active task.
    task.complete(completed_at=completed_at)

    # Assert: state and timestamp represent the same completion.
    assert task.status is TaskStatus.COMPLETED
    assert task.completed_at == completed_at


def test_paused_task_can_complete() -> None:
    """Verify that paused work may be completed without resuming first."""

    # Arrange: some tasks are finished while formally paused.
    task = Task(title="Study Docker.")
    task.start()
    task.pause()
    completed_at = datetime(2026, 7, 30, 11, 30, tzinfo=UTC)

    # Act: record completion directly from the paused state.
    task.complete(completed_at=completed_at)

    # Assert: the paused task reaches its terminal completed state.
    assert task.status is TaskStatus.COMPLETED
    assert task.completed_at == completed_at


def test_completed_task_cannot_complete_again() -> None:
    """Ensure that repeated completion cannot rewrite historical metadata."""

    # Arrange: complete the task once with its authoritative timestamp.
    task = Task(title="Study Docker.")
    original_completed_at = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    replacement_completed_at = datetime(2026, 7, 30, 13, 0, tzinfo=UTC)
    task.complete(completed_at=original_completed_at)

    # Act and Assert: a terminal task cannot be completed a second time.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot complete a task from 'completed'",
    ):
        task.complete(completed_at=replacement_completed_at)

    # Assert: rejection preserves the original historical timestamp.
    assert task.status is TaskStatus.COMPLETED
    assert task.completed_at == original_completed_at

def test_task_rejects_naive_completion_timestamp() -> None:
    """Ensure that completion instants always identify an absolute moment."""

    # Arrange: a naive datetime has no timezone or UTC offset.
    task = Task(title="Study Docker.")
    naive_completed_at = datetime(2026, 7, 30, 14, 0)

    # Act and Assert: ambiguous timestamps must be rejected.
    with pytest.raises(
        ValueError,
        match="Completion time must include a timezone",
    ):
        task.complete(completed_at=naive_completed_at)

    # Assert: validation failure must leave all lifecycle data unchanged.
    assert task.status is TaskStatus.PENDING
    assert task.completed_at is None

def test_pending_task_can_be_cancelled() -> None:
    """Verify that unstarted work may be intentionally abandoned."""

    # Arrange: a new task has not begun and has no completion timestamp.
    task = Task(title="Buy soil for the pitaya.")

    # Act: intentionally abandon the task.
    task.cancel()

    # Assert: cancellation is terminal but is not completion.
    assert task.status is TaskStatus.CANCELLED
    assert task.completed_at is None


def test_in_progress_task_can_be_cancelled() -> None:
    """Verify that active work may be intentionally abandoned."""

    # Arrange: move the task into active work.
    task = Task(title="Study Docker.")
    task.start()

    # Act: stop pursuing the task permanently.
    task.cancel()

    # Assert: active work becomes cancelled, not completed.
    assert task.status is TaskStatus.CANCELLED
    assert task.completed_at is None


def test_paused_task_can_be_cancelled() -> None:
    """Verify that paused work may be intentionally abandoned."""

    # Arrange: begin the task and then pause it.
    task = Task(title="Study Docker.")
    task.start()
    task.pause()

    # Act: abandon the paused task.
    task.cancel()

    # Assert: cancellation does not require resuming first.
    assert task.status is TaskStatus.CANCELLED
    assert task.completed_at is None


def test_completed_task_cannot_be_cancelled() -> None:
    """Ensure that cancellation cannot rewrite a successful outcome."""

    # Arrange: complete the task with authoritative historical metadata.
    task = Task(title="Study Docker.")
    completed_at = datetime(2026, 7, 30, 15, 0, tzinfo=UTC)
    task.complete(completed_at=completed_at)

    # Act and Assert: completed work cannot later become abandoned work.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot cancel a task from 'completed'",
    ):
        task.cancel()

    # Assert: the rejected transition preserves completion metadata.
    assert task.status is TaskStatus.COMPLETED
    assert task.completed_at == completed_at

def test_cancelled_task_cannot_be_cancelled_again() -> None:
    """Ensure that repeated cancellation is rejected explicitly."""

    # Arrange: cancel an unfinished task once.
    task = Task(title="Study Docker.")
    task.cancel()

    # Act and Assert: cancellation is a terminal transition.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot cancel a task from 'cancelled'",
    ):
        task.cancel()

    # Assert: the rejected operation preserves cancellation.
    assert task.status is TaskStatus.CANCELLED


def test_cancelled_task_cannot_be_completed() -> None:
    """Ensure that abandoned work cannot later become successful work."""

    # Arrange: cancel the task and prepare an otherwise valid timestamp.
    task = Task(title="Study Docker.")
    task.cancel()
    completed_at = datetime(2026, 7, 30, 16, 0, tzinfo=UTC)

    # Act and Assert: completion cannot replace cancellation history.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot complete a task from 'cancelled'",
    ):
        task.complete(completed_at=completed_at)

    # Assert: rejected completion creates no completion metadata.
    assert task.status is TaskStatus.CANCELLED
    assert task.completed_at is None

def test_task_normalizes_surrounding_title_whitespace() -> None:
    """Ensure that accidental surrounding whitespace is not persisted."""

    # Act: create a task with whitespace introduced by user input.
    task = Task(title="   Study Docker.   ")

    # Assert: meaningful content remains while surrounding noise is removed.
    assert task.title == "Study Docker."

def test_task_description_is_optional() -> None:
    """Verify that a task may exist without additional explanation."""

    # Act: create the smallest valid task.
    task = Task(title="Study Docker.")

    # Assert: absence has one explicit representation.
    assert task.description is None


def test_task_normalizes_surrounding_description_whitespace() -> None:
    """Ensure that accidental surrounding whitespace is not persisted."""

    # Act: create a task with a user-provided description.
    task = Task(
        title="Study Docker.",
        description="   Complete the networking chapter.   ",
    )

    # Assert: preserve content while removing surrounding noise.
    assert task.description == "Complete the networking chapter."


def test_task_converts_blank_description_to_none() -> None:
    """Ensure that blank and absent descriptions share one representation."""

    # Act: whitespace communicates no additional information.
    task = Task(title="Study Docker.", description="   ")

    # Assert: avoid storing an ambiguous empty string.
    assert task.description is None

def test_estimated_minutes_are_optional() -> None:
    """Verify that a task may exist before its effort is estimated."""

    # Act: create a task without planning its duration.
    task = Task(title="Study Docker.")

    # Assert: missing estimation has one explicit representation.
    assert task.estimated_minutes is None


def test_task_accepts_positive_estimated_minutes() -> None:
    """Verify that a positive whole-minute estimate is preserved."""

    # Act: create a task with one hour of estimated work.
    task = Task(title="Study Docker.", estimated_minutes=60)

    # Assert: retain the exact value for planning and analytics.
    assert task.estimated_minutes == 60


@pytest.mark.parametrize("invalid_minutes", [0, -1])
def test_task_rejects_non_positive_estimated_minutes(
    invalid_minutes: int,
) -> None:
    """Ensure that an existing estimate always represents real duration."""

    # Act and Assert: zero and negative durations have no domain meaning.
    with pytest.raises(
        ValueError,
        match="Estimated minutes must be greater than zero",
    ):
        Task(
            title="Study Docker.",
            estimated_minutes=invalid_minutes,
        )

@pytest.mark.parametrize("invalid_minutes", [True, 1.5, "60"])
def test_task_rejects_non_integer_estimated_minutes(
    invalid_minutes: object,
) -> None:
    """Ensure that duration is represented by whole minutes only."""

    # Act and Assert: booleans, decimals, and strings are not minute counts.
    with pytest.raises(
        TypeError,
        match="Estimated minutes must be an integer",
    ):
        Task(
            title="Study Docker.",
            estimated_minutes=invalid_minutes,
        )

def test_task_deadline_is_optional() -> None:
    """Verify that a task may exist before a deadline is assigned."""

    # Act: create a task without temporal constraints.
    task = Task(title="Study Docker.")

    # Assert: no deadline has one explicit representation.
    assert task.deadline is None


def test_task_accepts_valid_deadline_value_object() -> None:
    """Verify that Task stores an already validated deadline."""

    # Arrange: preserve the user's date-only intent.
    deadline = TaskDeadline(due_on=date(2026, 8, 15))

    # Act: assign the value object during task creation.
    task = Task(title="Renew the insurance.", deadline=deadline)

    # Assert: the entity retains the immutable value object.
    assert task.deadline == deadline


def test_task_rejects_raw_deadline_values() -> None:
    """Ensure that callers cannot bypass TaskDeadline validation."""

    # Act and Assert: raw dates must first become validated value objects.
    with pytest.raises(
        TypeError,
        match="Task deadline must be a TaskDeadline",
    ):
        Task(
            title="Renew the insurance.",
            deadline=date(2026, 8, 15),
        )

def test_task_can_replace_deadline() -> None:
    """Verify that an unfinished task may receive a new deadline."""

    # Arrange: create the original and replacement deadline values.
    original_deadline = TaskDeadline(due_on=date(2026, 8, 15))
    replacement_deadline = TaskDeadline(due_on=date(2026, 8, 20))
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )

    # Act: replace the deadline through an explicit domain operation.
    task.set_deadline(replacement_deadline)

    # Assert: the new immutable value replaces the old one.
    assert task.deadline == replacement_deadline


def test_task_can_clear_deadline() -> None:
    """Verify that an unfinished task may become undated."""

    # Arrange: create a task with an existing deadline.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )

    # Act: remove the temporal constraint explicitly.
    task.clear_deadline()

    # Assert: absence returns to its canonical representation.
    assert task.deadline is None


def test_set_deadline_rejects_raw_values() -> None:
    """Ensure that deadline changes cannot bypass the value object."""

    # Arrange: create an otherwise valid task.
    task = Task(title="Renew the insurance.")

    # Act and Assert: raw dates are not accepted by domain operations.
    with pytest.raises(
        TypeError,
        match="Task deadline must be a TaskDeadline",
    ):
        task.set_deadline(date(2026, 8, 15))

def test_completed_task_cannot_replace_deadline() -> None:
    """Ensure that completed task planning remains historical."""

    # Arrange: complete a task that already has a deadline.
    original_deadline = TaskDeadline(due_on=date(2026, 8, 15))
    replacement_deadline = TaskDeadline(due_on=date(2026, 8, 20))
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )
    task.complete(
        completed_at=datetime(2026, 8, 14, 18, 0, tzinfo=UTC),
    )

    # Act and Assert: terminal tasks cannot be rescheduled.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot change deadline for a task in 'completed'",
    ):
        task.set_deadline(replacement_deadline)

    # Assert: rejection preserves historical planning.
    assert task.deadline == original_deadline


def test_cancelled_task_cannot_clear_deadline() -> None:
    """Ensure that cancelled task planning remains historical."""

    # Arrange: cancel a task that has an existing deadline.
    original_deadline = TaskDeadline(due_on=date(2026, 8, 15))
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )
    task.cancel()

    # Act and Assert: terminal tasks cannot lose their historical deadline.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot clear deadline for a task in 'cancelled'",
    ):
        task.clear_deadline()

    # Assert: rejection preserves the original deadline.
    assert task.deadline == original_deadline
