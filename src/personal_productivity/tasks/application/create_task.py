"""Application use case for creating a task."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# The use case depends on a port instead of a concrete database adapter.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskRepository,
)

# Task contains the business rules required during creation.
from personal_productivity.tasks.domain.task import Task

# Priority uses the domain's explicit and serializable vocabulary.
from personal_productivity.tasks.domain.task_priority import TaskPriority

# Calendar intervals represent optional reserved work.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Deadlines preserve the user's temporal completion commitment.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


@dataclass(slots=True, kw_only=True)
class CreateTask:
    """Create and persist one valid task."""

    # The caller supplies an adapter that satisfies the repository contract.
    repository: TaskRepository

    def execute(
        self,
        *,
        title: str,
        description: str | None = None,
        estimated_minutes: int | None = None,
        deadline: TaskDeadline | None = None,
        time_block: CalendarTimeBlock | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Task:
        """Build, persist, and return a task."""

        # Construction delegates all validation and normalization to the domain.
        task = Task(
            title=title,
            description=description,
            estimated_minutes=estimated_minutes,
            deadline=deadline,
            time_block=time_block,
            priority=priority,
        )

        # Persistence occurs only after the entity has been created successfully.
        self.repository.add(task)

        # Return the authoritative entity, including its generated identifier.
        return task
