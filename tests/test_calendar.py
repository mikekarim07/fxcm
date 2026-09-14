from datetime import date

import pytest

from core.calendar import (
    BusinessCalendar,
    BusinessSchedule,
    CalendarError,
    build_business_schedule,
)


def test_default_calendar_is_monday_to_friday():

    calendar = BusinessCalendar()

    monday = date(2026, 9, 14)
    friday = date(2026, 9, 18)
    saturday = date(2026, 9, 19)
    sunday = date(2026, 9, 20)

    assert calendar.is_business_day(monday)
    assert calendar.is_business_day(friday)

    assert not calendar.is_business_day(saturday)
    assert not calendar.is_business_day(sunday)


def test_business_days_exclude_weekends():

    calendar = BusinessCalendar()

    days = calendar.business_days(
        date(2026, 9, 14),
        date(2026, 9, 20),
    )

    assert days == (
        date(2026, 9, 14),
        date(2026, 9, 15),
        date(2026, 9, 16),
        date(2026, 9, 17),
        date(2026, 9, 18),
    )


def test_next_business_day_skips_weekend():

    calendar = BusinessCalendar()

    friday = date(2026, 9, 18)

    assert calendar.next_business_day(friday) == date(
        2026,
        9,
        21,
    )


def test_previous_business_day_skips_weekend():

    calendar = BusinessCalendar()

    monday = date(2026, 9, 21)

    assert calendar.previous_business_day(monday) == date(
        2026,
        9,
        18,
    )


def test_holiday_is_excluded():

    holiday = date(2026, 9, 16)

    calendar = BusinessCalendar(
        holidays=frozenset({holiday})
    )

    days = calendar.business_days(
        date(2026, 9, 14),
        date(2026, 9, 18),
    )

    assert holiday not in days

    assert len(days) == 4


def test_blocked_date_is_excluded():

    blocked = date(2026, 9, 17)

    calendar = BusinessCalendar(
        blocked_dates=frozenset({blocked})
    )

    assert not calendar.is_business_day(blocked)


def test_added_business_date_can_open_saturday():

    saturday = date(2026, 9, 19)

    calendar = BusinessCalendar(
        added_business_dates=frozenset({saturday})
    )

    assert calendar.is_business_day(saturday)


def test_blocked_date_has_priority_over_added_date():

    saturday = date(2026, 9, 19)

    calendar = BusinessCalendar(
        blocked_dates=frozenset({saturday}),
        added_business_dates=frozenset({saturday}),
    )

    assert not calendar.is_business_day(saturday)


def test_schedule_positions_use_business_time():

    calendar = BusinessCalendar()

    schedule = build_business_schedule(
        calendar=calendar,
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 18),
    )

    assert schedule.periods == 5

    assert schedule.position(
        date(2026, 9, 14)
    ) == pytest.approx(0.20)

    assert schedule.position(
        date(2026, 9, 15)
    ) == pytest.approx(0.40)

    assert schedule.position(
        date(2026, 9, 16)
    ) == pytest.approx(0.60)

    assert schedule.position(
        date(2026, 9, 17)
    ) == pytest.approx(0.80)

    assert schedule.position(
        date(2026, 9, 18)
    ) == pytest.approx(1.00)


def test_weekend_does_not_consume_curve_position():

    calendar = BusinessCalendar()

    schedule = build_business_schedule(
        calendar=calendar,
        start_date=date(2026, 9, 18),  # Friday
        end_date=date(2026, 9, 22),    # Tuesday
    )

    assert schedule.business_days == (
        date(2026, 9, 18),
        date(2026, 9, 21),
        date(2026, 9, 22),
    )

    assert schedule.position(
        date(2026, 9, 18)
    ) == pytest.approx(1 / 3)

    assert schedule.position(
        date(2026, 9, 21)
    ) == pytest.approx(2 / 3)

    assert schedule.position(
        date(2026, 9, 22)
    ) == pytest.approx(1.0)


def test_calendar_boundaries_can_be_weekends():

    calendar = BusinessCalendar()

    schedule = build_business_schedule(
        calendar=calendar,
        start_date=date(2026, 9, 19),  # Saturday
        end_date=date(2026, 9, 27),    # Sunday
    )

    assert schedule.first_business_date == date(
        2026,
        9,
        21,
    )

    assert schedule.last_business_date == date(
        2026,
        9,
        25,
    )

    assert schedule.periods == 5


def test_previous_and_next_inside_schedule():

    calendar = BusinessCalendar()

    schedule = build_business_schedule(
        calendar=calendar,
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 18),
    )

    assert schedule.previous_business_date(
        date(2026, 9, 14)
    ) is None

    assert schedule.previous_business_date(
        date(2026, 9, 16)
    ) == date(2026, 9, 15)

    assert schedule.next_business_date(
        date(2026, 9, 16)
    ) == date(2026, 9, 17)

    assert schedule.next_business_date(
        date(2026, 9, 18)
    ) is None


def test_invalid_date_range_raises():

    calendar = BusinessCalendar()

    with pytest.raises(CalendarError):

        build_business_schedule(
            calendar=calendar,
            start_date=date(2026, 9, 20),
            end_date=date(2026, 9, 10),
        )


def test_range_without_business_days_raises():

    calendar = BusinessCalendar()

    with pytest.raises(CalendarError):

        build_business_schedule(
            calendar=calendar,
            start_date=date(2026, 9, 19),  # Saturday
            end_date=date(2026, 9, 20),    # Sunday
        )


def test_schedule_rejects_non_business_date_position():

    calendar = BusinessCalendar()

    schedule = build_business_schedule(
        calendar=calendar,
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 18),
    )

    with pytest.raises(CalendarError):

        schedule.position(
            date(2026, 9, 19)
        )
