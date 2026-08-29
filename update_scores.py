import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

# 1. Setup Google Sheets Authentication
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Use GitHub Secrets if running in the cloud, otherwise use local credentials.json
if "GOOGLE_CREDENTIALS" in os.environ:
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
else:
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

gc = gspread.authorize(creds)

# 2. Open Google Sheet
worksheet = gc.open("Premier_League_Predictor_Template").worksheet("Fixtures Tab")

# 3. Fetch Matches from Football API
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "b4d7bcc9be7147d78e53c7f11c9ec283") 
url = "https://api.football-data.org/v4/competitions/PL/matches"
headers = {"X-Auth-Token": API_KEY}

print("Fetching data from API...")
response = requests.get(url, headers=headers)
data = response.json()

if "matches" not in data:
    print("API Response Error:", data)
    exit()

print("Fetching data from API...")
response = requests.get(url, headers=headers)
data = response.json()

if "matches" not in data:
    print("Failed to fetch matches. Check API Key.")
    exit()

# 4. Filter Finished Matches & Update Sheet
finished_matches = {
    str(match["id"]): {
        "home_score": match["score"]["fullTime"]["home"],
        "away_score": match["score"]["fullTime"]["away"],
        "status": match["status"]
    }
    for match in data["matches"]
    if match["status"] == "FINISHED"
}

print(f"Found {len(finished_matches)} finished matches.")

all_rows = worksheet.get_all_values()
headers_row = all_rows[0]

# Column indexes (1-based for gspread)
match_id_idx = headers_row.index("Match ID") + 1
home_score_idx = headers_row.index("Actual Home Score") + 1
away_score_idx = headers_row.index("Actual Away Score") + 1
status_idx = headers_row.index("Status") + 1

cell_updates = []

for row_idx, row in enumerate(all_rows[1:], start=2):
    match_id = str(row[match_id_idx - 1])
    current_status = row[status_idx - 1]
    
    if match_id in finished_matches and current_status != "FINISHED":
        match_data = finished_matches[match_id]
        
        cell_updates.append(gspread.Cell(row_idx, home_score_idx, match_data["home_score"]))
        cell_updates.append(gspread.Cell(row_idx, away_score_idx, match_data["away_score"]))
        cell_updates.append(gspread.Cell(row_idx, status_idx, match_data["status"]))

if cell_updates:
    worksheet.update_cells(cell_updates)
    print(f"Successfully updated {len(cell_updates) // 3} matches in Google Sheets!")
else:
    print("No new finished matches to update.")