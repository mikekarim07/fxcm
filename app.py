import streamlit as st

from storage.sheets import (
    get_spreadsheet,
    initialize_schema,
    validate_schema,
)


st.set_page_config(
    page_title="Capital Growth App",
    page_icon="📈",
    layout="centered",
)


st.title("📈 Capital Growth App")

st.caption("Infrastructure & Schema Setup")


# ---------------------------------------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------------------------------------

try:

    spreadsheet = get_spreadsheet()

    st.success(
        f"Google Sheets connected: **{spreadsheet.title}**"
    )

except Exception as exc:

    st.error("Google Sheets connection failed.")

    st.exception(exc)

    st.stop()


# ---------------------------------------------------------
# SCHEMA VALIDATION
# ---------------------------------------------------------

st.divider()

st.subheader("Backend Schema")

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
            f"Show schema difference — {sheet_name}"
        ):

            st.write("Expected:")

            st.code(
                " | ".join(result["expected"])
            )

            st.write("Actual:")

            st.code(
                " | ".join(result["actual"])
            )


# ---------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------

if not all_valid:

    st.divider()

    st.subheader("Initialize Backend")

    st.info(
        "Initialization writes headers only to empty worksheets. "
        "Existing mismatched data will never be overwritten."
    )

    if st.button(
        "Initialize schema",
        type="primary",
    ):

        init_results = initialize_schema()

        for sheet_name, result in init_results.items():

            status = result["status"]

            if status == "INITIALIZED":

                st.success(
                    f"{sheet_name}: initialized"
                )

            elif status == "ALREADY_VALID":

                st.info(
                    f"{sheet_name}: already valid"
                )

            else:

                st.error(
                    f"{sheet_name}: {status}"
                )

                if "message" in result:

                    st.write(
                        result["message"]
                    )

        st.cache_resource.clear()

        st.rerun()


# ---------------------------------------------------------
# READY
# ---------------------------------------------------------

else:

    st.divider()

    st.success(
        "Backend schema is fully valid."
    )

    st.code(
        """
Google Sheets connection: PASS
Service Account: PASS
Secrets: PASS

App_Config: PASS
Plan_Versions: PASS
Actual_Events: PASS
Forecast_Revisions: PASS

Backend Status: READY
        """
    )
