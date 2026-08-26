"""Unit tests for the task-scheduling application use case."""

# Datetime creates deterministic calendar allocations.
from datetime import UTC, datetime

# UUID creates and types portable task identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application and domain failures.
import pytest

# CalendarTimeBlock represents exact reserved work.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Missing identities use one storage-independent application outcome.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskNotFoundError,
)

# Import the use case that coordinates scheduling.
from personal_productivity.tasks.application.schedule_task import ScheduleTask

# Tests exercise the real task entity and its editability errors.
from personal_productivity.tasks.domain.task import (
    Task,
    TaskNotEditableError,
)

# Status verifies that scheduling does not alter lifecycle.
from personal_productivity.tasks.domain.task_status import TaskStatus


class RecordingTaskRepository:
    """Provide one task while recording retrieval and persistence."""

    def __init__(
        self,
        *,
        task: Task | None,
    ) -> None:
        """Configure the entity returned by identity lookup."""

        # None represents an identity absent from persistence.
        self.task = task

        # Recorded interactions make orchestration observable.
        self.requested_ids: list[UUID] = []
        self.saved_tasks: list[Task] = []

    def get_by_id(
        self,
        task_id: UUID,
    ) -> Task | None:
        """Return the configured task and record its requested identity."""

        # Preserve the interaction for later assertions.
        self.requested_ids.append(task_id)
        return self.task

    def save(
        self,
        task: Task,
    ) -> None:
        """Record the entity selected for persistence."""

        # The fake avoids choosing a concrete storage technology.
        self.saved_tasks.append(task)


def test_schedule_task_assigns_time_block_and_persists_entity() -> None:
    """Verify scheduling coordinates retrieval, domain, and persistence."""

    # Arrange: create an unplanned task and one exact allocation.
    task = Task(title="Study Docker.")
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = ScheduleTask(repository=repository)

    # Act: reserve calendar time through the application boundary.
    scheduled_task = use_case.execute(
        task_id=task.id,
        time_block=time_block,
    )

    # Assert: planning changed without altering lifecycle.
    assert scheduled_task is task
    assert scheduled_task.time_block == time_block
    assert scheduled_task.status is TaskStatus.PENDING

    # Assert: the use case retrieved and persisted the same identity.
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == [task]


@pytest.mark.parametrize(
    "invalid_task_id",
    [
        None,
        42,
        "not-a-uuid",
    ],
    ids=[
        "none",
        "integer",
        "text",
    ],
)
def test_schedule_task_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare one valid exact allocation.
    task = Task(title="Study Docker.")
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = ScheduleTask(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(
            task_id=invalid_task_id,
            time_block=time_block,
        )

    # Assert: rejection occurs before any repository interaction.
    assert repository.requested_ids == []
    assert repository.saved_tasks == []


def test_schedule_task_reports_missing_identity() -> None:
    """Ensure that an absent task cannot be scheduled."""

    # Arrange: configure persistence to report absence.
    task_id = uuid4()
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
    )
    repository = RecordingTaskRepository(task=None)
    use_case = ScheduleTask(repository=repository)

    # Act and Assert: absence becomes an explicit application outcome.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{task_id}' was not found",
    ):
        use_case.execute(
            task_id=task_id,
            time_block=time_block,
        )

    # Assert: lookup occurred, but no entity was available to save.
    assert repository.requested_ids == [task_id]
    assert repository.saved_tasks == []


@pytest.mark.parametrize(
    "invalid_time_block",
    [
        None,
        datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        (
            datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
            datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
        ),
    ],
    ids=[
        "none",
        "raw_datetime",
        "tuple",
    ],
)
def test_schedule_task_does_not_save_raw_time_block_values(
    invalid_time_block: object,
) -> None:
    """Ensure that scheduling cannot bypass its value object."""

    # Arrange: preserve one task without calendar allocation.
    task = Task(title="Study Docker.")
    repository = RecordingTaskRepository(task=task)
    use_case = ScheduleTask(repository=repository)

    # Act and Assert: only CalendarTimeBlock may cross the domain boundary.
    with pytest.raises(
        TypeError,
        match="Task time block must be a CalendarTimeBlock",
    ):
        use_case.execute(
            task_id=task.id,
            time_block=invalid_time_block,
        )

    # Assert: rejection preserves planning and skips persistence.
    assert task.time_block is None
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []


def test_schedule_task_does_not_save_terminal_task_changes() -> None:
    """Ensure that completed task planning remains historical."""

    # Arrange: complete a task before proposing calendar allocation.
    task = Task(title="Study Docker.")
    task.complete(
        completed_at=datetime(
            2026,
            8,
            26,
            18,
            30,
            tzinfo=UTC,
        ),
    )
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = ScheduleTask(repository=repository)

    # Act and Assert: terminal planning cannot be rewritten.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot change calendar allocation for a task in 'completed'",
    ):
        use_case.execute(
            task_id=task.id,
            time_block=time_block,
        )

    # Assert: rejection preserves planning and skips persistence.
    assert task.time_block is None
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []