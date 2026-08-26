"""Application use case for pausing one task."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# UUID represents the portable identity supplied by an external channel.
from uuid import UUID

# The use case depends only on the repository contract.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskRepository,
)

# Shared lookup centralizes identity validation and absence handling.
from personal_productivity.tasks.application.task_lookup import (
    get_existing_task,
)

# Task contains the authoritative lifecycle transition.
from personal_productivity.tasks.domain.task import Task


@dataclass(slots=True, kw_only=True)
class PauseTask:
    """Pause one active task and persist its newer state."""

    # Dependency injection keeps storage outside application logic.
    repository: TaskRepository

    def execute(
        self,
        *,
        task_id: UUID,
    ) -> Task:
        """Move one active task into paused work."""

        # Delegate shared validation and required retrieval.
        task = get_existing_task(
            repository=self.repository,
            task_id=task_id,
        )

        # Delegate lifecycle rules to the domain entity itself.
        task.pause()

        # Persist only after the domain transition succeeds.
        self.repository.save(task)

        # Return the updated entity to the calling interface.
        return task
