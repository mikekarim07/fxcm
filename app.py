import json

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


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
