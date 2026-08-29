import os
import requests
import gspread
from google.oauth2.service_account import Credentials

# 1. Google Sheets Setup
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Pull credentials from environment variable or local file
creds_json = os.environ.get("GOOGLE_CREDENTIALS")
if creds_json:
    import json
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
else:
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)

client = gspread.authorize(creds)

# Open the Google Sheet file and target the 'Fixtures' tab
# Replace "PL Predictions" below with your exact Google Sheet filename if different
spreadsheet_name = "PL Predictions" 
sheet = client.open(spreadsheet_name).worksheet("Fixtures")

# 2. Football API Setup
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "b4d7bcc9be7147d78e53c7f11c9ec283")
headers = {"X-Auth-Token": API_KEY}

print("Fetching current matchday from Football API...")

# Step A: Get current competition status to find the current matchday
comp_url = "https://api.football-data.org/v4/competitions/PL"
comp_res = requests.get(comp_url, headers=headers).json()

current_matchday = comp_res.get("currentSeason", {}).get("currentMatchday")

if not current_matchday:
    print("Could not determine current matchday.")
    exit()

print(f"Current Gameweek/Matchday: {current_matchday}")

# Step B: Fetch matches ONLY for the current matchday
matches_url = f"https://api.football-data.org/v4/competitions/PL/matches?matchday={current_matchday}"
matches_res = requests.get(matches_url, headers=headers).json()
matches = matches_res.get("matches", [])

if not matches:
    print("No matches found for the current matchday.")
    exit()

# 3. Process Sheet Rows
all_rows = sheet.get_all_values()

# Create lookup map of existing rows in Google Sheet (Home Team + Away Team)
existing_fixtures = {}
for i, row in enumerate(all_rows[1:], start=2): # skip header row
    if len(row) >= 2:
        key = f"{row[0].strip().lower()} vs {row[1].strip().lower()}"
        existing_fixtures[key] = i

new_rows_to_add = []
updates_count = 0

for m in matches:
    home_team = m["homeTeam"]["name"]
    away_team = m["awayTeam"]["name"]
    status = m["status"]
    
    # Check if match is finished and extract score
    home_score = ""
    away_score = ""
    if status == "FINISHED":
        home_score = m["score"]["fullTime"]["home"]
        away_score = m["score"]["fullTime"]["away"]

    fixture_key = f"{home_team.strip().lower()} vs {away_team.strip().lower()}"

    # If fixture already exists in Google Sheet, update score if needed
    if fixture_key in existing_fixtures:
        row_num = existing_fixtures[fixture_key]
        current_home_val = sheet.cell(row_num, 3).value if len(all_rows[row_num-1]) >= 3 else None
        
        if status == "FINISHED" and (current_home_val is None or current_home_val == ""):
            sheet.update_cell(row_num, 3, home_score)
            sheet.update_cell(row_num, 4, away_score)
            print(f"Updated score: {home_team} {home_score} - {away_score} {away_team}")
            updates_count += 1
    else:
        # If fixture is missing from Google Sheet, add it to new_rows list
        new_rows_to_add.append([home_team, away_team, home_score, away_score, f"GW{current_matchday}"])

# Append any missing fixtures for this current gameweek
if new_rows_to_add:
    for new_row in new_rows_to_add:
        sheet.append_row(new_row)
    print(f"Added {len(new_rows_to_add)} missing fixtures for Gameweek {current_matchday} to 'Fixtures' tab.")
else:
    print(f"All Gameweek {current_matchday} fixtures already exist in 'Fixtures' tab.")

print(f"Finished. Total score updates made: {updates_count}")
