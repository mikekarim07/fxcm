import streamlit as st
import plotly.graph_objects as go

from storage.sheets import (
    get_spreadsheet,
    initialize_schema,
    validate_schema,
)

from core.calendar import (
    BusinessCalendar,
    build_business_schedule,
)

from core.calendar_selftest import (
    run_calendar_self_tests,
)

from core.curve import (
    BetaGrowthCurve,
)

from core.curve_selftest import (
    run_curve_self_tests,
)

st.set_page_config(
    page_title="Capital Growth App",
    page_icon="📈",
    layout="wide",
)


st.title("📈 Capital Growth App")

st.caption(
    "Development Environment"
)


# =========================================================
# TABS
# =========================================================

(
    tab_infrastructure,
    tab_calendar,
    tab_curve,
) = st.tabs(
    [
        "Infrastructure",
        "Phase 3.1 · Business Calendar",
        "Phase 3.2 · Beta Curve",
    ]
)

# =========================================================
# TAB 1 — INFRASTRUCTURE
# =========================================================

with tab_infrastructure:

    st.header(
        "Infrastructure & Backend Schema"
    )

    # -----------------------------------------------------
    # GOOGLE SHEETS CONNECTION
    # -----------------------------------------------------

    try:

        spreadsheet = get_spreadsheet()

        st.success(
            f"Google Sheets connected: "
            f"**{spreadsheet.title}**"
        )

    except Exception as exc:

        st.error(
            "Google Sheets connection failed."
        )

        st.exception(exc)

        st.stop()

    # -----------------------------------------------------
    # SCHEMA VALIDATION
    # -----------------------------------------------------

    st.divider()

    st.subheader(
        "Backend Schema"
    )

    schema_results = validate_schema()

    all_valid = True

    for sheet_name, result in schema_results.items():

        status = result["status"]

        if status == "VALID":

            st.success(
                f"{sheet_name}: VALID"
            )

        elif status == "EMPTY":

            st.warning(
                f"{sheet_name}: EMPTY"
            )

            all_valid = False

        elif status == "MISSING_SHEET":

            st.error(
                f"{sheet_name}: MISSING"
            )

            all_valid = False

        elif status == "SCHEMA_MISMATCH":

            st.error(
                f"{sheet_name}: SCHEMA MISMATCH"
            )

            all_valid = False

            with st.expander(
                f"Show schema difference — "
                f"{sheet_name}"
            ):

                st.write(
                    "Expected:"
                )

                st.code(
                    " | ".join(
                        result["expected"]
                    )
                )

                st.write(
                    "Actual:"
                )

                st.code(
                    " | ".join(
                        result["actual"]
                    )
                )

    # -----------------------------------------------------
    # INITIALIZE SCHEMA
    # -----------------------------------------------------

    if not all_valid:

        st.divider()

        st.subheader(
            "Initialize Backend"
        )

        st.info(
            "Initialization writes headers only "
            "to empty worksheets. Existing data "
            "is never overwritten."
        )

        if st.button(
            "Initialize schema",
            type="primary",
        ):

            init_results = (
                initialize_schema()
            )

            for (
                sheet_name,
                result,
            ) in init_results.items():

                status = result[
                    "status"
                ]

                if (
                    status
                    == "INITIALIZED"
                ):

                    st.success(
                        f"{sheet_name}: "
                        f"initialized"
                    )

                elif (
                    status
                    == "ALREADY_VALID"
                ):

                    st.info(
                        f"{sheet_name}: "
                        f"already valid"
                    )

                else:

                    st.error(
                        f"{sheet_name}: "
                        f"{status}"
                    )

                    if (
                        "message"
                        in result
                    ):

                        st.write(
                            result[
                                "message"
                            ]
                        )

            st.cache_resource.clear()

            st.rerun()

    else:

        st.divider()

        st.success(
            "Backend schema is fully valid."
        )


# =========================================================
# TAB 2 — PHASE 3.1 CALENDAR
# =========================================================

