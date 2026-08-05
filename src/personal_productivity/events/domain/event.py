"""Domain entity for a fixed calendar event."""

# Dataclass removes constructor boilerplate while preserving a regular class.
from dataclasses import dataclass, field

# UUID provides portable identity without requiring a database round trip.
from uuid import UUID, uuid4

# Import the shared calendar interval and event lifecycle vocabulary.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)
from personal_productivity.events.domain.event_status import EventStatus

class InvalidEventTransitionError(ValueError):
    """Raised when a requested event lifecycle transition is not allowed."""


@dataclass(slots=True, kw_only=True, eq=False)
class Event:
    """Represent an activity that occupies a concrete calendar interval."""

    # Every event needs a human-readable purpose.
    title: str

    # An event always occupies one exact validated interval.
    time_block: CalendarTimeBlock

    # Optional details may provide context without being required.
    description: str | None = None

    # The factory generates a fresh portable identity for every event.
    id: UUID = field(default_factory=uuid4)

    # Private storage prevents direct lifecycle replacement.
    _status: EventStatus = field(
        default=EventStatus.SCHEDULED,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        """Validate and normalize invariants after initialization."""

        # Runtime validation protects normalization from arbitrary values.
        if not isinstance(self.title, str):
            raise TypeError("Event title must be a string.")

        # Every event must occupy one validated shared calendar interval.
        if not isinstance(self.time_block, CalendarTimeBlock):
            raise TypeError(
                "Event time block must be a CalendarTimeBlock."
            )

        # Optional descriptions must remain textual when they are present.
        if (
            self.description is not None
            and not isinstance(self.description, str)
        ):
            raise TypeError("Event description must be a string.")

        # Remove accidental surrounding whitespace once.
        normalized_title = self.title.strip()

        # An event without meaningful text cannot explain its calendar purpose.
        if not normalized_title:
            raise ValueError("Event title cannot be empty.")

        # Persist one canonical representation for every delivery channel.
        self.title = normalized_title

        # Normalize optional details only when the caller supplied them.
        if self.description is not None:
            normalized_description = self.description.strip()

            # Blank descriptions share one canonical absence representation.
            self.description = normalized_description or None


    def cancel(self) -> None:
        """Cancel an event that is still expected to take place."""

        # Cancellation is valid only from the active scheduled state.
        if self._status is not EventStatus.SCHEDULED:
            raise InvalidEventTransitionError(
                f"Cannot cancel an event from '{self._status.value}'."
            )

        # Persist cancellation only after every transition rule has passed.
        self._status = EventStatus.CANCELLED

    def reschedule(
        self,
        *,
        time_block: CalendarTimeBlock,
    ) -> None:
        """Move a scheduled event to another calendar interval."""

        # Runtime validation preserves the shared calendar abstraction.
        if not isinstance(time_block, CalendarTimeBlock):
            raise TypeError(
                "Event time block must be a CalendarTimeBlock."
            )

        # Cancelled events are terminal historical records.
        if self._status is not EventStatus.SCHEDULED:
            raise InvalidEventTransitionError(
                f"Cannot reschedule an event from '{self._status.value}'."
            )

        # Replace the allocation only after every domain rule has passed.
        self.time_block = time_block

    @property
    def status(self) -> EventStatus:
        """Expose lifecycle state without allowing direct replacement."""

        # Explicit domain operations remain the only state writers.
        return self._status