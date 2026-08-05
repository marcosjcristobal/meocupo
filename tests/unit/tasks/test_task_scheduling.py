"""Unit tests for assigning calendar work blocks to tasks."""

# Datetime provides deterministic planned work boundaries.
from datetime import UTC, datetime

# Pytest executes the same domain boundary against several invalid values.
import pytest

# Import the entity and time block through their domain package paths.
from personal_productivity.tasks.domain.task import (
    Task,
    TaskNotEditableError,
)

from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)


def test_task_time_block_is_optional() -> None:
    """Verify that a task may exist without reserved calendar time."""

    # Act: create the smallest valid unscheduled task.
    task = Task(title="Study Docker.")

    # Assert: absence has one explicit representation.
    assert task.time_block is None


def test_task_accepts_a_valid_time_block() -> None:
    """Verify that a task may reserve a concrete calendar interval."""

    # Arrange: create one validated interval for planned work.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
    )

    # Act: create a task planned inside that interval.
    task = Task(
        title="Study Docker.",
        time_block=time_block,
    )

    # Assert: planning is preserved independently from completion deadline.
    assert task.time_block == time_block
    assert task.deadline is None


@pytest.mark.parametrize(
    "invalid_time_block",
    [
        datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        (
            datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
            datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
        ),
        "2026-08-05 18:00/19:30",
    ],
    ids=[
        "raw_datetime",
        "tuple",
        "text",
    ],
)
def test_task_rejects_raw_time_block_values(
    invalid_time_block: object,
) -> None:
    """Ensure that task planning cannot bypass the time block value object."""

    # Act and Assert: only CalendarTimeBlock may represent reserved calendar work.
    with pytest.raises(
        TypeError,
        match="Task time block must be a CalendarTimeBlock",
    ):
        Task(
            title="Study Docker.",
            time_block=invalid_time_block,
        )


def test_unplanned_task_can_be_scheduled() -> None:
    """Verify that an unfinished task may enter the calendar."""

    # Arrange: create an unscheduled task and a validated work interval.
    task = Task(title="Study Docker.")
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
    )

    # Act: reserve calendar time through an explicit domain operation.
    task.schedule(time_block=time_block)

    # Assert: the task now owns that calendar allocation.
    assert task.time_block == time_block


def test_scheduled_task_can_be_unscheduled() -> None:
    """Verify that calendar removal does not delete the task."""

    # Arrange: create a task with an existing calendar allocation.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
    )
    task = Task(
        title="Study Docker.",
        time_block=time_block,
    )

    # Act: remove only the calendar allocation.
    task.unschedule()

    # Assert: the task remains valid but no longer occupies calendar time.
    assert task.time_block is None
    assert task.title == "Study Docker."


def test_schedule_rejects_raw_time_block_values() -> None:
    """Ensure that schedule changes cannot bypass the value object."""

    # Arrange: create a task whose current allocation must be preserved.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
    )
    task = Task(
        title="Study Docker.",
        time_block=original_time_block,
    )
    raw_time_block = (
        datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act and Assert: raw interval data cannot cross the domain boundary.
    with pytest.raises(
        TypeError,
        match="Task time block must be a CalendarTimeBlock",
    ):
        task.schedule(time_block=raw_time_block)

    # Assert: failed replanning preserves the original calendar allocation.
    assert task.time_block == original_time_block


def test_completed_task_cannot_be_scheduled() -> None:
    """Ensure that completed work cannot receive new calendar planning."""

    # Arrange: complete an unscheduled task and prepare a proposed allocation.
    task = Task(title="Study Docker.")
    task.complete(
        completed_at=datetime(2026, 8, 5, 17, 0, tzinfo=UTC),
    )
    proposed_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 19, 30, tzinfo=UTC),
    )

    # Act and Assert: completed planning must remain historical.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot change calendar allocation for a task in 'completed'",
    ):
        task.schedule(time_block=proposed_time_block)

    # Assert: rejection cannot add calendar time.
    assert task.time_block is None


def test_cancelled_task_cannot_be_unscheduled() -> None:
    """Ensure that cancelled work preserves its previous calendar planning."""

    # Arrange: cancel a task that already owns a calendar allocation.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
    )
    task = Task(
        title="Study Docker.",
        time_block=original_time_block,
    )
    task.cancel()

    # Act and Assert: cancellation freezes the previous planning context.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot change calendar allocation for a task in 'cancelled'",
    ):
        task.unschedule()

    # Assert: rejection preserves the historical calendar allocation.
    assert task.time_block == original_time_block


def test_scheduled_task_can_replace_its_time_block() -> None:
    """Verify that replanning atomically replaces the previous interval."""

    # Arrange: create the original and replacement calendar allocations.
    original_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
    )
    replacement_time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 6, 19, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 6, 20, 30, tzinfo=UTC),
    )
    task = Task(
        title="Study Docker.",
        time_block=original_time_block,
    )
    original_status = task.status

    # Act: replace the immutable block through the scheduling operation.
    task.schedule(time_block=replacement_time_block)

    # Assert: only the calendar allocation changes.
    assert task.time_block == replacement_time_block
    assert task.status is original_status