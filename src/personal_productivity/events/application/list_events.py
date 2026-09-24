"""Application use case for listing calendar events."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# The use case depends on a repository port, not a storage implementation.
from personal_productivity.events.application.ports.event_repository import (
    EventRepository,
)

# Event represents each complete entity in the returned snapshot.
from personal_productivity.events.domain.event import Event


@dataclass(slots=True, kw_only=True)
class ListEvents:
    """Retrieve a snapshot containing all stored calendar events."""

    # Dependency injection allows the same use case to work with any adapter.
    repository: EventRepository

    def execute(self) -> tuple[Event, ...]:
        """Return the repository's immutable event collection."""

        # The repository owns collection retrieval and snapshot creation.
        return self.repository.list_all()
