"""Shared application helper for required task retrieval."""

# UUID represents the portable identity supplied by an external channel.
from uuid import UUID

# Repository contracts keep lookup independent from concrete storage.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskNotFoundError,
    TaskRepository,
)

# Successful lookup returns one complete domain entity.
from personal_productivity.tasks.domain.task import Task


def get_existing_task(
    *,
    repository: TaskRepository,
    task_id: UUID,
) -> Task:
    """Return one existing task or expose an explicit application outcome."""

    # Runtime validation rejects malformed external identifiers early.
    if not isinstance(task_id, UUID):
        raise TypeError("Task identifier must be a UUID.")

    # Retrieve the authoritative entity through the repository port.
    task = repository.get_by_id(task_id)

    # Absence remains independent from the selected storage adapter.
    if task is None:
        raise TaskNotFoundError(
            f"Task '{task_id}' was not found."
        )

    # Callers receive the authoritative entity ready for coordination.
    return task
