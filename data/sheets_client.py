import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_client():
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=SCOPES
    )
    return gspread.authorize(creds)

def get_sheet(sheet_name):
    client = get_client()
    return client.open(sheet_name)

