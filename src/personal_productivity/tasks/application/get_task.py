"""Application use case for retrieving one task."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# UUID represents the portable identity supplied by an external channel.
from uuid import UUID

# The use case depends on the repository contract, not on a database.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskRepository,
)

# Successful retrieval returns a complete domain entity.
from personal_productivity.tasks.domain.task import Task


class TaskNotFoundError(LookupError):
    """Raised when a requested task does not exist."""


@dataclass(slots=True, kw_only=True)
class GetTask:
    """Retrieve one task through its portable identifier."""

    # Dependency injection keeps storage outside the application logic.
    repository: TaskRepository

    def execute(
        self,
        *,
        task_id: UUID,
    ) -> Task:
        """Return the requested task or report that it is absent."""

        # Runtime validation rejects malformed external identifiers early.
        if not isinstance(task_id, UUID):
            raise TypeError("Task identifier must be a UUID.")

        # Ask the repository port without knowing its storage technology.
        task = self.repository.get_by_id(task_id)

        # Convert storage absence into an explicit application-level outcome.
        if task is None:
            raise TaskNotFoundError(
                f"Task '{task_id}' was not found."
            )

        # Return the authoritative entity obtained from persistence.
        return task
