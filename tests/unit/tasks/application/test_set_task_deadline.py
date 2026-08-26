"""Unit tests for the task-deadline application use case."""

# Temporal values create deterministic deadlines and completion history.
from datetime import UTC, date, datetime

# UUID creates and types portable task identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application and domain failures.
import pytest

# Tests exercise the real task entity and its editability errors.
from personal_productivity.tasks.domain.task import (
    Task,
    TaskNotEditableError,
)

# Deadline preserves date-only planning intent.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline

# Status verifies that deadline assignment does not alter lifecycle.
from personal_productivity.tasks.domain.task_status import TaskStatus

# Missing identities use one storage-independent application outcome.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskNotFoundError,
)

# Import the use case that will coordinate deadline assignment.
from personal_productivity.tasks.application.set_task_deadline import (
    SetTaskDeadline,
)


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


def test_set_task_deadline_assigns_and_persists_value() -> None:
    """Verify deadline assignment coordinates domain and persistence."""

    # Arrange: create an undated task and one calendar commitment.
    task = Task(title="Renew the insurance.")
    deadline = TaskDeadline(
        due_on=date(2026, 8, 30),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = SetTaskDeadline(repository=repository)

    # Act: assign the deadline through the application boundary.
    updated_task = use_case.execute(
        task_id=task.id,
        deadline=deadline,
    )

    # Assert: planning changed without becoming postponement.
    assert updated_task is task
    assert updated_task.deadline == deadline
    assert updated_task.postponement_count == 0
    assert updated_task.status is TaskStatus.PENDING

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
def test_set_task_deadline_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare one valid deadline.
    task = Task(title="Renew the insurance.")
    deadline = TaskDeadline(
        due_on=date(2026, 8, 30),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = SetTaskDeadline(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(
            task_id=invalid_task_id,
            deadline=deadline,
        )

    # Assert: rejection occurs before any repository interaction.
    assert repository.requested_ids == []
    assert repository.saved_tasks == []


def test_set_task_deadline_reports_missing_identity() -> None:
    """Ensure that an absent task cannot receive a deadline."""

    # Arrange: configure persistence to report absence.
    task_id = uuid4()
    deadline = TaskDeadline(
        due_on=date(2026, 8, 30),
    )
    repository = RecordingTaskRepository(task=None)
    use_case = SetTaskDeadline(repository=repository)

    # Act and Assert: absence becomes an explicit application outcome.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{task_id}' was not found",
    ):
        use_case.execute(
            task_id=task_id,
            deadline=deadline,
        )

    # Assert: lookup occurred, but no entity was available to save.
    assert repository.requested_ids == [task_id]
    assert repository.saved_tasks == []


@pytest.mark.parametrize(
    "invalid_deadline",
    [
        date(2026, 8, 30),
        "2026-08-30",
        None,
    ],
    ids=[
        "raw_date",
        "text",
        "none",
    ],
)
def test_set_task_deadline_does_not_save_raw_values(
    invalid_deadline: object,
) -> None:
    """Ensure that deadline assignment cannot bypass its value object."""

    # Arrange: preserve one task without a deadline.
    task = Task(title="Renew the insurance.")
    repository = RecordingTaskRepository(task=task)
    use_case = SetTaskDeadline(repository=repository)

    # Act and Assert: only TaskDeadline may cross the domain boundary.
    with pytest.raises(
        TypeError,
        match="Task deadline must be a TaskDeadline",
    ):
        use_case.execute(
            task_id=task.id,
            deadline=invalid_deadline,
        )

    # Assert: rejection preserves planning and skips persistence.
    assert task.deadline is None
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []


def test_set_task_deadline_does_not_save_terminal_task_changes() -> None:
    """Ensure that completed task planning remains historical."""

    # Arrange: complete a task before proposing a deadline.
    task = Task(title="Renew the insurance.")
    task.complete(
        completed_at=datetime(
            2026,
            8,
            27,
            18,
            30,
            tzinfo=UTC,
        ),
    )
    deadline = TaskDeadline(
        due_on=date(2026, 8, 30),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = SetTaskDeadline(repository=repository)

    # Act and Assert: terminal planning cannot be rewritten.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot change deadline for a task in 'completed'",
    ):
        use_case.execute(
            task_id=task.id,
            deadline=deadline,
        )

    # Assert: rejection preserves planning and skips persistence.
    assert task.deadline is None
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []
