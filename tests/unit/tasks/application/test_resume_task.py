"""Unit tests for the task-resuming application use case."""

# UUID creates and types portable task identities.
from uuid import UUID, uuid4

# Pytest verifies explicit application and domain failures.
import pytest

# Missing identities use one storage-independent application outcome.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskNotFoundError,
)

# Import the use case that will coordinate the transition.
from personal_productivity.tasks.application.resume_task import ResumeTask

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


def test_resume_task_transitions_and_persists_entity() -> None:
    """Verify that resuming coordinates retrieval, domain, and persistence."""

    # Arrange: only paused work may transition back into active work.
    task = Task(title="Study Docker.")
    task.start()
    task.pause()
    repository = RecordingTaskRepository(task=task)
    use_case = ResumeTask(repository=repository)

    # Act: request the lifecycle transition by portable identity.
    resumed_task = use_case.execute(task_id=task.id)

    # Assert: the domain entity performed the transition.
    assert resumed_task is task
    assert resumed_task.status is TaskStatus.IN_PROGRESS

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
def test_resume_task_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare an observable repository.
    task = Task(title="Study Docker.")
    task.start()
    task.pause()
    repository = RecordingTaskRepository(task=task)
    use_case = ResumeTask(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(task_id=invalid_task_id)

    # Assert: rejection occurs before any repository interaction.
    assert repository.requested_ids == []
    assert repository.saved_tasks == []


def test_resume_task_reports_missing_identity() -> None:
    """Ensure that an absent task cannot resume work."""

    # Arrange: configure persistence to report absence.
    task_id = uuid4()
    repository = RecordingTaskRepository(task=None)
    use_case = ResumeTask(repository=repository)

    # Act and Assert: absence becomes an explicit application outcome.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{task_id}' was not found",
    ):
        use_case.execute(task_id=task_id)

    # Assert: lookup occurred, but no entity was available to save.
    assert repository.requested_ids == [task_id]
    assert repository.saved_tasks == []


def test_resume_task_does_not_save_rejected_transition() -> None:
    """Ensure that domain rejection leaves persistence untouched."""

    # Arrange: pending work cannot be resumed.
    task = Task(title="Study Docker.")
    repository = RecordingTaskRepository(task=task)
    use_case = ResumeTask(repository=repository)

    # Act and Assert: the domain preserves its lifecycle invariant.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot resume a task from 'pending'",
    ):
        use_case.execute(task_id=task.id)

    # Assert: retrieval occurred, but failed state was never saved.
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []
