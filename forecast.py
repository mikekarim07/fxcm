"""
The reforecast engine.

This module has exactly one job: turn (Settings, list[PlanVersion],
list[ActualEntry]) into a daily DataFrame, then a monthly DataFrame.
Nothing here writes anything back to storage -- call build_daily_series()
fresh on every Streamlit rerun. That statelessness is what makes the
"past is frozen, future is recalculated" rule hold without any special-
case bookkeeping: history is frozen because it is computed from frozen
(immutable) PlanVersion rows, and the future is recalculated because it
is re-derived from the latest real balance every single call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from .model import ActualEntry, PlanVersion, Settings


def business_day_calendar(start: date, end: date) -> list[date]:
    """Mon-Fri calendar, inclusive. Holidays/custom calendars are a
    documented future extension point (architecture review, BUSINESS
    DAYS), not handled here."""
    if end < start:
        return []
    return list(pd.bdate_range(start=start, end=end).date)


def effective_version_for(on_date: date, versions_sorted: list[PlanVersion]) -> PlanVersion:
    """The plan version whose effective_date is the latest one <= on_date.
    Ties (two versions saved same day) are broken by the higher
    version_id -- see architecture review, point 15. `versions_sorted`
    must already be sorted ascending by (effective_date, version_id)."""
    candidates = [v for v in versions_sorted if v.effective_date <= on_date]
    if not candidates:
        raise ValueError(f"No plan version is effective on {on_date}")
    return max(candidates, key=lambda v: (v.effective_date, v.version_id))


@dataclass
class DailySeriesResult:
    daily: pd.DataFrame
    forecast_base_date: date
    forecast_base_balance: float
    last_actual_date: Optional[date]


def build_daily_series(
    settings: Settings,
    versions: list[PlanVersion],
    actuals: list[ActualEntry],
    as_of: date,
) -> DailySeriesResult:
    """
    Build the full daily target / actual / forecast series.

    Historical days (on or before the latest actual's date) use the
    plan version that was effective ON THAT DAY, evaluated with THAT
    version's own frozen anchors. This is what "never rewrite history"
    means concretely: saving a new plan version tomorrow changes which
    version is effective for future dates, but never touches the
    (effective_date, starting_balance) pair a past version was anchored
    to, so a past day's target is reproducible forever.

    Missing-day policy (architecture review, point 6): a business day
    with no actual entry, sitting BEFORE the latest actual date, carries
    the real balance forward flat and is marked ungraded=True rather
    than assumed "on target". This needs to stay a documented default,
    not a silent one -- flag to the user if it doesn't match intent.

    The forecast segment (days after the latest actual) is re-anchored
    to (forecast_base_date, current_real_balance) and evaluated with a
    throwaway PlanVersion that reuses the CURRENT version's shape
    parameters but starts fresh at the real balance -- this is the
    "regenerate the remaining future mathematically" rule.
    """
    if not versions:
        raise ValueError("At least one plan version is required")
    versions_sorted = sorted(versions, key=lambda v: (v.effective_date, v.version_id))

    actuals_by_date = {a.entry_date: a for a in actuals}
    last_actual_date = max(actuals_by_date) if actuals_by_date else None

    current_version = effective_version_for(as_of, versions_sorted)
    calendar_end = max(current_version.end_date, as_of)
    calendar = business_day_calendar(settings.initial_date, calendar_end)

    real_balance = settings.initial_balance
    forecast_base_date = settings.initial_date
    forecast_base_balance = settings.initial_balance

    records = []
    for day in calendar:
        version = effective_version_for(day, versions_sorted)
        is_history = last_actual_date is not None and day <= last_actual_date
        actual = actuals_by_date.get(day)

        ungraded = False
        if is_history:
            if actual is not None:
                real_balance += actual.actual_pnl
                forecast_base_date = day
                forecast_base_balance = real_balance
            else:
                ungraded = True  # flat carry-forward, see docstring
            row_real_balance = real_balance
            actual_pnl = actual.actual_pnl if actual is not None else None
        else:
            row_real_balance = None
            actual_pnl = None

        records.append({
            "date": day,
            "plan_version_id": version.version_id,
            "target_balance": version.target_balance_at(day),
            "actual_pnl": actual_pnl,
            "real_balance": row_real_balance,
            "is_forecast": not is_history,
            "is_ungraded": ungraded,
        })

    df = pd.DataFrame.from_records(records).set_index("date")

    # Re-anchor the forecast segment to the latest real state, using the
    # CURRENT version's own peak/intensity but starting_balance = the
    # latest real balance and effective_date = forecast_base_date.
    forecast_mask = df.index > forecast_base_date
    if forecast_mask.any():
        remainder = PlanVersion(
            version_id=current_version.version_id,
            effective_date=forecast_base_date,
            starting_balance=forecast_base_balance,
            target_balance=current_version.target_balance,
            end_date=current_version.end_date,
            peak_position=current_version.peak_position,
            curve_intensity=current_version.curve_intensity,
            created_at=current_version.created_at,
        )
        for day in df.index[forecast_mask]:
            df.loc[day, "target_balance"] = remainder.target_balance_at(day)
            df.loc[day, "plan_version_id"] = current_version.version_id

    df["target_pnl"] = df["target_balance"].diff()
    df["target_return"] = df["target_balance"].pct_change()
    df = df.reset_index()

    return DailySeriesResult(
        daily=df,
        forecast_base_date=forecast_base_date,
        forecast_base_balance=forecast_base_balance,
        last_actual_date=last_actual_date,
    )


def build_monthly_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """Monthly rows are a pure reporting aggregate over the daily series
    -- never a separate calculation path (architecture review, CORE
    MATHEMATICAL ARCHITECTURE)."""
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["month"] = d["date"].dt.to_period("M")

    def summarize(g: pd.DataFrame) -> pd.Series:
        starting = g["target_balance"].iloc[0] - (g["target_pnl"].iloc[0] or 0.0)
        ending = g["target_balance"].iloc[-1]
        real_vals = g["real_balance"].dropna()
        has_actuals = g["actual_pnl"].notna().any()
        return pd.Series({
            "starting_target_balance": starting,
            "ending_target_balance": ending,
            "target_pnl": ending - starting,
            "target_return": (ending / starting - 1) if starting else np.nan,
            "real_pnl": g["actual_pnl"].sum(skipna=True) if has_actuals else np.nan,
            "real_ending_balance": real_vals.iloc[-1] if len(real_vals) else np.nan,
            "plan_version": g["plan_version_id"].iloc[-1],
        })

    monthly = d.groupby("month", group_keys=False).apply(summarize, include_groups=False)
    monthly["variance"] = monthly["real_ending_balance"] - monthly["ending_target_balance"]
    return monthly.reset_index()
