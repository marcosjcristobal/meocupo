"""In-memory repository adapter for event entities."""

# UUID provides the key type used by the repository contract.
from uuid import UUID

# Duplicate identities use one adapter-independent repository outcome.
from personal_productivity.events.application.ports.event_repository import (
    EventAlreadyExistsError,
)

# Event is the complete domain entity stored by this adapter.
from personal_productivity.events.domain.event import Event


class InMemoryEventRepository:
    """Store event entities in process memory by their identity."""

    def __init__(self) -> None:
        """Initialize isolated empty event storage."""

        # The dictionary provides direct identity-based access.
        self._events_by_id: dict[UUID, Event] = {}

    def add(
        self,
        event: Event,
    ) -> None:
        """Store a newly created event under its identity."""

        # Reject arbitrary values before reading domain attributes.
        if not isinstance(event, Event):
            raise TypeError("Event must be an Event.")

        # Creation must never overwrite an event already under this identity.
        if event.id in self._events_by_id:
            raise EventAlreadyExistsError(
                f"Event '{event.id}' already exists."
            )

        # Keep the authoritative domain entity available to later use cases.
        self._events_by_id[event.id] = event

    def get_by_id(
        self,
        event_id: UUID,
    ) -> Event | None:
        """Return one stored event or None when its identity is absent."""

        # Reject malformed keys before accessing repository storage.
        if not isinstance(event_id, UUID):
            raise TypeError("Event identifier must be a UUID.")

        # Dictionary lookup preserves the repository's optional result.
        return self._events_by_id.get(event_id)

    def list_all(self) -> tuple[Event, ...]:
        """Return an immutable snapshot of all stored events."""

        # Copy dictionary values into a tuple without exposing storage itself.
        return tuple(self._events_by_id.values())
