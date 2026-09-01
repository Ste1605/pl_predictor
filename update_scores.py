import os
import requests
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ------------------ RETRY DECORATORS ------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry_if_exception_type(APIError),
    reraise=True
)
def get_worksheet_with_retry(client, file_name, tab_name):
    return client.open(file_name).worksheet(tab_name)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry_if_exception_type(APIError),
    reraise=True
)
def fetch_all_values_with_retry(sheet):
    return sheet.get_all_values()

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry_if_exception_type(APIError),
    reraise=True
)
def bulk_write_with_retry(sheet, range_name, values):
    return sheet.update(range_name=range_name, values=values)

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

print(f"Current Matchday: {current_matchday}")

matchdays_to_fetch = [current_matchday, current_matchday + 1]
matches = []
for md in matchdays_to_fetch:
    print(f"Fetching matches for Matchday {md}...")
    matches_url = f"https://api.football-data.org/v4/competitions/PL/matches?matchday={md}"
    matches_res = requests.get(matches_url, headers=headers).json()
    matches.extend(matches_res.get("matches", []))

if not matches:
    print("No matches found.")
    exit()

# 3. Process Sheet Rows in Memory
all_rows = fetch_all_values_with_retry(sheet)
headers_row = all_rows[0] if all_rows else []
data_rows = all_rows[1:] if len(all_rows) > 1 else []

existing_fixtures = {}
for i, row in enumerate(data_rows):
    if len(row) >= 3:
        key = f"{row[1].strip().lower()} vs {row[2].strip().lower()}"
        existing_fixtures[key] = i

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
        home_score = str(m["score"]["fullTime"]["home"])
        away_score = str(m["score"]["fullTime"]["away"])

    fixture_key = f"{home_team.strip().lower()} vs {away_team.strip().lower()}"

    if fixture_key in existing_fixtures:
        idx = existing_fixtures[fixture_key]
        row = data_rows[idx]
        
        # Ensure row has enough columns
        while len(row) < 9:
            row.append("")
            
        row[3] = gameweek
        if formatted_kickoff: row[4] = formatted_kickoff
        if deadline_str: row[5] = deadline_str
        
        if status == "FINISHED" and (row[6] == "" or row[6] is None):
            row[6] = home_score
            row[7] = away_score
            row[8] = status
            updates_count += 1
        elif status != "FINISHED":
            row[8] = status
    else:
        new_row = [match_id, home_team, away_team, gameweek, formatted_kickoff, deadline_str, home_score, away_score, status]
        data_rows.append(new_row)

# 4. Write back EVERYTHING in 1 Single API Call
all_combined = [headers_row] + data_rows
bulk_write_with_retry(sheet, "A1", all_combined)

print(f"Finished successfully! Total finished matches updated: {updates_count}")
