from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable


class CalendarError(ValueError):
    """Raised when a business-calendar operation is invalid."""


@dataclass(frozen=True)
class BusinessCalendar:
    """
    Defines which dates are considered operational/business days.

    Default behavior:
    - Monday through Friday are business days.
    - Saturday and Sunday are closed.

    Future-ready:
    - holidays can close normal weekdays.
    - blocked_dates can manually close any date.
    - added_business_dates can explicitly open a normally closed date.

    Precedence:
    1. blocked_dates -> CLOSED
    2. added_business_dates -> OPEN
    3. holidays -> CLOSED
    4. business_weekdays rule
    """

    business_weekdays: frozenset[int] = field(
        default_factory=lambda: frozenset({0, 1, 2, 3, 4})
    )

    holidays: frozenset[date] = field(
        default_factory=frozenset
    )

    blocked_dates: frozenset[date] = field(
        default_factory=frozenset
    )

    added_business_dates: frozenset[date] = field(
        default_factory=frozenset
    )

    def __post_init__(self):
        invalid_weekdays = [
            weekday
            for weekday in self.business_weekdays
            if weekday < 0 or weekday > 6
        ]

        if invalid_weekdays:
            raise CalendarError(
                "business_weekdays must contain values from 0 to 6."
            )

    def is_business_day(self, day: date) -> bool:
        """
        Returns True if the supplied date is operational.
        """

        if day in self.blocked_dates:
            return False

        if day in self.added_business_dates:
            return True

        if day in self.holidays:
            return False

        return day.weekday() in self.business_weekdays

    def next_business_day(self, day: date) -> date:
        """
        Returns the first business day strictly AFTER `day`.
        """

        candidate = day + timedelta(days=1)

        while not self.is_business_day(candidate):
            candidate += timedelta(days=1)

        return candidate

    def previous_business_day(self, day: date) -> date:
        """
        Returns the first business day strictly BEFORE `day`.
        """

        candidate = day - timedelta(days=1)

        while not self.is_business_day(candidate):
            candidate -= timedelta(days=1)

        return candidate

    def business_day_on_or_after(self, day: date) -> date:
        """
        Returns `day` if it is operational.
        Otherwise returns the next operational date.
        """

        if self.is_business_day(day):
            return day

        candidate = day

        while not self.is_business_day(candidate):
            candidate += timedelta(days=1)

        return candidate

    def business_day_on_or_before(self, day: date) -> date:
        """
        Returns `day` if it is operational.
        Otherwise returns the previous operational date.
        """

        if self.is_business_day(day):
            return day

        candidate = day

        while not self.is_business_day(candidate):
            candidate -= timedelta(days=1)

        return candidate

    def business_days(
        self,
        start_date: date,
        end_date: date,
    ) -> tuple[date, ...]:
        """
        Returns all business dates inside the inclusive calendar range.
        """

        if end_date < start_date:
            raise CalendarError(
                "end_date cannot be earlier than start_date."
            )

        days = []

        candidate = start_date

        while candidate <= end_date:

            if self.is_business_day(candidate):
                days.append(candidate)

            candidate += timedelta(days=1)

        return tuple(days)

    def business_day_count(
        self,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        Counts operational dates in an inclusive date range.
        """

        return len(
            self.business_days(
                start_date=start_date,
                end_date=end_date,
            )
        )


@dataclass(frozen=True)
class BusinessSchedule:
    """
    Represents the operational timeline of a plan.

    Important convention:

    The opening balance exists BEFORE the first business day.

    Therefore, if a schedule contains N business days:

        first business day -> position 1 / N
        ...
        final business day -> position N / N = 1

    This guarantees that:
    - the first business day may generate P&L;
    - the final business day lands exactly at x = 1.
    """

    requested_start_date: date
    requested_end_date: date
    business_days: tuple[date, ...]

    def __post_init__(self):

        if self.requested_end_date < self.requested_start_date:
            raise CalendarError(
                "requested_end_date cannot be earlier "
                "than requested_start_date."
            )

        if not self.business_days:
            raise CalendarError(
                "The selected date range contains no business days."
            )

        if tuple(sorted(self.business_days)) != self.business_days:
            raise CalendarError(
                "business_days must be chronologically ordered."
            )

        if len(set(self.business_days)) != len(self.business_days):
            raise CalendarError(
                "business_days cannot contain duplicates."
            )

    @property
    def first_business_date(self) -> date:
        return self.business_days[0]

    @property
    def last_business_date(self) -> date:
        return self.business_days[-1]

    @property
    def periods(self) -> int:
        """
        Number of target-generating business periods.
        """

        return len(self.business_days)

    def contains(self, day: date) -> bool:
        return day in self.business_days

    def ordinal(self, day: date) -> int:
        """
        Returns the 1-based operational period number.

        Example:
            first business day -> 1
            second -> 2
        """

        try:
            return self.business_days.index(day) + 1

        except ValueError as exc:
            raise CalendarError(
                f"{day.isoformat()} is not a business date "
                "inside this schedule."
            ) from exc

    def position(self, day: date) -> float:
        """
        Returns normalized business-time position in the interval (0, 1].

        Example with five business days:

            Day 1 -> 0.20
            Day 2 -> 0.40
            Day 3 -> 0.60
            Day 4 -> 0.80
            Day 5 -> 1.00
        """

        return self.ordinal(day) / self.periods

    def previous_business_date(
        self,
        day: date,
    ) -> date | None:
        """
        Returns the previous date INSIDE the schedule.

        None means the supplied date is the first target period.
        """

        ordinal = self.ordinal(day)

        if ordinal == 1:
            return None

        return self.business_days[ordinal - 2]

    def next_business_date(
        self,
        day: date,
    ) -> date | None:
        """
        Returns the following date INSIDE the schedule.

        None means the supplied date is the final period.
        """

        ordinal = self.ordinal(day)

        if ordinal == self.periods:
            return None

        return self.business_days[ordinal]


def build_business_schedule(
    calendar: BusinessCalendar,
    start_date: date,
    end_date: date,
) -> BusinessSchedule:
    """
    Creates the target-generating schedule for a plan.

    Calendar boundaries may themselves be non-business days.

    Example:
        start_date = Saturday
        end_date   = following Sunday

    The resulting schedule will contain the operational dates
    that exist inside that calendar interval.
    """

    business_days = calendar.business_days(
        start_date=start_date,
        end_date=end_date,
    )

    return BusinessSchedule(
        requested_start_date=start_date,
        requested_end_date=end_date,
        business_days=business_days,
    )
