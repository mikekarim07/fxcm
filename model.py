"""
Domain model for the capital-growth / P&L planner.

Three entities, and only three, are ever persisted (to Google Sheets or
wherever). Everything else -- daily targets, monthly summaries, KPIs -- is
a pure function of these, recomputed on every read (see core/forecast.py).
That is the central architectural decision from the review: no derived
row is ever written back to storage, which is what makes "never rewrite
history" and "safe under concurrent writes" true by construction rather
than by discipline.

    Settings      -- immutable, set once at plan inception
    PlanVersion   -- immutable, append-only (a new row per change)
    ActualEntry   -- mutable, but edits should be audit-logged by the caller
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from scipy.stats import beta as beta_dist

# App-wide default curve shape, locked in after the interactive review:
# a symmetric S-curve peaking at the midpoint of the horizon.
DEFAULT_PEAK_POSITION = 0.5
DEFAULT_CURVE_INTENSITY = 9.0


@dataclass(frozen=True)
class Settings:
    """Plan-wide constants. Effectively immutable after the plan formally
    starts (see architecture review, SETTINGS section)."""

    initial_balance: float
    initial_date: date

    def __post_init__(self) -> None:
        if self.initial_balance < 0:
            raise ValueError("initial_balance cannot be negative")


@dataclass(frozen=True)
class PlanVersion:
    """
    One immutable snapshot of the growth plan.

    `Plan_Versions` is append-only: a new PlanVersion row is created every
    time the user changes final target, end date, peak position, or curve
    intensity. Existing rows are NEVER updated. That immutability is what
    lets a historical target be recomputed on demand -- from the version
    that was effective on that date -- instead of stored, without any risk
    of a later change silently rewriting it.

    Time is normalized on CALENDAR days between effective_date and
    end_date (not business-day count) -- see architecture review, point 3,
    for why: business-day normalization would make "Peak Position = 0.5"
    drift relative to the real calendar depending on how holidays/weekends
    fall, and would understate the compounding implied by a long weekend.
    """

    version_id: int
    effective_date: date
    starting_balance: float
    target_balance: float
    end_date: date
    peak_position: float = DEFAULT_PEAK_POSITION
    curve_intensity: float = DEFAULT_CURVE_INTENSITY
    created_at: date = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not (0.0 < self.peak_position < 1.0):
            raise ValueError("peak_position must be strictly between 0 and 1")
        if self.curve_intensity < 0:
            raise ValueError("curve_intensity must be >= 0")
        if self.end_date <= self.effective_date:
            raise ValueError("end_date must be after effective_date")
        if self.created_at is None:
            object.__setattr__(self, "created_at", self.effective_date)

    @property
    def alpha(self) -> float:
        return 1.0 + self.peak_position * self.curve_intensity

    @property
    def beta(self) -> float:
        return 1.0 + (1.0 - self.peak_position) * self.curve_intensity

    def _x(self, on_date: date) -> float:
        """Normalized calendar-day position in [0, 1], clamped."""
        total_days = (self.end_date - self.effective_date).days
        if total_days <= 0:
            return 1.0
        elapsed = (on_date - self.effective_date).days
        return min(max(elapsed / total_days, 0.0), 1.0)

    def fraction_complete(self, on_date: date) -> float:
        """F(x): the fraction of (target - starting) that should be
        achieved by on_date, per this version's own curve."""
        x = self._x(on_date)
        if self.curve_intensity == 0:
            # Beta(1, 1) is uniform, i.e. F(x) == x exactly. Handled
            # explicitly rather than relying on scipy's Beta(1,1) path,
            # since intensity == 0 is a documented, deliberate "linear
            # ramp" mode (see architecture review, point 1-2).
            return x
        return float(beta_dist.cdf(x, self.alpha, self.beta))

    def target_balance_at(self, on_date: date) -> float:
        """Evaluate this version's own curve at on_date. Beyond end_date
        the curve saturates at target_balance rather than extrapolating."""
        f = self.fraction_complete(on_date)
        return self.starting_balance + (self.target_balance - self.starting_balance) * f


@dataclass
class ActualEntry:
    """A single day's reported actual P&L (net total, no trade-level
    detail -- see architecture review, ENTRY FORM). Mutable: editing an
    existing entry is allowed, but every edit should be appended to a
    separate Actuals_Audit_Log by the caller, not tracked here."""

    entry_date: date
    actual_pnl: float
    created_at: date
    updated_at: date
