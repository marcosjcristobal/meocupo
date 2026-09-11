"""Unit tests for the task-deadline clearing application use case."""

# Temporal values create deterministic deadlines and completion history.
from datetime import UTC, date, datetime

# UUID creates and types portable task identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application and domain failures.
import pytest

# Import the use case that will coordinate deadline removal.
from personal_productivity.tasks.application.clear_task_deadline import (
    ClearTaskDeadline,
)

# Tests exercise the real task entity and its editability errors.
from personal_productivity.tasks.domain.task import (
    Task,
    TaskNotEditableError,
)

# Deadline preserves date-only planning intent.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline

# Status verifies that deadline removal does not alter lifecycle.
from personal_productivity.tasks.domain.task_status import TaskStatus

# Missing identities use one storage-independent application outcome.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskNotFoundError,
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


def test_clear_task_deadline_removes_and_persists_value() -> None:
    """Verify deadline removal coordinates domain and persistence."""

    # Arrange: create a task with one existing deadline.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(
            due_on=date(2026, 9, 15),
        ),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = ClearTaskDeadline(repository=repository)

    # Act: remove the deadline through the application boundary.
    updated_task = use_case.execute(task_id=task.id)

    # Assert: planning changed without altering lifecycle history.
    assert updated_task is task
    assert updated_task.deadline is None
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
def test_clear_task_deadline_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare one task containing an existing deadline.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(
            due_on=date(2026, 9, 15),
        ),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = ClearTaskDeadline(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(task_id=invalid_task_id)

    # Assert: rejection occurs before any repository interaction.
    assert repository.requested_ids == []
    assert repository.saved_tasks == []


def test_clear_task_deadline_reports_missing_identity() -> None:
    """Ensure that an absent task cannot have its deadline removed."""

    # Arrange: configure persistence to report absence.
    task_id = uuid4()
    repository = RecordingTaskRepository(task=None)
    use_case = ClearTaskDeadline(repository=repository)

    # Act and Assert: absence becomes an explicit application outcome.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{task_id}' was not found",
    ):
        use_case.execute(task_id=task_id)

    # Assert: lookup occurred, but no entity was available to save.
    assert repository.requested_ids == [task_id]
    assert repository.saved_tasks == []


def test_clear_task_deadline_does_not_save_terminal_task_changes() -> None:
    """Ensure that completed task planning remains historical."""

    # Arrange: complete a task while retaining its existing deadline.
    deadline = TaskDeadline(
        due_on=date(2026, 9, 15),
    )
    task = Task(
        title="Renew the insurance.",
        deadline=deadline,
    )
    task.complete(
        completed_at=datetime(
            2026,
            9,
            12,
            18,
            30,
            tzinfo=UTC,
        ),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = ClearTaskDeadline(repository=repository)

    # Act and Assert: terminal planning cannot be rewritten.
    with pytest.raises(
        TaskNotEditableError,
        match="Cannot clear deadline for a task in 'completed'",
    ):
        use_case.execute(task_id=task.id)

    # Assert: rejection preserves the deadline and skips persistence.
    assert task.deadline == deadline
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []


