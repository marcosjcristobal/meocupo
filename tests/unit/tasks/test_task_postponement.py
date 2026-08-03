"""Unit tests for explicit task postponement behavior."""

# Date and datetime provide deterministic calendar and instant deadlines.
from datetime import UTC, date, datetime

# Pytest executes the same boundary rule against several invalid values.
import pytest

# Import the task entity and its deadline value object.
from personal_productivity.tasks.domain.task import (
    InvalidTaskPostponementError,
    Task,
    TaskNotEditableError,
)
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


def test_date_only_deadline_can_be_postponed() -> None:
    """Verify that postponement moves a deadline without changing lifecycle."""

    # Arrange: create an unfinished task with an existing calendar deadline.
    original_deadline = TaskDeadline(due_on=date(2026, 8, 15))
    postponed_deadline = TaskDeadline(due_on=date(2026, 8, 20))
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )
    original_status = task.status

    # Act: express postponement as an explicit domain operation.
    task.postpone(deadline=postponed_deadline)

    # Assert: the temporal commitment moves to the later date.
    assert task.deadline == postponed_deadline

    # Assert: analytics can distinguish postponement from initial scheduling.
    assert task.postponement_count == 1

    # Assert: postponement does not pretend that work changed lifecycle state.
    assert task.status is original_status


@pytest.mark.parametrize(
    "invalid_deadline",
    [
        date(2026, 8, 20),
        "2026-08-20",
        None,
    ],
    ids=[
        "raw_date",
        "text",
        "none",
    ],
)
def test_postponement_rejects_raw_deadline_values(
    invalid_deadline: object,
) -> None:
    """Ensure that postponement cannot bypass the deadline value object."""

    # Arrange: preserve the original state so rejection can be verified fully.
    original_deadline = TaskDeadline(due_on=date(2026, 8, 15))
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )

    # Act and Assert: only a validated TaskDeadline may cross this boundary.
    with pytest.raises(
        TypeError,
        match="Task deadline must be a TaskDeadline",
    ):
        task.postpone(deadline=invalid_deadline)

    # Assert: failed operations must not mutate planning or analytics.
    assert task.deadline == original_deadline
    assert task.postponement_count == 0


def test_completed_task_cannot_be_postponed() -> None:
    """Ensure that completed task planning remains historical."""

    # Arrange: complete a task that still contains its original deadline.
    original_deadline = TaskDeadline(due_on=date(2026, 8, 15))
    postponed_deadline = TaskDeadline(due_on=date(2026, 8, 20))
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )
    task.complete(
        completed_at=datetime(2026, 8, 14, 18, 0, tzinfo=UTC),
    )

    # Act and Assert: completed work cannot receive new planning decisions.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot postpone deadline for a task in 'completed'",
    ):
        task.postpone(deadline=postponed_deadline)

    # Assert: rejection preserves both history and analytics.
    assert task.deadline == original_deadline
    assert task.postponement_count == 0


def test_cancelled_task_cannot_be_postponed() -> None:
    """Ensure that cancelled task planning remains historical."""

    # Arrange: cancel a task that still contains its original deadline.
    original_deadline = TaskDeadline(due_on=date(2026, 8, 15))
    postponed_deadline = TaskDeadline(due_on=date(2026, 8, 20))
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )
    task.cancel()

    # Act and Assert: abandoned work cannot receive new planning decisions.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot postpone deadline for a task in 'cancelled'",
    ):
        task.postpone(deadline=postponed_deadline)

    # Assert: rejection preserves both history and analytics.
    assert task.deadline == original_deadline
    assert task.postponement_count == 0


def test_undated_task_cannot_be_postponed() -> None:
    """Ensure that initial scheduling is not counted as postponement."""

    # Arrange: create an undated task and a possible initial deadline.
    task = Task(title="Renew the insurance.")
    proposed_deadline = TaskDeadline(due_on=date(2026, 8, 20))

    # Act and Assert: postponement requires a previous temporal commitment.
    with pytest.raises(
        InvalidTaskPostponementError,
        match="Cannot postpone a task without an existing deadline",
    ):
        task.postpone(deadline=proposed_deadline)

    # Assert: rejection cannot silently schedule or alter analytics.
    assert task.deadline is None
    assert task.postponement_count == 0

@pytest.mark.parametrize(
    "proposed_due_on",
    [
        date(2026, 8, 15),
        date(2026, 8, 14),
    ],
    ids=[
        "same_date",
        "earlier_date",
    ],
)
def test_date_only_postponement_requires_a_later_date(
    proposed_due_on: date,
) -> None:
    """Ensure that calendar postponement moves strictly forward."""

    # Arrange: create a task with an existing calendar commitment.
    original_deadline = TaskDeadline(due_on=date(2026, 8, 15))
    proposed_deadline = TaskDeadline(due_on=proposed_due_on)
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )

    # Act and Assert: equal or earlier dates are not postponements.
    with pytest.raises(
        InvalidTaskPostponementError,
        match="Postponed deadline must be later than the current deadline",
    ):
        task.postpone(deadline=proposed_deadline)

    # Assert: rejection preserves both the original deadline and its count.
    assert task.deadline == original_deadline
    assert task.postponement_count == 0


