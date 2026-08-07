"""Unit tests for the in-memory task repository adapter."""

# UUID creates a valid identity that is absent from the repository.
from uuid import uuid4

# Pytest verifies runtime protection at the infrastructure boundary.
import pytest

# Import the adapter that will implement the application repository port.
from personal_productivity.tasks.infrastructure.repositories.in_memory_task_repository import (
    InMemoryTaskRepository,
)

# Repository tests store and retrieve real domain entities.
from personal_productivity.tasks.domain.task import Task

# Duplicate identities use one storage-independent application error.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskAlreadyExistsError,
)


def test_added_task_can_be_retrieved_by_identity() -> None:
    """Verify that an added task remains available under its UUID."""

    # Arrange: create an empty adapter and one valid domain entity.
    repository = InMemoryTaskRepository()
    task = Task(title="Study Docker.")

    # Act: persist and retrieve the task through repository operations.
    repository.add(task)
    retrieved_task = repository.get_by_id(task.id)

    # Assert: memory storage returns the authoritative entity instance.
    assert retrieved_task is task


def test_unknown_task_identity_returns_none() -> None:
    """Verify that an absent UUID has an explicit repository result."""

    # Arrange: create an empty repository and an unknown valid identity.
    repository = InMemoryTaskRepository()
    unknown_task_id = uuid4()

    # Act: request an entity that has never been stored.
    retrieved_task = repository.get_by_id(unknown_task_id)

    # Assert: repository absence follows the application port contract.
    assert retrieved_task is None


@pytest.mark.parametrize(
    "invalid_task",
    [
        None,
        42,
        "not-a-task",
    ],
    ids=[
        "none",
        "integer",
        "text",
    ],
)
def test_add_rejects_non_task_values(
    invalid_task: object,
) -> None:
    """Ensure that arbitrary values cannot enter task storage."""

    # Arrange: create an empty adapter for the invalid write attempt.
    repository = InMemoryTaskRepository()

    # Act and Assert: persistence accepts complete Task entities only.
    with pytest.raises(
        TypeError,
        match="Stored value must be a Task",
    ):
        repository.add(invalid_task)


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
def test_get_by_id_rejects_non_uuid_values(
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities cannot enter storage lookup."""

    # Arrange: create an empty adapter for the invalid query.
    repository = InMemoryTaskRepository()

    # Act and Assert: repository keys must use the domain identity type.
    with pytest.raises(
        TypeError,
        match="Task identifier must be a UUID",
    ):
        repository.get_by_id(invalid_task_id)


def test_add_rejects_duplicate_task_identity() -> None:
    """Ensure that adding a task cannot overwrite an existing entity."""

    # Arrange: create two different entities sharing one identity.
    repository = InMemoryTaskRepository()
    existing_task = Task(title="Study Docker.")
    replacement_task = Task(
        title="Replace the original task.",
        id=existing_task.id,
    )
    repository.add(existing_task)

    # Act and Assert: add semantics reject the duplicate identity.
    with pytest.raises(
        TaskAlreadyExistsError,
        match=f"Task '{existing_task.id}' already exists",
    ):
        repository.add(replacement_task)

    # Assert: rejection preserves the original authoritative entity.
    assert repository.get_by_id(existing_task.id) is existing_task
