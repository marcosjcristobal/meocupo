"""Application use case for retrieving one required event."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# UUID represents the portable event identity supplied by a caller.
from uuid import UUID

# Repository contracts keep retrieval independent from concrete storage.
from personal_productivity.events.application.ports.event_repository import (
    EventNotFoundError,
    EventRepository,
)

# Event is the domain entity returned through the application boundary.
from personal_productivity.events.domain.event import Event


@dataclass(slots=True, kw_only=True)
class GetEvent:
    """Retrieve one existing event by its portable identity."""

    # Dependency injection allows any compatible persistence adapter.
    repository: EventRepository

    def execute(
        self,
        *,
        event_id: UUID,
    ) -> Event:
        """Return one event or report that its identity is absent."""

        # Reject malformed external identities before querying persistence.
        if not isinstance(event_id, UUID):
            raise TypeError("Event identifier must be a UUID.")

        # Ask persistence for the entity without exposing storage details.
        event = self.repository.get_by_id(event_id)

        # Absence becomes one stable application-level outcome.
        if event is None:
            raise EventNotFoundError(
                f"Event '{event_id}' was not found."
            )

        # Return the authoritative entity reconstructed by persistence.
        return event
