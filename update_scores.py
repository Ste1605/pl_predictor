import os
import requests
import gspread
import time
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ------------------ RETRY DECORATORS FOR GSPREAD ------------------
# Automatically retries Google API calls up to 5 times if 503/500/429 errors occur
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
def update_cell_with_retry(sheet, row, col, value):
    return sheet.update_cell(row, col, value)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry_if_exception_type(APIError),
    reraise=True
)
def append_row_with_retry(sheet, row_data):
    return sheet.append_row(row_data)

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

# Exact File & Tab names matching your workbook
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

# Fetch both Current Gameweek and Next Gameweek to populate upcoming fixtures ahead of time
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

# 3. Process Sheet Rows
all_rows = fetch_all_values_with_retry(sheet)

# Existing fixtures map (Home Team in Col 2, Away Team in Col 3)
existing_fixtures = {}
for i, row in enumerate(all_rows[1:], start=2):  # skip headers
    if len(row) >= 3:
        key = f"{row[1].strip().lower()} vs {row[2].strip().lower()}"
        existing_fixtures[key] = i

new_rows_to_add = []
updates_count = 0

for m in matches:
    match_id = str(m["id"])
    home_team = m["homeTeam"]["name"]
    away_team = m["awayTeam"]["name"]
    raw_kickoff = m.get("utcDate", "")
    status = m.get("status", "SCHEDULED")
    
    # Use the matchday from each fixture object (e.g. GW2 or GW3)
    matchday_num = m.get("matchday", current_matchday)
    gameweek = f"GW{matchday_num}"
    
    # Format Kickoff and Deadline to readable format (e.g., "28 Aug 2026, 19:00")
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
        
        # Always update formatted Kickoff and Deadline if present
        if formatted_kickoff:
            update_cell_with_retry(sheet, row_num, 5, formatted_kickoff)
        if deadline_str:
            update_cell_with_retry(sheet, row_num, 6, deadline_str)
        
        # Update finished match scores & status
        if status == "FINISHED" and (current_home_val is None or current_home_val == ""):
            update_cell_with_retry(sheet, row_num, 7, home_score)  # Actual Home Score (Col 7)
            update_cell_with_retry(sheet, row_num, 8, away_score)  # Actual Away Score (Col 8)
            update_cell_with_retry(sheet, row_num, 9, status)      # Status (Col 9)
            print(f"Updated score: {home_team} {home_score} - {away_score} {away_team}")
            updates_count += 1
    else:
        # Match ID, Home Team, Away Team, GameWeek, Kickoff Time, Deadline, Actual Home Score, Actual Away Score, Status
        new_rows_to_add.append([match_id, home_team, away_team, gameweek, formatted_kickoff, deadline_str, home_score, away_score, status])

if new_rows_to_add:
    for new_row in new_rows_to_add:
        append_row_with_retry(sheet, new_row)
    print(f"Added {len(new_rows_to_add)} missing fixtures to '{TAB_NAME}'.")
else:
    print(f"All fixtures for requested matchdays processed in '{TAB_NAME}'.")

print(f"Finished. Total score updates made: {updates_count}")
