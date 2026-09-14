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
    """
    Creates and caches the authenticated Google Sheets client.
    """

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
    """
    Opens and caches the application's backend spreadsheet.
    """

    client = get_google_client()

    spreadsheet_id = st.secrets["SPREADSHEET_ID"]

    return client.open_by_key(spreadsheet_id)


def validate_schema():
    """
    Validates the Google Sheets structure against the expected schema.

    Does NOT modify anything.

    Returns a dictionary with validation information.
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

        # Completely empty worksheet
        if not actual_headers:

            results[sheet_name] = {
                "status": "EMPTY",
                "expected": expected_headers,
                "actual": [],
            }

            continue

        # Exact match
        if actual_headers == expected_headers:

            results[sheet_name] = {
                "status": "VALID",
                "expected": expected_headers,
                "actual": actual_headers,
            }

            continue

        # Something exists, but it is not our schema
        results[sheet_name] = {
            "status": "SCHEMA_MISMATCH",
            "expected": expected_headers,
            "actual": actual_headers,
        }

    return results


def initialize_schema():
    """
    Initializes headers ONLY in worksheets whose first row is empty.

    Important:
    This function will NEVER overwrite an existing mismatched schema.
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
                "status": "ERROR",
                "message": "Worksheet does not exist.",
            }

            continue

        worksheet = existing_sheets[sheet_name]

        actual_headers = worksheet.row_values(1)

        # If completely empty, initialize
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

        # Already correct
        if actual_headers == expected_headers:

            results[sheet_name] = {
                "status": "ALREADY_VALID",
            }

            continue

        # Never overwrite unknown/mismatched data
        results[sheet_name] = {
            "status": "BLOCKED",
            "message": (
                "Worksheet contains headers that do not match "
                "the expected schema. Nothing was overwritten."
            ),
        }

    return results
