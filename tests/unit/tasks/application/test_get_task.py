"""Unit tests for the task retrieval application use case."""

# UUID records exactly which identity the use case requested.
from uuid import UUID, uuid4

# Pytest verifies explicit application errors and runtime validation.
import pytest

# Import the use case that coordinates task retrieval.
from personal_productivity.tasks.application.get_task import (
    GetTask,
    TaskNotFoundError,
)

# Tests use real domain entities as repository results.
from personal_productivity.tasks.domain.task import Task


class ReturningTaskRepository:
    """Return one configured task while recording repository interactions."""

    def __init__(self, task: Task) -> None:
        """Configure the entity available to the retrieval use case."""

        # The repository returns this entity when its identity is requested.
        self.task = task

        # Recorded identifiers make the application interaction observable.
        self.requested_ids: list[UUID] = []

    def add(self, task: Task) -> None:
        """Reject writes because this test repository is read-only."""

        # Retrieval must never perform an unexpected persistence write.
        raise AssertionError("GetTask must not add tasks.")

    def get_by_id(self, task_id: UUID) -> Task | None:
        """Return the configured entity when its identifier matches."""

        # Record the query before returning its deterministic result.
        self.requested_ids.append(task_id)

        # A mismatched identity behaves like an absent database record.
        if task_id != self.task.id:
            return None

        return self.task


def test_get_task_returns_entity_requested_by_identifier() -> None:
    """Verify that retrieval returns the repository's domain entity."""

    # Arrange: configure one existing task and inject its repository.
    existing_task = Task(title="Study Docker.")
    repository = ReturningTaskRepository(task=existing_task)
    use_case = GetTask(repository=repository)

    # Act: retrieve the task through the application boundary.
    retrieved_task = use_case.execute(task_id=existing_task.id)

    # Assert: the same authoritative domain entity is returned.
    assert retrieved_task is existing_task

    # Assert: the repository received exactly one query for the requested ID.
    assert repository.requested_ids == [existing_task.id]


def test_get_task_reports_missing_identifier() -> None:
    """Verify that a valid but unknown identity has an explicit outcome."""

    # Arrange: configure a repository containing a different task.
    existing_task = Task(title="Study Docker.")
    repository = ReturningTaskRepository(task=existing_task)
    use_case = GetTask(repository=repository)
    missing_task_id = uuid4()

    # Act and Assert: repository absence becomes an application error.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{missing_task_id}' was not found",
    ):
        use_case.execute(task_id=missing_task_id)

    # Assert: the repository received the valid missing identifier once.
    assert repository.requested_ids == [missing_task_id]


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
def test_get_task_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never reach persistence."""

    # Arrange: configure a repository whose interactions are observable.
    existing_task = Task(title="Study Docker.")
    repository = ReturningTaskRepository(task=existing_task)
    use_case = GetTask(repository=repository)

    # Act and Assert: external identity values require runtime validation.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        use_case.execute(task_id=invalid_task_id)

    # Assert: invalid input is rejected before any repository query.
    assert repository.requested_ids == []
