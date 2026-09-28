"""Application use case for cancelling one calendar event."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# UUID represents the event identity supplied by an external channel.
from uuid import UUID

# Existing retrieval centralizes identity validation and absence handling.
from personal_productivity.events.application.get_event import GetEvent

# The use case depends on a repository contract instead of concrete storage.
from personal_productivity.events.application.ports.event_repository import (
    EventRepository,
)

# Event owns the lifecycle transition performed by this operation.
from personal_productivity.events.domain.event import Event


@dataclass(slots=True, kw_only=True)
class CancelEvent:
    """Cancel one existing event and persist its newer lifecycle state."""

    # Any repository adapter satisfying the port can be injected here.
    repository: EventRepository

    def execute(self, *, event_id: UUID) -> Event:
        """Cancel the event identified by UUID and return it."""

        # Reuse the application's required event lookup behavior.
        event = GetEvent(repository=self.repository).execute(
            event_id=event_id,
        )

        # The domain decides whether this lifecycle transition is valid.
        event.cancel()

        # Persist only after the domain transition succeeds.
        self.repository.save(event)

        # Return the updated entity to the calling interface.
        return event
