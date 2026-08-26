"""Unit tests for the task-postponing application use case."""

# Date creates deterministic calendar deadlines.
from datetime import date

# UUID creates and types portable task identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application and domain failures.
import pytest

# Missing identities use one storage-independent application outcome.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskNotFoundError,
)

# Import the use case that will coordinate postponement.
from personal_productivity.tasks.application.postpone_task import PostponeTask

# Tests exercise the real task entity and postponement errors.
from personal_productivity.tasks.domain.task import (
    InvalidTaskPostponementError,
    Task,
)

# Deadline preserves date-only planning intent.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline

# Status verifies that planning does not alter lifecycle.
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


def test_postpone_task_updates_deadline_and_persists_entity() -> None:
    """Verify postponement coordinates retrieval, domain, and persistence."""

    # Arrange: create a task with an existing calendar commitment.
    original_deadline = TaskDeadline(
        due_on=date(2026, 8, 26),
    )
    postponed_deadline = TaskDeadline(
        due_on=date(2026, 8, 30),
    )
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )
    repository = RecordingTaskRepository(task=task)
    use_case = PostponeTask(repository=repository)

    # Act: request a later deadline through the application boundary.
    postponed_task = use_case.execute(
        task_id=task.id,
        deadline=postponed_deadline,
    )

    # Assert: planning changed without altering lifecycle.
    assert postponed_task is task
    assert postponed_task.deadline == postponed_deadline
    assert postponed_task.postponement_count == 1
    assert postponed_task.status is TaskStatus.PENDING

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
def test_postpone_task_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare valid current and proposed deadlines.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(
            due_on=date(2026, 8, 26),
        ),
    )
    postponed_deadline = TaskDeadline(
        due_on=date(2026, 8, 30),
    )
    repository = RecordingTaskRepository(task=task)
    use_case = PostponeTask(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(
            task_id=invalid_task_id,
            deadline=postponed_deadline,
        )

    # Assert: rejection occurs before any repository interaction.
    assert repository.requested_ids == []
    assert repository.saved_tasks == []


def test_postpone_task_reports_missing_identity() -> None:
    """Ensure that an absent task cannot be postponed."""

    # Arrange: configure persistence to report absence.
    task_id = uuid4()
    postponed_deadline = TaskDeadline(
        due_on=date(2026, 8, 30),
    )
    repository = RecordingTaskRepository(task=None)
    use_case = PostponeTask(repository=repository)

    # Act and Assert: absence becomes an explicit application outcome.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{task_id}' was not found",
    ):
        use_case.execute(
            task_id=task_id,
            deadline=postponed_deadline,
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
def test_postpone_task_does_not_save_raw_deadline_values(
    invalid_deadline: object,
) -> None:
    """Ensure that postponement cannot bypass its value object."""

    # Arrange: preserve one valid current deadline.
    original_deadline = TaskDeadline(
        due_on=date(2026, 8, 26),
    )
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )
    repository = RecordingTaskRepository(task=task)
    use_case = PostponeTask(repository=repository)

    # Act and Assert: only TaskDeadline may cross the domain boundary.
    with pytest.raises(
        TypeError,
        match="Task deadline must be a TaskDeadline",
    ):
        use_case.execute(
            task_id=task.id,
            deadline=invalid_deadline,
        )

    # Assert: rejection preserves planning history and skips persistence.
    assert task.deadline == original_deadline
    assert task.postponement_count == 0
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []


def test_postpone_task_does_not_save_non_later_deadline() -> None:
    """Ensure that rejected postponement leaves persistence untouched."""

    # Arrange: propose the same date as the current commitment.
    original_deadline = TaskDeadline(
        due_on=date(2026, 8, 26),
    )
    task = Task(
        title="Renew the insurance.",
        deadline=original_deadline,
    )
    repository = RecordingTaskRepository(task=task)
    use_case = PostponeTask(repository=repository)

    # Act and Assert: equal dates do not represent postponement.
    with pytest.raises(
        InvalidTaskPostponementError,
        match="Postponed deadline must be later than the current deadline",
    ):
        use_case.execute(
            task_id=task.id,
            deadline=TaskDeadline(
                due_on=date(2026, 8, 26),
            ),
        )

    # Assert: rejection preserves planning history and skips persistence.
    assert task.deadline == original_deadline
    assert task.postponement_count == 0
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []
