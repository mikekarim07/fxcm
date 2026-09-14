from core.curve import (
    BetaGrowthCurve,
    CurveError,
)


TOLERANCE = 1e-9


def _approx_equal(
    a,
    b,
    tolerance=TOLERANCE,
):

    return abs(a - b) <= tolerance


def run_curve_self_tests():
    """
    Runs mathematical tests for the Beta Growth Curve.

    Returns list of test result dictionaries.
    """

    results = []

    def run_test(
        name,
        test_function,
    ):

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

    # =====================================================
    # TEST 1
    # Endpoints
    # =====================================================

    def test_endpoints():

        curve = BetaGrowthCurve(
            peak_position=0.55,
            curve_intensity=8,
        )

        assert _approx_equal(
            curve.cdf(0),
            0,
        )

        assert _approx_equal(
            curve.cdf(1),
            1,
        )

    run_test(
        "CDF endpoints are exactly 0 and 1",
        test_endpoints,
    )

    # =====================================================
    # TEST 2
    # Alpha / Beta calculation
    # =====================================================

    def test_parameters():

        curve = BetaGrowthCurve(
            peak_position=0.55,
            curve_intensity=8,
        )

        assert _approx_equal(
            curve.alpha,
            5.4,
        )

        assert _approx_equal(
            curve.beta,
            4.6,
        )

    run_test(
        "Alpha and Beta are calculated correctly",
        test_parameters,
    )

    # =====================================================
    # TEST 3
    # Peak formula
    # =====================================================

    def test_peak_formula():

        curve = BetaGrowthCurve(
            peak_position=0.55,
            curve_intensity=8,
        )

        calculated_mode = (
            (curve.alpha - 1)
            /
            (
                curve.alpha
                + curve.beta
                - 2
            )
        )

        assert _approx_equal(
            calculated_mode,
            0.55,
        )

    run_test(
        "Beta PDF mode equals Peak Position",
        test_peak_formula,
    )

    # =====================================================
    # TEST 4
    # PDF actually peaks there
    # =====================================================

    def test_pdf_peak():

        curve = BetaGrowthCurve(
            peak_position=0.55,
            curve_intensity=8,
        )

        peak_density = curve.pdf(
            0.55
        )

        left_density = curve.pdf(
            0.50
        )

        right_density = curve.pdf(
            0.60
        )

        assert (
            peak_density
            > left_density
        )

        assert (
            peak_density
            > right_density
        )

    run_test(
        "Maximum growth velocity occurs near Peak Position",
        test_pdf_peak,
    )

    # =====================================================
    # TEST 5
    # Monotonicity
    # =====================================================

    def test_monotonicity():

        curve = BetaGrowthCurve(
            peak_position=0.55,
            curve_intensity=8,
        )

        values = [
            curve.cdf(
                i / 1000
            )
            for i in range(1001)
        ]

        for previous, current in zip(
            values,
            values[1:],
        ):

            assert (
                current
                >= previous
            )

    run_test(
        "CDF is monotonically increasing",
        test_monotonicity,
    )

    # =====================================================
    # TEST 6
    # Linear mode
    # =====================================================

    def test_linear_intensity_zero():

        curve = BetaGrowthCurve(
            peak_position=0.80,
            curve_intensity=0,
        )

        assert _approx_equal(
            curve.cdf(0.25),
            0.25,
        )

        assert _approx_equal(
            curve.cdf(0.50),
            0.50,
        )

        assert _approx_equal(
            curve.cdf(0.75),
            0.75,
        )

        assert _approx_equal(
            curve.pdf(0.25),
            1.0,
        )

        assert (
            curve
            .theoretical_peak_position()
            is None
        )

    run_test(
        "Intensity 0 produces a linear curve",
        test_linear_intensity_zero,
    )

    # =====================================================
    # TEST 7
    # Symmetric curve
    # =====================================================

    def test_symmetric_curve():

        curve = BetaGrowthCurve(
            peak_position=0.50,
            curve_intensity=8,
        )

        assert _approx_equal(
            curve.alpha,
            curve.beta,
        )

        assert _approx_equal(
            curve.cdf(0.50),
            0.50,
        )

    run_test(
        "Peak 50% produces symmetric curve",
        test_symmetric_curve,
    )

    # =====================================================
    # TEST 8
    # Earlier peak
    # =====================================================

    def test_early_peak():

        curve = BetaGrowthCurve(
            peak_position=0.30,
            curve_intensity=8,
        )

        mode = (
            (curve.alpha - 1)
            /
            (
                curve.alpha
                + curve.beta
                - 2
            )
        )

        assert _approx_equal(
            mode,
            0.30,
        )

    run_test(
        "Early Peak Position moves maximum growth earlier",
        test_early_peak,
    )

    # =====================================================
    # TEST 9
    # Later peak
    # =====================================================

    def test_late_peak():

        curve = BetaGrowthCurve(
            peak_position=0.75,
            curve_intensity=8,
        )

        mode = (
            (curve.alpha - 1)
            /
            (
                curve.alpha
                + curve.beta
                - 2
            )
        )

        assert _approx_equal(
            mode,
            0.75,
        )

    run_test(
        "Late Peak Position moves maximum growth later",
        test_late_peak,
    )

    # =====================================================
    # TEST 10
    # Intensity concentration
    # =====================================================

    def test_intensity():

        soft = BetaGrowthCurve(
            peak_position=0.50,
            curve_intensity=2,
        )

        strong = BetaGrowthCurve(
            peak_position=0.50,
            curve_intensity=20,
        )

        assert (
            strong.pdf(0.50)
            > soft.pdf(0.50)
        )

    run_test(
        "Higher intensity concentrates growth around peak",
        test_intensity,
    )

    # =====================================================
    # TEST 11
    # Invalid Peak
    # =====================================================

    def test_invalid_peak():

        error_raised = False

        try:

            BetaGrowthCurve(
                peak_position=1.20,
                curve_intensity=8,
            )

        except CurveError:

            error_raised = True

        assert error_raised

    run_test(
        "Peak outside [0,1] is rejected",
        test_invalid_peak,
    )

    # =====================================================
    # TEST 12
    # Negative intensity
    # =====================================================

    def test_negative_intensity():

        error_raised = False

        try:

            BetaGrowthCurve(
                peak_position=0.50,
                curve_intensity=-1,
            )

        except CurveError:

            error_raised = True

        assert error_raised

    run_test(
        "Negative intensity is rejected",
        test_negative_intensity,
    )

    # =====================================================
    # TEST 13
    # Invalid x
    # =====================================================

    def test_invalid_position():

        curve = BetaGrowthCurve(
            peak_position=0.50,
            curve_intensity=8,
        )

        error_raised = False

        try:

            curve.cdf(
                1.01
            )

        except CurveError:

            error_raised = True

        assert error_raised

    run_test(
        "Curve position outside [0,1] is rejected",
        test_invalid_position,
    )

    # =====================================================
    # TEST 14
    # Sampling
    # =====================================================

    def test_sampling():

        curve = BetaGrowthCurve(
            peak_position=0.55,
            curve_intensity=8,
        )

        sample = curve.sample(
            points=101
        )

        assert len(sample) == 101

        assert _approx_equal(
            sample[0]["x"],
            0,
        )

        assert _approx_equal(
            sample[-1]["x"],
            1,
        )

        assert _approx_equal(
            sample[0]["cdf"],
            0,
        )

        assert _approx_equal(
            sample[-1]["cdf"],
            1,
        )

    run_test(
        "Curve sampling spans complete interval",
        test_sampling,
    )

    return results
