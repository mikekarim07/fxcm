import uuid
from datetime import datetime, timezone

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

st.set_page_config(
    page_title="Capital Growth App - Connectivity Test",
    page_icon="🧪",
    layout="centered",
)

REQUIRED_WORKSHEETS = [
    "App_Config",
    "Plan_Versions",
    "Actual_Events",
    "Forecast_Revisions",
]

TEST_WORKSHEET = "_Connectivity_Test"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ---------------------------------------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------------------------------------

@st.cache_resource
def get_google_client():
    service_account_info = dict(
        st.secrets["google_service_account"]
    )

    # Makes the private key robust whether it contains
    # actual line breaks or escaped \n characters.
    service_account_info["private_key"] = (
        service_account_info["private_key"]
        .replace("\\n", "\n")
    )

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )

    return gspread.authorize(credentials)


@st.cache_resource
def get_spreadsheet():
    client = get_google_client()

    spreadsheet_id = st.secrets["app"]["spreadsheet_id"]

    return client.open_by_key(spreadsheet_id)


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------

st.title("🧪 Capital Growth App")
st.subheader("Google Sheets Connectivity Test")

st.caption(
    "Temporary smoke test for Streamlit Cloud → "
    "Secrets → Google Service Account → Google Sheets."
)


# ---------------------------------------------------------
# 1. CONNECTION TEST
# ---------------------------------------------------------

try:
    spreadsheet = get_spreadsheet()

    st.success(
        f"Connected successfully to Google Sheet: "
        f"**{spreadsheet.title}**"
    )

except Exception as exc:
    st.error("Could not connect to Google Sheets.")
    st.exception(exc)
    st.stop()


# ---------------------------------------------------------
# 2. SCHEMA / WORKSHEET TEST
# ---------------------------------------------------------

worksheet_names = [
    worksheet.title
    for worksheet in spreadsheet.worksheets()
]

missing_worksheets = [
    sheet
    for sheet in REQUIRED_WORKSHEETS
    if sheet not in worksheet_names
]

if missing_worksheets:
    st.error(
        "Missing required worksheets: "
        + ", ".join(missing_worksheets)
    )

else:
    st.success("All four required worksheets were found.")

    st.write(REQUIRED_WORKSHEETS)


# ---------------------------------------------------------
# 3. WRITE / READ / DELETE TEST
# ---------------------------------------------------------

st.divider()

st.subheader("Write test")

st.write(
    "This test creates a temporary worksheet, writes data, "
    "reads it back, verifies it, and deletes the worksheet."
)


if st.button(
    "Run write/read test",
    type="primary",
):

    test_worksheet = None

    try:

        # -------------------------------------------------
        # Remove leftover test tab from an interrupted test
        # -------------------------------------------------

        try:
            old_test_sheet = spreadsheet.worksheet(
                TEST_WORKSHEET
            )

            spreadsheet.del_worksheet(old_test_sheet)

        except gspread.WorksheetNotFound:
            pass


        # -------------------------------------------------
        # Create temporary worksheet
        # -------------------------------------------------

        test_worksheet = spreadsheet.add_worksheet(
            title=TEST_WORKSHEET,
            rows=10,
            cols=5,
        )


        # -------------------------------------------------
        # Test payload
        # -------------------------------------------------

        test_id = str(uuid.uuid4())

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()


        values = [
            ["field", "value"],
            ["test_id", test_id],
            ["timestamp_utc", timestamp],
            ["status", "WRITE_OK"],
        ]


        # -------------------------------------------------
        # WRITE
        # -------------------------------------------------

        test_worksheet.update(
            range_name="A1:B4",
            values=values,
            value_input_option="RAW",
        )


        # -------------------------------------------------
        # READ
        # -------------------------------------------------

        readback = test_worksheet.get("A1:B4")


        # -------------------------------------------------
        # VERIFY
        # -------------------------------------------------

        returned_test_id = readback[1][1]

        if returned_test_id != test_id:
            raise ValueError(
                "Read/write validation failed: "
                "test ID does not match."
            )


        # -------------------------------------------------
        # DELETE TEMP WORKSHEET
        # -------------------------------------------------

        spreadsheet.del_worksheet(
            test_worksheet
        )

        test_worksheet = None


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        st.success(
            "Full connectivity test passed successfully."
        )

        st.code(
            f"""
Connection: PASS
Secrets: PASS
Spreadsheet access: PASS
Required tabs: PASS
Write: PASS
Read: PASS
Validation: PASS
Delete: PASS

Test ID:
{test_id}
            """
        )


    except Exception as exc:

        st.error(
            "Connectivity test failed."
        )

        st.exception(exc)


        # Try to clean up the temporary worksheet
        if test_worksheet is not None:

            try:
                spreadsheet.del_worksheet(
                    test_worksheet
                )

            except Exception:
                st.warning(
                    "The temporary test worksheet "
                    "could not be deleted automatically."
                )
