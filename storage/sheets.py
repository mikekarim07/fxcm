import json

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from storage.schema import SHEET_SCHEMAS


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_google_client():

    credentials_dict = json.loads(
        st.secrets["GOOGLE_CREDENTIALS"]
    )

    credentials = Credentials.from_service_account_info(
        credentials_dict,
        scopes=SCOPES,
    )

    return gspread.authorize(credentials)


@st.cache_resource
def get_spreadsheet():

    client = get_google_client()

    spreadsheet_id = st.secrets["SPREADSHEET_ID"]

    return client.open_by_key(spreadsheet_id)


@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def validate_schema():
    """
    Validate Google Sheets structure.

    Cached for 5 minutes so Streamlit widget reruns
    do not repeatedly hit the Sheets API.
    """

    spreadsheet = get_spreadsheet()

    existing_sheets = {
        worksheet.title: worksheet
        for worksheet in spreadsheet.worksheets()
    }

    results = {}

    for sheet_name, expected_headers in SHEET_SCHEMAS.items():

        if sheet_name not in existing_sheets:

            results[sheet_name] = {
                "status": "MISSING_SHEET",
                "expected": expected_headers,
                "actual": [],
            }

            continue

        worksheet = existing_sheets[sheet_name]

        actual_headers = worksheet.row_values(1)

        if not actual_headers:

            results[sheet_name] = {
                "status": "EMPTY",
                "expected": expected_headers,
                "actual": [],
            }

            continue

        if actual_headers == expected_headers:

            results[sheet_name] = {
                "status": "VALID",
                "expected": expected_headers,
                "actual": actual_headers,
            }

            continue

        results[sheet_name] = {
            "status": "SCHEMA_MISMATCH",
            "expected": expected_headers,
            "actual": actual_headers,
        }

    return results


def initialize_schema():

    spreadsheet = get_spreadsheet()

    existing_sheets = {
        worksheet.title: worksheet
        for worksheet in spreadsheet.worksheets()
    }

    results = {}

    for sheet_name, expected_headers in SHEET_SCHEMAS.items():

        if sheet_name not in existing_sheets:

            results[sheet_name] = {
                "status": "ERROR",
                "message": "Worksheet does not exist.",
            }

            continue

        worksheet = existing_sheets[sheet_name]

        actual_headers = worksheet.row_values(1)

        if not actual_headers:

            worksheet.update(
                range_name="A1",
                values=[expected_headers],
                value_input_option="RAW",
            )

            results[sheet_name] = {
                "status": "INITIALIZED",
            }

            continue

        if actual_headers == expected_headers:

            results[sheet_name] = {
                "status": "ALREADY_VALID",
            }

            continue

        results[sheet_name] = {
            "status": "BLOCKED",
            "message": (
                "Worksheet contains headers that do not match "
                "the expected schema."
            ),
        }

    # Important: refresh cached validation after writes
    validate_schema.clear()

    return results
