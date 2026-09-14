from datetime import date

from core.calendar import (
    BusinessCalendar,
    CalendarError,
    build_business_schedule,
)


def _approx_equal(a, b, tolerance=1e-10):
    return abs(a - b) <= tolerance


def run_calendar_self_tests():
    """
    Runs Business Calendar Engine tests without pytest.

    Returns:
        list[dict]

    Each result contains:
        name
        status
        details
    """

    results = []

    def run_test(name, test_function):

        try:

            test_function()

            results.append({
                "name": name,
                "status": "PASS",
                "details": "",
            })

        except Exception as exc:

            results.append({
                "name": name,
                "status": "FAIL",
                "details": str(exc),
            })

    # -----------------------------------------------------
    # TEST 1
    # Monday-Friday calendar
    # -----------------------------------------------------

    def test_default_weekdays():

        calendar = BusinessCalendar()

        assert calendar.is_business_day(
            date(2026, 9, 14)
        )

        assert calendar.is_business_day(
            date(2026, 9, 18)
        )

        assert not calendar.is_business_day(
            date(2026, 9, 19)
        )

        assert not calendar.is_business_day(
            date(2026, 9, 20)
        )

    run_test(
        "Default calendar = Monday-Friday",
        test_default_weekdays,
    )

    # -----------------------------------------------------
    # TEST 2
    # Weekend exclusion
    # -----------------------------------------------------

    def test_weekend_exclusion():

        calendar = BusinessCalendar()

        days = calendar.business_days(
            date(2026, 9, 14),
            date(2026, 9, 20),
        )

        expected = (
            date(2026, 9, 14),
            date(2026, 9, 15),
            date(2026, 9, 16),
            date(2026, 9, 17),
            date(2026, 9, 18),
        )

        assert days == expected

    run_test(
        "Weekends are excluded",
        test_weekend_exclusion,
    )

    # -----------------------------------------------------
    # TEST 3
    # Next business day
    # -----------------------------------------------------

    def test_next_business_day():

        calendar = BusinessCalendar()

        result = calendar.next_business_day(
            date(2026, 9, 18)
        )

        assert result == date(
            2026,
            9,
            21,
        )

    run_test(
        "Friday → next business day = Monday",
        test_next_business_day,
    )

    # -----------------------------------------------------
    # TEST 4
    # Previous business day
    # -----------------------------------------------------

    def test_previous_business_day():

        calendar = BusinessCalendar()

        result = calendar.previous_business_day(
            date(2026, 9, 21)
        )

        assert result == date(
            2026,
            9,
            18,
        )

    run_test(
        "Monday → previous business day = Friday",
        test_previous_business_day,
    )

    # -----------------------------------------------------
    # TEST 5
    # Holiday
    # -----------------------------------------------------

    def test_holiday():

        holiday = date(
            2026,
            9,
            16,
        )

        calendar = BusinessCalendar(
            holidays=frozenset({
                holiday
            })
        )

        assert not calendar.is_business_day(
            holiday
        )

        days = calendar.business_days(
            date(2026, 9, 14),
            date(2026, 9, 18),
        )

        assert len(days) == 4

    run_test(
        "Holiday closes a weekday",
        test_holiday,
    )

    # -----------------------------------------------------
    # TEST 6
    # Blocked date
    # -----------------------------------------------------

    def test_blocked_date():

        blocked = date(
            2026,
            9,
            17,
        )

        calendar = BusinessCalendar(
            blocked_dates=frozenset({
                blocked
            })
        )

        assert not calendar.is_business_day(
            blocked
        )

    run_test(
        "Blocked date is excluded",
        test_blocked_date,
    )

    # -----------------------------------------------------
    # TEST 7
    # Added Saturday
    # -----------------------------------------------------

    def test_added_business_day():

        saturday = date(
            2026,
            9,
            19,
        )

        calendar = BusinessCalendar(
            added_business_dates=frozenset({
                saturday
            })
        )

        assert calendar.is_business_day(
            saturday
        )

    run_test(
        "Manual business date can open Saturday",
        test_added_business_day,
    )

    # -----------------------------------------------------
    # TEST 8
    # Blocked has priority
    # -----------------------------------------------------

    def test_blocked_priority():

        saturday = date(
            2026,
            9,
            19,
        )

        calendar = BusinessCalendar(
            blocked_dates=frozenset({
                saturday
            }),
            added_business_dates=frozenset({
                saturday
            }),
        )

        assert not calendar.is_business_day(
            saturday
        )

    run_test(
        "Blocked date overrides manual opening",
        test_blocked_priority,
    )

    # -----------------------------------------------------
    # TEST 9
    # Business positions
    # -----------------------------------------------------

    def test_business_positions():

        calendar = BusinessCalendar()

        schedule = build_business_schedule(
            calendar=calendar,
            start_date=date(
                2026,
                9,
                14,
            ),
            end_date=date(
                2026,
                9,
                18,
            ),
        )

        assert schedule.periods == 5

        assert _approx_equal(
            schedule.position(
                date(2026, 9, 14)
            ),
            0.20,
        )

        assert _approx_equal(
            schedule.position(
                date(2026, 9, 15)
            ),
            0.40,
        )

        assert _approx_equal(
            schedule.position(
                date(2026, 9, 16)
            ),
            0.60,
        )

        assert _approx_equal(
            schedule.position(
                date(2026, 9, 17)
            ),
            0.80,
        )

        assert _approx_equal(
            schedule.position(
                date(2026, 9, 18)
            ),
            1.00,
        )

    run_test(
        "Business-time positions = 1/N ... N/N",
        test_business_positions,
    )

    # -----------------------------------------------------
    # TEST 10
    # Weekend consumes no curve time
    # -----------------------------------------------------

    def test_weekend_no_curve_time():

        calendar = BusinessCalendar()

        schedule = build_business_schedule(
            calendar=calendar,
            start_date=date(
                2026,
                9,
                18,
            ),
            end_date=date(
                2026,
                9,
                22,
            ),
        )

        expected = (
            date(2026, 9, 18),
            date(2026, 9, 21),
            date(2026, 9, 22),
        )

        assert schedule.business_days == expected

        assert _approx_equal(
            schedule.position(
                date(2026, 9, 18)
            ),
            1 / 3,
        )

        assert _approx_equal(
            schedule.position(
                date(2026, 9, 21)
            ),
            2 / 3,
        )

        assert _approx_equal(
            schedule.position(
                date(2026, 9, 22)
            ),
            1.0,
        )

    run_test(
        "Weekend consumes zero curve time",
        test_weekend_no_curve_time,
    )

    # -----------------------------------------------------
    # TEST 11
    # Weekend boundaries
    # -----------------------------------------------------

    def test_weekend_boundaries():

        calendar = BusinessCalendar()

        schedule = build_business_schedule(
            calendar=calendar,
            start_date=date(
                2026,
                9,
                19,
            ),
            end_date=date(
                2026,
                9,
                27,
            ),
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

    run_test(
        "Weekend plan boundaries resolve correctly",
        test_weekend_boundaries,
    )

    # -----------------------------------------------------
    # TEST 12
    # Previous / next inside schedule
    # -----------------------------------------------------

    def test_schedule_neighbors():

        calendar = BusinessCalendar()

        schedule = build_business_schedule(
            calendar=calendar,
            start_date=date(
                2026,
                9,
                14,
            ),
            end_date=date(
                2026,
                9,
                18,
            ),
        )

        assert (
            schedule.previous_business_date(
                date(2026, 9, 14)
            )
            is None
        )

        assert schedule.previous_business_date(
            date(2026, 9, 16)
        ) == date(
            2026,
            9,
            15,
        )

        assert schedule.next_business_date(
            date(2026, 9, 16)
        ) == date(
            2026,
            9,
            17,
        )

        assert (
            schedule.next_business_date(
                date(2026, 9, 18)
            )
            is None
        )

    run_test(
        "Schedule previous/next dates work",
        test_schedule_neighbors,
    )

    # -----------------------------------------------------
    # TEST 13
    # Invalid range
    # -----------------------------------------------------

    def test_invalid_range():

        calendar = BusinessCalendar()

        error_raised = False

        try:

            build_business_schedule(
                calendar=calendar,
                start_date=date(
                    2026,
                    9,
                    20,
                ),
                end_date=date(
                    2026,
                    9,
                    10,
                ),
            )

        except CalendarError:

            error_raised = True

        assert error_raised

    run_test(
        "Invalid date range raises CalendarError",
        test_invalid_range,
    )

    # -----------------------------------------------------
    # TEST 14
    # Zero business days
    # -----------------------------------------------------

    def test_zero_business_days():

        calendar = BusinessCalendar()

        error_raised = False

        try:

            build_business_schedule(
                calendar=calendar,
                start_date=date(
                    2026,
                    9,
                    19,
                ),
                end_date=date(
                    2026,
                    9,
                    20,
                ),
            )

        except CalendarError:

            error_raised = True

        assert error_raised

    run_test(
        "Range with zero business days is rejected",
        test_zero_business_days,
    )

    return results
