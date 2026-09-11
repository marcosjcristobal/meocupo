"""Persistence boundary required by event application use cases."""

# Protocol describes required behavior without choosing an implementation.
from typing import Protocol

# The application layer persists complete event domain entities.
from personal_productivity.events.domain.event import Event


class EventRepository(Protocol):
    """Define how event use cases communicate with persistent storage."""

    def add(
        self,
        event: Event,
    ) -> None:
        """Persist a newly created event."""

        # Concrete adapters will implement this operation.
        ...
