import os
import requests
import gspread
import time
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ------------------ RETRY DECORATORS FOR GSPREAD ------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry_if_exception_type(APIError),
    reraise=True
)
def get_worksheet_with_retry(client, file_name, tab_name):
    print(f"Connecting to sheet '{file_name}' / tab '{tab_name}'...")
    return client.open(file_name).worksheet(tab_name)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry_if_exception_type(APIError),
    reraise=True
)
def fetch_all_values_with_retry(sheet):
    return sheet.get_all_values()

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry_if_exception_type(APIError),
    reraise=True
)
def batch_update_with_retry(sheet, data_cells):
    return sheet.update_cells(data_cells)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry_if_exception_type(APIError),
    reraise=True
)
def append_rows_with_retry(sheet, rows_data):
    return sheet.append_rows(rows_data)

# 1. Google Sheets Setup
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_json = os.environ.get("GOOGLE_CREDENTIALS")
if creds_json:
    import json
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
else:
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)

client = gspread.authorize(creds)

FILE_NAME = "PL Predictions"
TAB_NAME = "Fixtures Tab"

sheet = get_worksheet_with_retry(client, FILE_NAME, TAB_NAME)

# 2. Football API Setup
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "b4d7bcc9be7147d78e53c7f11c9ec283")
headers = {"X-Auth-Token": API_KEY}

print("Fetching current matchday from Football API...")

comp_url = "https://api.football-data.org/v4/competitions/PL"
comp_res = requests.get(comp_url, headers=headers).json()

current_matchday = comp_res.get("currentSeason", {}).get("currentMatchday")

if not current_matchday:
    print("Could not determine current matchday.")
    exit()

print(f"Current Gameweek/Matchday: {current_matchday}")

matchdays_to_fetch = [current_matchday, current_matchday + 1]

matches = []
for md in matchdays_to_fetch:
    print(f"Fetching matches for Matchday {md}...")
    matches_url = f"https://api.football-data.org/v4/competitions/PL/matches?matchday={md}"
    matches_res = requests.get(matches_url, headers=headers).json()
    fetched = matches_res.get("matches", [])
    matches.extend(fetched)

if not matches:
    print("No matches found for the requested matchdays.")
    exit()

# 3. Process Sheet Rows (In-Memory Batching)
all_rows = fetch_all_values_with_retry(sheet)

existing_fixtures = {}
for i, row in enumerate(all_rows[1:], start=2):
    if len(row) >= 3:
        key = f"{row[1].strip().lower()} vs {row[2].strip().lower()}"
        existing_fixtures[key] = i

cells_to_update = []
new_rows_to_add = []
updates_count = 0

for m in matches:
    match_id = str(m["id"])
    home_team = m["homeTeam"]["name"]
    away_team = m["awayTeam"]["name"]
    raw_kickoff = m.get("utcDate", "")
    status = m.get("status", "SCHEDULED")
    
    matchday_num = m.get("matchday", current_matchday)
    gameweek = f"GW{matchday_num}"
    
    formatted_kickoff = ""
    deadline_str = ""
    
    if raw_kickoff:
        try:
            dt = datetime.fromisoformat(raw_kickoff.replace("Z", "+00:00"))
            formatted_kickoff = dt.strftime("%d %b %Y, %H:%M")
            deadline_dt = dt - timedelta(hours=1)
            deadline_str = deadline_dt.strftime("%d %b %Y, %H:%M")
        except ValueError:
            formatted_kickoff = raw_kickoff
            deadline_str = raw_kickoff

    home_score = ""
    away_score = ""
    if status == "FINISHED":
        home_score = m["score"]["fullTime"]["home"]
        away_score = m["score"]["fullTime"]["away"]

    fixture_key = f"{home_team.strip().lower()} vs {away_team.strip().lower()}"

    if fixture_key in existing_fixtures:
        row_num = existing_fixtures[fixture_key]
        row_data = all_rows[row_num - 1]
        
        current_home_val = row_data[6] if len(row_data) >= 7 else ""
        
        # Batch collect kickoff and deadline updates
        if formatted_kickoff and (len(row_data) < 5 or row_data[4] != formatted_kickoff):
            cells_to_update.append(gspread.Cell(row_num, 5, formatted_kickoff))
        if deadline_str and (len(row_data) < 6 or row_data[5] != deadline_str):
            cells_to_update.append(gspread.Cell(row_num, 6, deadline_str))
        
        # Batch collect finished scores & status updates
        if status == "FINISHED" and (current_home_val is None or current_home_val == ""):
            cells_to_update.append(gspread.Cell(row_num, 7, home_score))
            cells_to_update.append(gspread.Cell(row_num, 8, away_score))
            cells_to_update.append(gspread.Cell(row_num, 9, status))
            print(f"Queued score update: {home_team} {home_score} - {away_score} {away_team}")
            updates_count += 1
    else:
        new_rows_to_add.append([match_id, home_team, away_team, gameweek, formatted_kickoff, deadline_str, home_score, away_score, status])

# 4. Execute Batch Requests
if cells_to_update:
    print(f"Pushed {len(cells_to_update)} cell updates in 1 batch request...")
    batch_update_with_retry(sheet, cells_to_update)

if new_rows_to_add:
    print(f"Appending {len(new_rows_to_add)} new fixture rows in 1 batch request...")
    append_rows_with_retry(sheet, new_rows_to_add)

print(f"Finished. Total score updates made: {updates_count}")
