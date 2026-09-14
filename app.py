import streamlit as st

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

tab_infrastructure, tab_calendar = st.tabs(
    [
        "Infrastructure",
        "Phase 3.1 · Business Calendar",
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
