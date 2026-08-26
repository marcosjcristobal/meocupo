"""Application use case for scheduling one task."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# UUID represents the portable identity supplied by an external channel.
from uuid import UUID

# CalendarTimeBlock carries a validated exact allocation.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# The use case depends only on the repository contract.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskRepository,
)

# Shared lookup centralizes identity validation and absence handling.
from personal_productivity.tasks.application.task_lookup import (
    get_existing_task,
)

# Task contains the authoritative scheduling operation.
from personal_productivity.tasks.domain.task import Task


@dataclass(slots=True, kw_only=True)
class ScheduleTask:
    """Assign calendar time to one task and persist its planning state."""

    # Dependency injection keeps storage outside application logic.
    repository: TaskRepository

    def execute(
        self,
        *,
        task_id: UUID,
        time_block: CalendarTimeBlock,
    ) -> Task:
        """Assign or replace one exact calendar allocation."""

        # Delegate shared validation and required retrieval.
        task = get_existing_task(
            repository=self.repository,
            task_id=task_id,
        )

        # Delegate type and editability rules to the domain entity.
        task.schedule(time_block=time_block)

        # Persist only after the domain operation succeeds.
        self.repository.save(task)

        # Return the updated entity to the calling interface.
        return task
