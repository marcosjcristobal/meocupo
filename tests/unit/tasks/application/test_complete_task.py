"""Unit tests for the task-completing application use case."""

# Datetime provides one deterministic completion instant.
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
from personal_productivity.tasks.application.complete_task import CompleteTask

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


def test_complete_task_transitions_and_persists_entity() -> None:
    """Verify completion coordinates retrieval, domain, and persistence."""

    # Arrange: use one explicit instant independent from the real clock.
    task = Task(title="Prepare the investor presentation.")
    completed_at = datetime(
        2026,
        8,
        26,
        18,
        30,
        tzinfo=UTC,
    )
    repository = RecordingTaskRepository(task=task)
    use_case = CompleteTask(repository=repository)

    # Act: request completion by portable identity and exact instant.
    completed_task = use_case.execute(
        task_id=task.id,
        completed_at=completed_at,
    )

    # Assert: lifecycle and historical metadata changed together.
    assert completed_task is task
    assert completed_task.status is TaskStatus.COMPLETED
    assert completed_task.completed_at == completed_at

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
def test_complete_task_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: prepare a valid task and completion instant.
    task = Task(title="Prepare the investor presentation.")
    completed_at = datetime(
        2026,
        8,
        26,
        18,
        30,
        tzinfo=UTC,
    )
    repository = RecordingTaskRepository(task=task)
    use_case = CompleteTask(repository=repository)

    # Act and Assert: external identities must use UUID.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(
            task_id=invalid_task_id,
            completed_at=completed_at,
        )

    # Assert: rejection occurs before any repository interaction.
    assert repository.requested_ids == []
    assert repository.saved_tasks == []


def test_complete_task_reports_missing_identity() -> None:
    """Ensure that an absent task cannot be completed."""

    # Arrange: configure persistence to report absence.
    task_id = uuid4()
    completed_at = datetime(
        2026,
        8,
        26,
        18,
        30,
        tzinfo=UTC,
    )
    repository = RecordingTaskRepository(task=None)
    use_case = CompleteTask(repository=repository)

    # Act and Assert: absence becomes an explicit application outcome.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{task_id}' was not found",
    ):
        use_case.execute(
            task_id=task_id,
            completed_at=completed_at,
        )

    # Assert: lookup occurred, but no entity was available to save.
    assert repository.requested_ids == [task_id]
    assert repository.saved_tasks == []


def test_complete_task_does_not_save_rejected_transition() -> None:
    """Ensure that repeated completion leaves persistence untouched."""

    # Arrange: complete the task once with its authoritative history.
    task = Task(title="Prepare the investor presentation.")
    original_completed_at = datetime(
        2026,
        8,
        26,
        18,
        30,
        tzinfo=UTC,
    )
    task.complete(completed_at=original_completed_at)
    repository = RecordingTaskRepository(task=task)
    use_case = CompleteTask(repository=repository)

    # Act and Assert: a terminal task cannot be completed again.
    with pytest.raises(
        InvalidTaskTransitionError,
        match="Cannot complete a task from 'completed'",
    ):
        use_case.execute(
            task_id=task.id,
            completed_at=datetime(
                2026,
                8,
                26,
                19,
                0,
                tzinfo=UTC,
            ),
        )

    # Assert: rejection preserves the original historical instant.
    assert task.completed_at == original_completed_at
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []


def test_complete_task_does_not_save_invalid_completion_time() -> None:
    """Ensure that invalid temporal metadata is never persisted."""

    # Arrange: a naive datetime does not identify an absolute instant.
    task = Task(title="Prepare the investor presentation.")
    repository = RecordingTaskRepository(task=task)
    use_case = CompleteTask(repository=repository)

    # Act and Assert: domain timestamp validation remains authoritative.
    with pytest.raises(
        ValueError,
        match="Completion time must include a timezone",
    ):
        use_case.execute(
            task_id=task.id,
            completed_at=datetime(2026, 8, 26, 18, 30),
        )

    # Assert: invalid history changed neither lifecycle nor persistence.
    assert task.status is TaskStatus.PENDING
    assert task.completed_at is None
    assert repository.requested_ids == [task.id]
    assert repository.saved_tasks == []
