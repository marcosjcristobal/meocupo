"""Persistence boundary required by event application use cases."""

# Protocol describes required behavior without choosing an implementation.
from typing import Protocol

# UUID identifies events without exposing database-specific keys.
from uuid import UUID

# The application layer persists complete event domain entities.
from personal_productivity.events.domain.event import Event


class EventAlreadyExistsError(RuntimeError):
    """Raised when storage already contains the event identity."""


class EventNotFoundError(LookupError):
    """Raised when storage does not contain the requested event identity."""


class EventRepository(Protocol):
    """Define how event use cases communicate with persistent storage."""

    def add(
        self,
        event: Event,
    ) -> None:
        """Persist a newly created event."""

        # Concrete adapters will implement this operation.
        ...

    def get_by_id(
        self,
        event_id: UUID,
    ) -> Event | None:
        """Return one event by identity or report that it is absent."""

        # Concrete adapters decide how stored events are located.
        ...

    def list_all(self) -> tuple[Event, ...]:
        """Return an immutable snapshot of every stored event."""

        # Concrete adapters decide how event collections are loaded.
        ...
