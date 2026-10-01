"""Application use case for listing calendar events."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# The use case depends on a repository port, not a storage implementation.
from personal_productivity.events.application.ports.event_repository import (
    EventRepository,
)

# Event represents each complete entity in the returned snapshot.
from personal_productivity.events.domain.event import Event
from personal_productivity.events.domain.event_status import EventStatus


@dataclass(slots=True, kw_only=True)
class ListEvents:
    """Retrieve a snapshot containing all stored calendar events."""

    # Dependency injection allows the same use case to work with any adapter.
    repository: EventRepository

    def execute(
        self,
        *,
        status: EventStatus | None = None,
    ) -> tuple[Event, ...]:
        """Return all events or only those with the requested status."""

        # Reject malformed filters before requesting a persistence snapshot.
        if status is not None and not isinstance(status, EventStatus):
            raise TypeError(
                "Event status filter must be an EventStatus."
            )

        # Request one immutable snapshot regardless of the selected filter.
        events = self.repository.list_all()

        # Preserve the original snapshot when the caller requests all events.
        if status is None:
            return events

        # Select matching domain states without changing repository storage.
        return tuple(event for event in events if event.status is status)
