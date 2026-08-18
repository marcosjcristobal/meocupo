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

# Repository outcomes remain independent from concrete storage.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskAlreadyExistsError,
    TaskNotFoundError,
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


def test_list_all_returns_immutable_task_snapshot() -> None:
    """Verify that collection retrieval does not expose mutable storage."""

    # Arrange: store two independent domain entities.
    repository = InMemoryTaskRepository()
    first_task = Task(title="Study Docker.")
    second_task = Task(title="Buy soil for the pitaya.")
    repository.add(first_task)
    repository.add(second_task)

    # Act: request a snapshot of every stored task.
    task_snapshot = repository.list_all()

    # Assert: the adapter returns an immutable collection.
    assert isinstance(task_snapshot, tuple)

    # Assert: every stored entity appears exactly once.
    assert len(task_snapshot) == 2
    assert first_task in task_snapshot
    assert second_task in task_snapshot


def test_save_replaces_existing_task_entity() -> None:
    """Verify that saving replaces the entity stored under one identity."""

    # Arrange: persist an initial entity under its generated identity.
    repository = InMemoryTaskRepository()
    existing_task = Task(title="Study Docker.")
    repository.add(existing_task)

    # Create a different entity representing newer state for that identity.
    replacement_task = Task(
        title="Study advanced Docker networking.",
        id=existing_task.id,
    )
    replacement_task.start()

    # Act: persist the newer authoritative state.
    repository.save(replacement_task)

    # Assert: retrieval exposes the replacement entity and its lifecycle.
    retrieved_task = repository.get_by_id(existing_task.id)
    assert retrieved_task is replacement_task
    assert retrieved_task.title == "Study advanced Docker networking."
    assert retrieved_task.status is replacement_task.status


def test_save_rejects_unknown_task_identity() -> None:
    """Ensure that save semantics cannot create a missing task."""

    # Arrange: create an entity whose identity is absent from storage.
    repository = InMemoryTaskRepository()
    missing_task = Task(title="Study Docker.")

    # Act and Assert: creation must use add instead of save.
    with pytest.raises(
        TaskNotFoundError,
        match=f"Task '{missing_task.id}' was not found",
    ):
        repository.save(missing_task)

    # Assert: rejection leaves storage unchanged.
    assert repository.get_by_id(missing_task.id) is None


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
def test_save_rejects_non_task_values(
    invalid_task: object,
) -> None:
    """Ensure that arbitrary values cannot enter task updates."""

    # Arrange: create empty in-memory storage.
    repository = InMemoryTaskRepository()

    # Act and Assert: save accepts complete Task entities only.
    with pytest.raises(
        TypeError,
        match="Stored value must be a Task",
    ):
        repository.save(invalid_task)
