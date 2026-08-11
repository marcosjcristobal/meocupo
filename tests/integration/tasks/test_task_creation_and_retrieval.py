"""Integration tests for task use cases and repository adapters."""

# Application use cases coordinate behavior without knowing storage details.
from personal_productivity.tasks.application.create_task import CreateTask
from personal_productivity.tasks.application.get_task import GetTask
from personal_productivity.tasks.application.list_tasks import ListTasks

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


def test_created_tasks_appear_in_application_listing() -> None:
    """Verify that creation and listing share one persistence boundary."""

    # Arrange: inject one repository into both application operations.
    repository = InMemoryTaskRepository()
    create_task = CreateTask(repository=repository)
    list_tasks = ListTasks(repository=repository)

    # Act: create two entities before requesting the collection snapshot.
    first_task = create_task.execute(
        title="Study Docker.",
    )
    second_task = create_task.execute(
        title="Buy soil for the pitaya.",
    )
    listed_tasks = list_tasks.execute()

    # Assert: listing exposes an immutable repository snapshot.
    assert isinstance(listed_tasks, tuple)

    # Assert: every created entity is present exactly once.
    assert len(listed_tasks) == 2
    assert first_task in listed_tasks
    assert second_task in listed_tasks
