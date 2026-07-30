"""Unit tests for calculated task overdue behavior."""

# Date and datetime provide deterministic local and absolute references.
from datetime import UTC, date, datetime

# Pytest executes the same rule against multiple temporal scenarios.
import pytest

# Import the entity and deadline value object through domain package paths.
from personal_productivity.tasks.domain.task import Task
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


def test_undated_task_is_not_overdue() -> None:
    """Verify that missing deadlines cannot produce artificial delay."""

    # Arrange: provide deterministic references despite having no deadline.
    task = Task(title="Study Docker.")
    today = date(2026, 8, 15)
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    # Act and Assert: an undated task is never overdue.
    assert task.is_overdue(today=today, now=now) is False


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 8, 15), False),
        (date(2026, 8, 16), True),
    ],
    ids=["on_due_date", "after_due_date"],
)
def test_date_only_deadline_uses_local_calendar_date(
    today: date,
    expected: bool,
) -> None:
    """Verify that a date-only task becomes overdue the following day."""

    # Arrange: the user supplied a date but no artificial time.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    # Act and Assert: compare calendar dates rather than clock times.
    assert task.is_overdue(today=today, now=now) is expected

@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 8, 15, 18, 0, tzinfo=UTC), False),
        (datetime(2026, 8, 15, 18, 1, tzinfo=UTC), True),
    ],
    ids=["at_due_instant", "after_due_instant"],
)
def test_exact_deadline_uses_absolute_instant(
    now: datetime,
    expected: bool,
) -> None:
    """Verify that exact deadlines become overdue only after their instant."""

    # Arrange: create a globally comparable exact deadline.
    task = Task(
        title="Submit the report.",
        deadline=TaskDeadline(
            due_at=datetime(2026, 8, 15, 18, 0, tzinfo=UTC),
        ),
    )
    today = date(2026, 8, 15)

    # Act and Assert: equality is still on time; only later is overdue.
    assert task.is_overdue(today=today, now=now) is expected


def test_completed_task_is_not_overdue() -> None:
    """Ensure that completed work cannot remain operationally overdue."""

    # Arrange: complete a task before evaluating it after its deadline.
    task = Task(
        title="Submit the report.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )
    task.complete(
        completed_at=datetime(2026, 8, 14, 18, 0, tzinfo=UTC),
    )

    # Act and Assert: terminal success removes the task from overdue work.
    assert task.is_overdue(
        today=date(2026, 8, 16),
        now=datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
    ) is False


def test_cancelled_task_is_not_overdue() -> None:
    """Ensure that abandoned work cannot remain operationally overdue."""

    # Arrange: cancel a task before evaluating it after its deadline.
    task = Task(
        title="Submit the report.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )
    task.cancel()

    # Act and Assert: terminal cancellation removes it from overdue work.
    assert task.is_overdue(
        today=date(2026, 8, 16),
        now=datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
    ) is False