def test_exact_deadline_can_be_postponed() -> None:
    """Verify that an exact deadline may move to a later instant."""

    # Arrange: create two globally comparable deadline instants.
    original_deadline = TaskDeadline(
        due_at=datetime(2026, 8, 15, 18, 0, tzinfo=UTC),
    )
    postponed_deadline = TaskDeadline(
        due_at=datetime(2026, 8, 15, 20, 0, tzinfo=UTC),
    )
    task = Task(
        title="Submit the report.",
        deadline=original_deadline,
    )
    original_status = task.status

    # Act: postpone the exact deadline by two hours.
    task.postpone(deadline=postponed_deadline)

    # Assert: planning and analytics change while lifecycle remains stable.
    assert task.deadline == postponed_deadline
    assert task.postponement_count == 1
    assert task.status is original_status


@pytest.mark.parametrize(
    "proposed_due_at",
    [
        datetime(2026, 8, 15, 18, 0, tzinfo=UTC),
        datetime(2026, 8, 15, 17, 59, tzinfo=UTC),
    ],
    ids=[
        "same_instant",
        "earlier_instant",
    ],
)
def test_exact_postponement_requires_a_later_instant(
    proposed_due_at: datetime,
) -> None:
    """Ensure that exact postponement moves strictly forward in time."""

    # Arrange: create an existing deadline and a proposed replacement.
    original_deadline = TaskDeadline(
        due_at=datetime(2026, 8, 15, 18, 0, tzinfo=UTC),
    )
    proposed_deadline = TaskDeadline(due_at=proposed_due_at)
    task = Task(
        title="Submit the report.",
        deadline=original_deadline,
    )

    # Act and Assert: equal or earlier instants are not postponements.
    with pytest.raises(
        InvalidTaskPostponementError,
        match="Postponed deadline must be later than the current deadline",
    ):
        task.postpone(deadline=proposed_deadline)

    # Assert: rejection preserves both the original deadline and its count.
    assert task.deadline == original_deadline
    assert task.postponement_count == 0

@pytest.mark.parametrize(
    ("original_deadline", "proposed_deadline"),
    [
        (
            TaskDeadline(due_on=date(2026, 8, 15)),
            TaskDeadline(
                due_at=datetime(2026, 8, 16, 18, 0, tzinfo=UTC),
            ),
        ),
        (
            TaskDeadline(
                due_at=datetime(2026, 8, 15, 18, 0, tzinfo=UTC),
            ),
            TaskDeadline(due_on=date(2026, 8, 16)),
        ),
    ],
    ids=[
        "date_to_exact_instant",
        "exact_instant_to_date",
    ],
)
def test_postponement_preserves_deadline_precision(
    original_deadline: TaskDeadline,
    proposed_deadline: TaskDeadline,
) -> None:
    """Ensure that postponement never invents cross-precision ordering."""

    # Arrange: create a task using the original deadline representation.
    task = Task(
        title="Submit the report.",
        deadline=original_deadline,
    )

    # Act and Assert: changing precision is rescheduling, not postponement.
    with pytest.raises(
        InvalidTaskPostponementError,
        match="Postponement must preserve deadline precision",
    ):
        task.postpone(deadline=proposed_deadline)

    # Assert: rejection preserves planning and postponement analytics.
    assert task.deadline == original_deadline
    assert task.postponement_count == 0


def test_successive_postponements_increment_the_count() -> None:
    """Verify that every successful postponement contributes to analytics."""

    # Arrange: create a task with its original calendar deadline.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )
    first_postponement = TaskDeadline(due_on=date(2026, 8, 20))
    second_postponement = TaskDeadline(due_on=date(2026, 8, 25))

    # Act: postpone the same task through two valid forward movements.
    task.postpone(deadline=first_postponement)
    task.postpone(deadline=second_postponement)

    # Assert: retain the latest commitment and count both user decisions.
    assert task.deadline == second_postponement
    assert task.postponement_count == 2


@pytest.mark.parametrize(
    "pause_before_postponement",
    [
        False,
        True,
    ],
    ids=[
        "in_progress",
        "paused",
    ],
)
def test_postponement_preserves_active_lifecycle_state(
    pause_before_postponement: bool,
) -> None:
    """Ensure that planning changes do not alter execution state."""

    # Arrange: begin work and optionally pause it before replanning.
    task = Task(
        title="Submit the report.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )
    task.start()
    if pause_before_postponement:
        task.pause()
    original_status = task.status

    # Act: move the deadline while preserving the work lifecycle.
    task.postpone(
        deadline=TaskDeadline(due_on=date(2026, 8, 20)),
    )

    # Assert: only planning and postponement analytics may change.
    assert task.status is original_status
    assert task.postponement_count == 1


def test_postponement_count_cannot_be_reassigned_directly() -> None:
    """Ensure that external code cannot rewrite postponement analytics."""

    # Arrange: create a task whose count begins at the safe default.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )

    # Act and Assert: only successful domain operations may change the count.
    with pytest.raises(AttributeError):
        task.postponement_count = 99

    # Assert: rejected assignment preserves the original analytics value.
    assert task.postponement_count == 0