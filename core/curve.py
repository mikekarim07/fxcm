from __future__ import annotations

from dataclasses import dataclass
import math

from scipy.stats import beta as beta_distribution


class CurveError(ValueError):
    """Raised when curve parameters or positions are invalid."""


@dataclass(frozen=True)
class BetaGrowthCurve:
    """
    Continuous normalized growth curve based on a Beta CDF.

    Parameters
    ----------
    peak_position:
        Desired position of maximum growth velocity.
        Valid range: 0 <= peak_position <= 1.

    curve_intensity:
        Controls how concentrated the growth is around the peak.

        0 -> linear curve
        larger values -> stronger S-shape / concentration

    Mathematical definition
    -----------------------
    alpha = 1 + peak_position * curve_intensity

    beta = 1 + (1 - peak_position) * curve_intensity

    F(x) = BetaCDF(x, alpha, beta)

    For intensity > 0, the mode of the Beta PDF is:

        (alpha - 1) / (alpha + beta - 2)

    which simplifies exactly to:

        peak_position
    """

    peak_position: float
    curve_intensity: float

    def __post_init__(self):

        try:
            peak = float(
                self.peak_position
            )

            intensity = float(
                self.curve_intensity
            )

        except (TypeError, ValueError) as exc:

            raise CurveError(
                "Curve parameters must be numeric."
            ) from exc

        if not math.isfinite(peak):

            raise CurveError(
                "peak_position must be finite."
            )

        if not math.isfinite(intensity):

            raise CurveError(
                "curve_intensity must be finite."
            )

        if peak < 0 or peak > 1:

            raise CurveError(
                "peak_position must be between 0 and 1."
            )

        if intensity < 0:

            raise CurveError(
                "curve_intensity cannot be negative."
            )

    @property
    def alpha(self) -> float:

        return (
            1.0
            + float(self.peak_position)
            * float(self.curve_intensity)
        )

    @property
    def beta(self) -> float:

        return (
            1.0
            + (
                1.0
                - float(self.peak_position)
            )
            * float(self.curve_intensity)
        )

    @property
    def is_linear(self) -> bool:

        return (
            float(self.curve_intensity)
            == 0.0
        )

    def _validate_position(
        self,
        x: float,
    ) -> float:

        try:

            x = float(x)

        except (TypeError, ValueError) as exc:

            raise CurveError(
                "Curve position x must be numeric."
            ) from exc

        if not math.isfinite(x):

            raise CurveError(
                "Curve position x must be finite."
            )

        if x < 0 or x > 1:

            raise CurveError(
                "Curve position x must be between 0 and 1."
            )

        return x

    def cdf(
        self,
        x: float,
    ) -> float:
        """
        Returns normalized accumulated curve progress F(x).

        Output is always between 0 and 1.
        """

        x = self._validate_position(x)

        if self.is_linear:

            return x

        value = beta_distribution.cdf(
            x,
            self.alpha,
            self.beta,
        )

        return float(value)

    def pdf(
        self,
        x: float,
    ) -> float:
        """
        Returns instantaneous growth velocity.

        This is the derivative of the CDF.
        """

        x = self._validate_position(x)

        if self.is_linear:

            return 1.0

        value = beta_distribution.pdf(
            x,
            self.alpha,
            self.beta,
        )

        return float(value)

    def theoretical_peak_position(
        self,
    ) -> float | None:
        """
        Returns the theoretical location of maximum growth velocity.

        For intensity = 0 the curve is linear and therefore
        every point has the same growth rate. There is no
        unique peak.
        """

        if self.is_linear:

            return None

        return float(
            self.peak_position
        )

    def sample(
        self,
        points: int = 201,
    ) -> list[dict]:
        """
        Samples the curve across the interval [0, 1].

        Useful for charts and diagnostics.
        """

        if points < 2:

            raise CurveError(
                "sample points must be at least 2."
            )

        rows = []

        for i in range(points):

            x = i / (points - 1)

            rows.append({
                "x": x,
                "cdf": self.cdf(x),
                "pdf": self.pdf(x),
            })

        return rows
