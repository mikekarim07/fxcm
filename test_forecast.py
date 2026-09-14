"""
Sanity checks for core/model.py and core/forecast.py. Not exhaustive --
see the architecture review's Testing Strategy section for the fuller
plan (property-based tests on the curve, golden-master tests per
scenario, a regression guard on history never changing).
"""

from datetime import date, timedelta

from core.model import ActualEntry, PlanVersion, Settings
from core.forecast import build_daily_series, build_monthly_summary


def test_curve_endpoints_and_monotonic():
    v = PlanVersion(
        version_id=1, effective_date=date(2026, 1, 1), starting_balance=1000,
        target_balance=2_000_000, end_date=date(2041, 1, 1),
        peak_position=0.5, curve_intensity=9,
    )
    assert v.target_balance_at(date(2026, 1, 1)) == 1000
    assert abs(v.target_balance_at(date(2041, 1, 1)) - 2_000_000) < 1e-6
    mid = v.target_balance_at(date(2033, 7, 2))
    # peak_position=0.5 -> midpoint should sit close to 50% of the way there
    assert 900_000 < mid < 1_100_000
    # Monotonic non-decreasing across the horizon
    prev = -1
    d = v.effective_date
    while d <= v.end_date:
        bal = v.target_balance_at(d)
        assert bal >= prev
        prev = bal
        d += timedelta(days=90)


def test_intensity_zero_is_linear():
    v = PlanVersion(
        version_id=1, effective_date=date(2026, 1, 1), starting_balance=0,
        target_balance=100, end_date=date(2026, 1, 11), curve_intensity=0,
    )
    # x = 0.5 (halfway) should give exactly 50 when intensity == 0
    assert abs(v.target_balance_at(date(2026, 1, 6)) - 50) < 1e-6


def test_retroactive_actual_rebuild():
    """Monday/Tuesday retroactive-entry example from the spec: entering
    Monday and Tuesday actuals on Thursday must rebuild both days
    chronologically and leave the forecast starting from Wednesday."""
    settings = Settings(initial_balance=1000, initial_date=date(2026, 3, 2))  # Monday
    v = PlanVersion(
        version_id=1, effective_date=date(2026, 3, 2), starting_balance=1000,
        target_balance=2000, end_date=date(2026, 3, 20),
    )
    actuals = [
        ActualEntry(date(2026, 3, 2), 8, date(2026, 3, 5), date(2026, 3, 5)),
        ActualEntry(date(2026, 3, 3), 9, date(2026, 3, 5), date(2026, 3, 5)),
    ]
    result = build_daily_series(settings, [v], actuals, as_of=date(2026, 3, 5))
    df = result.daily.set_index("date")

    assert df.loc[date(2026, 3, 2), "real_balance"] == 1008
    assert df.loc[date(2026, 3, 3), "real_balance"] == 1017
    assert result.forecast_base_date == date(2026, 3, 3)
    assert result.forecast_base_balance == 1017
    # Wednesday onward should be marked as forecast, not history
    assert df.loc[date(2026, 3, 4), "is_forecast"] == True  # noqa: E712


def test_saving_new_version_never_changes_history():
    """The core 'never rewrite history' guarantee: build the daily series
    before and after adding a new plan version, and confirm every day up
    to the forecast base is byte-identical."""
    settings = Settings(initial_balance=1000, initial_date=date(2026, 1, 5))
    v1 = PlanVersion(
        version_id=1, effective_date=date(2026, 1, 5), starting_balance=1000,
        target_balance=2_000_000, end_date=date(2041, 1, 5),
    )
    actuals = [ActualEntry(date(2026, 1, 5), 50, date(2026, 1, 6), date(2026, 1, 6))]

    before = build_daily_series(settings, [v1], actuals, as_of=date(2026, 1, 6)).daily
    before_hist = before[before["date"] <= date(2026, 1, 5)].reset_index(drop=True)

    v2 = PlanVersion(
        version_id=2, effective_date=date(2026, 2, 1), starting_balance=1050,
        target_balance=1_000_000, end_date=date(2036, 1, 5),
    )
    after = build_daily_series(settings, [v1, v2], actuals, as_of=date(2026, 2, 1)).daily
    after_hist = after[after["date"] <= date(2026, 1, 5)].reset_index(drop=True)

    assert before_hist["target_balance"].tolist() == after_hist["target_balance"].tolist()
    assert before_hist["real_balance"].tolist() == after_hist["real_balance"].tolist()


def test_monthly_summary_aggregates_from_daily_only():
    settings = Settings(initial_balance=1000, initial_date=date(2026, 1, 2))
    v = PlanVersion(
        version_id=1, effective_date=date(2026, 1, 2), starting_balance=1000,
        target_balance=1500, end_date=date(2026, 4, 30),
    )
    actuals = [ActualEntry(date(2026, 1, 2), 20, date(2026, 1, 2), date(2026, 1, 2))]
    daily = build_daily_series(settings, [v], actuals, as_of=date(2026, 1, 2)).daily
    monthly = build_monthly_summary(daily)
    assert not monthly.empty
    assert set(["starting_target_balance", "ending_target_balance", "target_pnl",
                "target_return", "real_pnl", "real_ending_balance", "variance",
                "plan_version"]).issubset(monthly.columns)


if __name__ == "__main__":
    test_curve_endpoints_and_monotonic()
    test_intensity_zero_is_linear()
    test_retroactive_actual_rebuild()
    test_saving_new_version_never_changes_history()
    test_monthly_summary_aggregates_from_daily_only()
    print("All sanity checks passed.")
