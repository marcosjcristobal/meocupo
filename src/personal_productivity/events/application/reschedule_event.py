"""Application use case for rescheduling one calendar event."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# UUID represents the event identity supplied by an external channel.
from uuid import UUID

# CalendarTimeBlock carries the validated replacement allocation.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Existing retrieval centralizes identity validation and absence handling.
from personal_productivity.events.application.get_event import GetEvent

# The use case depends on a repository contract instead of concrete storage.
from personal_productivity.events.application.ports.event_repository import (
    EventRepository,
)

# Event owns the planning rule performed by this operation.
from personal_productivity.events.domain.event import Event


@dataclass(slots=True, kw_only=True)
class RescheduleEvent:
    """Move an existing event and persist its newer allocation."""

    # Any repository adapter satisfying the port can be injected here.
    repository: EventRepository

    def execute(
        self,
        *,
        event_id: UUID,
        time_block: CalendarTimeBlock,
    ) -> Event:
        """Reschedule the identified event and return its updated entity."""

        # Reuse the application's required event lookup behavior.
        event = GetEvent(repository=self.repository).execute(
            event_id=event_id,
        )

        # The domain validates the replacement and lifecycle state.
        event.reschedule(time_block=time_block)

        # Persist only after the domain operation succeeds.
        self.repository.save(event)

        # Return the updated entity to the calling interface.
        return event