with tab_calendar:

    st.header(
        "Phase 3.1 · Business Calendar Engine"
    )

    st.write(
        """
        This environment validates the operational
        calendar independently from the forecast,
        Beta curve, P&L engine and Google Sheets.
        """
    )

    # -----------------------------------------------------
    # AUTOMATED SELF TESTS
    # -----------------------------------------------------

    st.subheader(
        "Automated Tests"
    )

    if st.button(
        "Run Phase 3.1 tests",
        type="primary",
        key="run_calendar_tests",
    ):

        test_results = (
            run_calendar_self_tests()
        )

        passed = sum(
            result["status"] == "PASS"
            for result in test_results
        )

        failed = sum(
            result["status"] == "FAIL"
            for result in test_results
        )

        col1, col2, col3 = st.columns(
            3
        )

        col1.metric(
            "Tests",
            len(test_results),
        )

        col2.metric(
            "Passed",
            passed,
        )

        col3.metric(
            "Failed",
            failed,
        )

        if failed == 0:

            st.success(
                "Phase 3.1 test suite PASSED."
            )

        else:

            st.error(
                "Phase 3.1 contains failing tests."
            )

        for result in test_results:

            if result["status"] == "PASS":

                st.success(
                    f"PASS · {result['name']}"
                )

            else:

                st.error(
                    f"FAIL · {result['name']}"
                )

                st.code(
                    result["details"]
                )

    # -----------------------------------------------------
    # INTERACTIVE CALENDAR SANDBOX
    # -----------------------------------------------------

    st.divider()

    st.subheader(
        "Interactive Calendar Sandbox"
    )

    st.caption(
        "This does not save anything to Google Sheets."
    )

    col_start, col_end = st.columns(
        2
    )

    with col_start:

        start_date = st.date_input(
            "Plan start date",
            value="today",
            key="calendar_start",
        )

    with col_end:

        end_date = st.date_input(
            "Plan end date",
            value=None,
            key="calendar_end",
        )

    if end_date is None:

        st.info(
            "Select an end date to generate "
            "the operational schedule."
        )

    elif end_date < start_date:

        st.error(
            "End date cannot be before "
            "start date."
        )

    else:

        try:

            calendar = BusinessCalendar()

            schedule = (
                build_business_schedule(
                    calendar=calendar,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

            st.success(
                "Business schedule generated."
            )

            metric1, metric2, metric3 = (
                st.columns(3)
            )

            metric1.metric(
                "Business periods",
                schedule.periods,
            )

            metric2.metric(
                "First business day",
                schedule
                .first_business_date
                .strftime("%d-%b-%Y"),
            )

            metric3.metric(
                "Last business day",
                schedule
                .last_business_date
                .strftime("%d-%b-%Y"),
            )

            # ---------------------------------------------
            # Preview schedule
            # ---------------------------------------------

            preview_rows = []

            for index, business_day in enumerate(
                schedule.business_days,
                start=1,
            ):

                preview_rows.append({
                    "Period": index,
                    "Date": business_day,
                    "Business Position": (
                        index
                        / schedule.periods
                    ),
                })

            st.dataframe(
                preview_rows,
                use_container_width=True,
                hide_index=True,
            )

        except Exception as exc:

            st.error(
                "Could not build schedule."
            )

            st.exception(exc)

# =========================================================
# TAB 3 — PHASE 3.2 BETA CURVE
# =========================================================

with tab_curve:

    st.header(
        "Phase 3.2 · Continuous Beta Growth Curve"
    )

    st.write(
        """
        This sandbox validates the mathematical shape
        of the continuous growth curve before money,
        balances, P&L or actual results are introduced.
        """
    )

    st.info(
        "CDF = accumulated target progress. "
        "PDF = instantaneous growth velocity."
    )

    # =====================================================
    # AUTOMATED TESTS
    # =====================================================

    st.subheader(
        "Automated Mathematical Tests"
    )

    if st.button(
        "Run Phase 3.2 tests",
        type="primary",
        key="run_curve_tests",
    ):

        test_results = (
            run_curve_self_tests()
        )

        passed = sum(
            result["status"] == "PASS"
            for result in test_results
        )

        failed = sum(
            result["status"] == "FAIL"
            for result in test_results
        )

        col1, col2, col3 = st.columns(
            3
        )

        col1.metric(
            "Tests",
            len(test_results),
        )

        col2.metric(
            "Passed",
            passed,
        )

        col3.metric(
            "Failed",
            failed,
        )

        if failed == 0:

            st.success(
                "Phase 3.2 test suite PASSED."
            )

        else:

            st.error(
                "Phase 3.2 contains failing tests."
            )

        for result in test_results:

            if result["status"] == "PASS":

                st.success(
                    f"PASS · {result['name']}"
                )

            else:

                st.error(
                    f"FAIL · {result['name']}"
                )

                st.code(
                    result["details"]
                )

    # =====================================================
    # INTERACTIVE CURVE SANDBOX
    # =====================================================

    st.divider()

    st.subheader(
        "Interactive Curve Sandbox"
    )

    st.caption(
        "Nothing in this sandbox is saved to Google Sheets."
    )

    col_peak, col_intensity = (
        st.columns(2)
    )

    with col_peak:

        peak_position = st.slider(
            "Peak Position",
            min_value=0.05,
            max_value=0.95,
            value=0.55,
            step=0.01,
            format="%.2f",
            help=(
                "Approximate position in the plan "
                "where maximum growth velocity occurs."
            ),
        )

    with col_intensity:

        curve_intensity = st.slider(
            "Curve Intensity",
            min_value=0.0,
            max_value=30.0,
            value=8.0,
            step=0.5,
            format="%.1f",
            help=(
                "Controls how concentrated growth is "
                "around the Peak Position. "
                "Zero produces a linear curve."
            ),
        )

    curve = BetaGrowthCurve(
        peak_position=peak_position,
        curve_intensity=curve_intensity,
    )

    # =====================================================
    # CURVE PARAMETERS
    # =====================================================

    metric1, metric2, metric3 = (
        st.columns(3)
    )

    metric1.metric(
        "Alpha",
        f"{curve.alpha:.4f}",
    )

    metric2.metric(
        "Beta",
        f"{curve.beta:.4f}",
    )

    if curve.is_linear:

        peak_display = "No unique peak"

    else:

        peak_display = (
            f"{curve.theoretical_peak_position():.0%}"
        )

    metric3.metric(
        "Growth Peak",
        peak_display,
    )

    # =====================================================
    # SAMPLE CURVE
    # =====================================================

    samples = curve.sample(
        points=301
    )

    x_values = [
        row["x"]
        for row in samples
    ]

    cdf_values = [
        row["cdf"]
        for row in samples
    ]

    pdf_values = [
        row["pdf"]
        for row in samples
    ]

    # =====================================================
    # CDF CHART
    # =====================================================

    st.subheader(
        "Accumulated Growth — F(x)"
    )

    fig_cdf = go.Figure()

    fig_cdf.add_trace(
        go.Scatter(
            x=x_values,
            y=cdf_values,
            mode="lines",
            name="Beta CDF",
        )
    )

    fig_cdf.add_vline(
        x=peak_position,
        line_dash="dash",
        annotation_text="Peak Position",
        annotation_position="top",
    )

    fig_cdf.update_layout(
        xaxis_title="Business-Time Position",
        yaxis_title="Accumulated Progress",
        yaxis=dict(
            range=[0, 1]
        ),
        hovermode="x unified",
    )

    st.plotly_chart(
        fig_cdf,
        use_container_width=True,
    )

    # =====================================================
    # PDF CHART
    # =====================================================

    st.subheader(
        "Growth Velocity — F'(x)"
    )

    fig_pdf = go.Figure()

    fig_pdf.add_trace(
        go.Scatter(
            x=x_values,
            y=pdf_values,
            mode="lines",
            name="Beta PDF",
        )
    )

    fig_pdf.add_vline(
        x=peak_position,
        line_dash="dash",
        annotation_text="Maximum growth",
        annotation_position="top",
    )

    fig_pdf.update_layout(
        xaxis_title="Business-Time Position",
        yaxis_title="Relative Growth Velocity",
        hovermode="x unified",
    )

    st.plotly_chart(
        fig_pdf,
        use_container_width=True,
    )

    # =====================================================
    # CHECKPOINT TABLE
    # =====================================================

    st.subheader(
        "Curve Checkpoints"
    )

    checkpoint_positions = sorted(
        set(
            [
                0.00,
                0.10,
                0.25,
                0.50,
                peak_position,
                0.75,
                0.90,
                1.00,
            ]
        )
    )

    checkpoint_rows = []

    for x in checkpoint_positions:

        checkpoint_rows.append({
            "Position": x,
            "Plan %": f"{x:.1%}",
            "Accumulated Progress": (
                curve.cdf(x)
            ),
            "Accumulated %": (
                f"{curve.cdf(x):.2%}"
            ),
            "Growth Velocity": (
                curve.pdf(x)
            ),
        })

    st.dataframe(
        checkpoint_rows,
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # INTERPRETATION
    # =====================================================

    st.divider()

    if curve.is_linear:

        st.info(
            "Intensity = 0. The model is currently linear: "
            "50% of business time corresponds to exactly "
            "50% of accumulated target progress."
        )

    else:

        progress_at_peak = curve.cdf(
            peak_position
        )

        st.write(
            f"""
            **Interpretation**

            Maximum growth velocity occurs at approximately
            **{peak_position:.0%} of the operational horizon**.

            At that point, the model has already completed
            approximately **{progress_at_peak:.2%} of total
            accumulated growth**.
            """
        )

ad
