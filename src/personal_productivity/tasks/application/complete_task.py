"""Application use case for completing one task."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# Datetime represents the authoritative completion instant.
from datetime import datetime

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
class CompleteTask:
    """Complete one unfinished task and persist its historical state."""

    # Dependency injection keeps storage outside application logic.
    repository: TaskRepository

    def execute(
        self,
        *,
        task_id: UUID,
        completed_at: datetime,
    ) -> Task:
        """Complete one task at an explicit absolute instant."""

        # Delegate shared validation and required retrieval.
        task = get_existing_task(
            repository=self.repository,
            task_id=task_id,
        )

        # Delegate timestamp and lifecycle invariants to the domain.
        task.complete(completed_at=completed_at)

        # Persist only after the domain transition succeeds.
        self.repository.save(task)

        # Return the updated entity to the calling interface.
        return task
