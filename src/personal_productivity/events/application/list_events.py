"""Application use case for listing calendar events."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# The shared interval defines calendar overlap semantics for event queries.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

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
        time_block: CalendarTimeBlock | None = None,
    ) -> tuple[Event, ...]:
        """Return events matching the requested status and calendar window."""

        # Reject malformed filters before requesting a persistence snapshot.
        if status is not None and not isinstance(status, EventStatus):
            raise TypeError(
                "Event status filter must be an EventStatus."
            )

        # Calendar queries require an already validated shared interval.
        if time_block is not None and not isinstance(
            time_block,
            CalendarTimeBlock,
        ):
            raise TypeError(
                "Event time block filter must be a CalendarTimeBlock."
            )

        # Request one immutable snapshot regardless of the selected filter.
        events = self.repository.list_all()

        # Preserve the original snapshot when the caller requests all events.
        if status is None and time_block is None:
            return events

        # Apply both optional filters without changing repository storage.
        return tuple(
            event
            for event in events
            if (status is None or event.status is status)
            and (
                time_block is None
                or event.time_block.overlaps(time_block)
            )
        )
