"""Application use case for resuming one task."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# UUID represents the portable identity supplied by an external channel.
from uuid import UUID

# The use case depends on repository contracts and shared outcomes.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskNotFoundError,
    TaskRepository,
)

# Task contains the authoritative lifecycle transition.
from personal_productivity.tasks.domain.task import Task


@dataclass(slots=True, kw_only=True)
class ResumeTask:
    """Resume one paused task and persist its newer state."""

    # Dependency injection keeps storage outside application logic.
    repository: TaskRepository

    def execute(
        self,
        *,
        task_id: UUID,
    ) -> Task:
        """Move one paused task back into active work."""

        # Runtime validation rejects malformed external identifiers early.
        if not isinstance(task_id, UUID):
            raise TypeError("Task identifier must be a UUID.")

        # Retrieve the authoritative entity through the repository port.
        task = self.repository.get_by_id(task_id)

        # Absence becomes one explicit storage-independent outcome.
        if task is None:
            raise TaskNotFoundError(
                f"Task '{task_id}' was not found."
            )

        # Delegate lifecycle rules to the domain entity itself.
        task.resume()

        # Persist only after the domain transition succeeds.
        self.repository.save(task)

        # Return the updated entity to the calling interface.
        return task
