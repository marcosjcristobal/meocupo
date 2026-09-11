"""Application use case for creating one calendar event."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# CalendarTimeBlock carries the validated interval occupied by the event.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# The use case depends on a port instead of a concrete database adapter.
from personal_productivity.events.application.ports.event_repository import (
    EventRepository,
)

# Event contains the business rules required during creation.
from personal_productivity.events.domain.event import Event


@dataclass(slots=True, kw_only=True)
class CreateEvent:
    """Create and persist one valid calendar event."""

    # The caller supplies an adapter satisfying the repository contract.
    repository: EventRepository

    def execute(
        self,
        *,
        title: str,
        time_block: CalendarTimeBlock,
        description: str | None = None,
    ) -> Event:
        """Build, persist, and return one event."""

        # Construction delegates validation and normalization to the domain.
        event = Event(
            title=title,
            time_block=time_block,
            description=description,
        )

        # Persistence occurs only after valid entity construction succeeds.
        self.repository.add(event)

        # Return the authoritative entity, including its generated identity.
        return event
