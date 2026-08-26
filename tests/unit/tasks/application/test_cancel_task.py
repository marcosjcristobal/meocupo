"""Unit tests for the task-cancelling application use case."""

# Datetime creates valid completion history for a terminal task.
from datetime import UTC, datetime

# UUID creates and types portable task identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application and domain failures.
import pytest

# Missing identities use one storage-independent application outcome.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskNotFoundError,
)

# Import the use case that will coordinate the transition.
from personal_productivity.tasks.application.cancel_task import CancelTask

# Tests exercise the real task entity and its lifecycle errors.
from personal_productivity.tasks.domain.task import (
    InvalidTaskTransitionError,
    Task,
)

# Status verifies the resulting lifecycle explicitly.
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


def test_cancel_task_transitions_and_persists_entity() -> None:
    """Verify cancellation coordinates retrieval, domain, and persistence."""

    # Arrange: create one unfinished task available for cancellation.
    task = Task(title="Buy soil for the pitaya.")
    repository = RecordingTaskRepository(task=task)
    use_case = CancelTask(repository=repository)

    # Act: request cancellation by portable identity.
    cancelled_task = use_case.execute(task_id=task.id)

    # Assert: the domain entity performed the transition.
    assert cancelled_task is task
    assert cancelled_task.status is TaskStatus.CANCELLED
    assert cancelled_task.completed_at is None

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
def test_cancel_task_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare an observable repository.
    repository = RecordingTaskRepository(
        task=Task(title="Buy soil for the pitaya."),
    )
    use_case = CancelTask(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(task_id=invalid_task_id)

    # Assert: rejection occurs before any repository interaction.
    assert repository.requested_ids == []
    assert repository.saved_tasks == []


def test_cancel_task_reports_missing_identity() -> None:
    """Ensure that an absent task cannot be cancelled."""

    # Arrange: configure persistence to report absence.
    task_id = uuid4()
    repository = RecordingTaskRepository(task=None)
    use_case = CancelTask(repository=repository)

    # Act and Assert: absence becomes an explicit application outcome.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{task_id}' was not found",
    ):
        use_case.execute(task_id=task_id)

    # Assert: lookup occurred, but no entity was available to save.
    assert repository.requested_ids == [task_id]
    assert repository.saved_tasks == []


def test_cancel_task_does_not_save_rejected_transition() -> None:
    """Ensure that terminal task history remains untouched."""

    # Arrange: completed work cannot be cancelled afterward.
    task = Task(title="Prepare the investor presentation.")
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
    repository = RecordingTaskRepository(task=task)
    use_case = CancelTask(repository=repository)

    # Act and Assert: the domain preserves its terminal lifecycle.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot cancel a task from 'completed'",
    ):
        use_case.execute(task_id=task.id)

    # Assert: rejection preserves completion history and skips persistence.
    assert task.status is TaskStatus.COMPLETED
    assert task.completed_at is not None
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []
