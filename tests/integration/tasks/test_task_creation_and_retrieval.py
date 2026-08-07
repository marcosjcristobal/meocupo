"""Integration tests for task use cases and repository adapters."""

# Application use cases coordinate behavior without knowing storage details.
from personal_productivity.tasks.application.create_task import CreateTask
from personal_productivity.tasks.application.get_task import GetTask

# The in-memory adapter provides one shared persistence implementation.
from personal_productivity.tasks.infrastructure.repositories.in_memory_task_repository import (
    InMemoryTaskRepository,
)


def test_created_task_can_be_retrieved_through_shared_repository() -> None:
    """Verify collaboration across application and infrastructure layers."""

    # Arrange: inject one adapter instance into both application use cases.
    repository = InMemoryTaskRepository()
    create_task = CreateTask(repository=repository)
    get_task = GetTask(repository=repository)

    # Act: create an entity and retrieve it through a separate use case.
    created_task = create_task.execute(
        title="Study Docker.",
        description="Complete the networking chapter.",
    )
    retrieved_task = get_task.execute(
        task_id=created_task.id,
    )

    # Assert: both operations share one authoritative persisted entity.
    assert retrieved_task is created_task
    assert retrieved_task.description == "Complete the networking chapter."
