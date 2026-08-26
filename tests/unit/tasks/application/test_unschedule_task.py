"""Unit tests for the task-unscheduling application use case."""

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

# Import the use case that coordinates unscheduling.
from personal_productivity.tasks.application.unschedule_task import (
    UnscheduleTask,
)

# Tests exercise the real task entity and its editability errors.
from personal_productivity.tasks.domain.task import (
    Task,
    TaskNotEditableError,
)

# Status verifies that unscheduling does not alter lifecycle.
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


def test_unschedule_task_clears_time_block_and_persists_entity() -> None:
    """Verify unscheduling coordinates retrieval, domain, and persistence."""

    # Arrange: create a task with one existing calendar allocation.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
    )
    task = Task(
        title="Study Docker.",
        time_block=time_block,
    )
    repository = RecordingTaskRepository(task=task)
    use_case = UnscheduleTask(repository=repository)

    # Act: remove calendar allocation through the application boundary.
    unscheduled_task = use_case.execute(task_id=task.id)

    # Assert: planning was cleared without altering lifecycle.
    assert unscheduled_task is task
    assert unscheduled_task.time_block is None
    assert unscheduled_task.status is TaskStatus.PENDING

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
def test_unschedule_task_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare a task with one calendar allocation.
    task = Task(
        title="Study Docker.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
        ),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = UnscheduleTask(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(task_id=invalid_task_id)

    # Assert: rejection occurs before any repository interaction.
    assert repository.requested_ids == []
    assert repository.saved_tasks == []


def test_unschedule_task_reports_missing_identity() -> None:
    """Ensure that an absent task cannot be unscheduled."""

    # Arrange: configure persistence to report absence.
    task_id = uuid4()
    repository = RecordingTaskRepository(task=None)
    use_case = UnscheduleTask(repository=repository)

    # Act and Assert: absence becomes an explicit application outcome.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{task_id}' was not found",
    ):
        use_case.execute(task_id=task_id)

    # Assert: lookup occurred, but no entity was available to save.
    assert repository.requested_ids == [task_id]
    assert repository.saved_tasks == []


def test_unschedule_task_does_not_save_terminal_task_changes() -> None:
    """Ensure that completed task planning remains historical."""

    # Arrange: complete a task that retains its former allocation.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
    )
    task = Task(
        title="Study Docker.",
        time_block=time_block,
    )
    task.complete(
        completed_at=datetime(
            2026,
            8,
            27,
            19,
            30,
            tzinfo=UTC,
        ),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = UnscheduleTask(repository=repository)

    # Act and Assert: terminal planning cannot be rewritten.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot change calendar allocation for a task in 'completed'",
    ):
        use_case.execute(task_id=task.id)

    # Assert: rejection preserves the historical allocation.
    assert task.time_block == time_block
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []
