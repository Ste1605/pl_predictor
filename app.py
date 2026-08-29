import os
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timezone

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="PL Predictor", 
    page_icon="⚽", 
    layout="centered"
)

# Premier League Header Logo URL
PL_LOGO_URL = "https://upload.wikimedia.org/wikipedia/en/f/f2/Premier_League_Logo.svg"

# Premier League Official Team Badge Directory
TEAM_BADGES = {
    "brighton hove": "https://upload.wikimedia.org/wikipedia/en/thumb/d/d0/Brighton_and_Hove_Albion_FC_crest.svg/250px-Brighton_and_Hove_Albion_FC_crest.svg.png",
    "brighton & hove albion": "https://upload.wikimedia.org/wikipedia/en/thumb/d/d0/Brighton_and_Hove_Albion_FC_crest.svg/250px-Brighton_and_Hove_Albion_FC_crest.svg.png",
    "brighton": "https://upload.wikimedia.org/wikipedia/en/thumb/d/d0/Brighton_and_Hove_Albion_FC_crest.svg/250px-Brighton_and_Hove_Albion_FC_crest.svg.png",
    
    "aston villa": "https://upload.wikimedia.org/wikipedia/en/thumb/9/9a/Aston_Villa_FC_new_crest.svg/250px-Aston_Villa_FC_new_crest.svg.png",
    "aston villa fc": "https://upload.wikimedia.org/wikipedia/en/thumb/9/9a/Aston_Villa_FC_new_crest.svg/250px-Aston_Villa_FC_new_crest.svg.png",
    
    "fulham": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/600px_FFC_su_sfondo_Bianco_e_Nero.png/960px-600px_FFC_su_sfondo_Bianco_e_Nero.png",
    "fulham fc": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/600px_FFC_su_sfondo_Bianco_e_Nero.png/960px-600px_FFC_su_sfondo_Bianco_e_Nero.png",
    
    "coventry city": "https://upload.wikimedia.org/wikipedia/en/thumb/7/7b/Coventry_City_FC_crest.svg/250px-Coventry_City_FC_crest.svg.png",
    "coventry": "https://upload.wikimedia.org/wikipedia/en/thumb/7/7b/Coventry_City_FC_crest.svg/250px-Coventry_City_FC_crest.svg.png",

    "arsenal": "https://upload.wikimedia.org/wikipedia/en/5/53/Arsenal_FC.svg",
    "bournemouth": "https://upload.wikimedia.org/wikipedia/en/e/e5/AFC_Bournemouth_%282013%29.svg",
    "brentford": "https://upload.wikimedia.org/wikipedia/en/2/2a/Brentford_FC_crest.svg",
    "chelsea": "https://upload.wikimedia.org/wikipedia/en/c/cc/Chelsea_FC.svg",
    "crystal palace": "https://upload.wikimedia.org/wikipedia/en/a/a2/Crystal_Palace_FC_logo_%282022%29.svg",
    "everton": "https://upload.wikimedia.org/wikipedia/en/7/7c/Everton_FC_logo.svg",
    "hull city": "https://upload.wikimedia.org/wikipedia/en/5/54/Hull_City_A.F.C._logo.svg",
    "ipswich town": "https://upload.wikimedia.org/wikipedia/en/4/43/Ipswich_Town.svg",
    "leeds united": "https://upload.wikimedia.org/wikipedia/en/5/54/Leeds_United_F.C._logo.svg",
    "leicester city": "https://upload.wikimedia.org/wikipedia/en/2/2d/Leicester_City_crest.svg",
    "liverpool": "https://upload.wikimedia.org/wikipedia/en/0/0c/Liverpool_FC.svg",
    "man city": "https://upload.wikimedia.org/wikipedia/en/e/eb/Manchester_City_FC_badge.svg",
    "manchester city": "https://upload.wikimedia.org/wikipedia/en/e/eb/Manchester_City_FC_badge.svg",
    "man united": "https://upload.wikimedia.org/wikipedia/en/7/7a/Manchester_United_FC_crest.svg",
    "manchester united": "https://upload.wikimedia.org/wikipedia/en/7/7a/Manchester_United_FC_crest.svg",
    "newcastle": "https://upload.wikimedia.org/wikipedia/en/5/56/Newcastle_United_Logo.svg",
    "newcastle united": "https://upload.wikimedia.org/wikipedia/en/5/56/Newcastle_United_Logo.svg",
    "nottingham": "https://upload.wikimedia.org/wikipedia/en/e/e5/Nottingham_Forest_F.C._logo.svg",
    "nottingham forest": "https://upload.wikimedia.org/wikipedia/en/e/e5/Nottingham_Forest_F.C._logo.svg",
    "southampton": "https://upload.wikimedia.org/wikipedia/en/c/c9/FC_Southampton.svg",
    "sunderland": "https://upload.wikimedia.org/wikipedia/en/7/77/Logo_Sunderland.svg",
    "tottenham": "https://upload.wikimedia.org/wikipedia/en/b/b4/Tottenham_Hotspur.svg",
    "tottenham hotspur": "https://upload.wikimedia.org/wikipedia/en/b/b4/Tottenham_Hotspur.svg",
    "west ham": "https://upload.wikimedia.org/wikipedia/en/c/c2/West_Ham_United_FC_logo.svg",
    "wolves": "https://upload.wikimedia.org/wikipedia/en/c/c9/Wolverhampton_Wanderers_FC_crest.svg",
    "wolverhampton wanderers": "https://upload.wikimedia.org/wikipedia/en/c/c9/Wolverhampton_Wanderers_FC_crest.svg"
}

def get_badge_url(team_name):
    clean_name = str(team_name).strip().lower()
    if clean_name in TEAM_BADGES:
        return TEAM_BADGES[clean_name]
    if "brighton" in clean_name:
        return TEAM_BADGES["brighton hove"]
    if "villa" in clean_name:
        return TEAM_BADGES["aston villa"]
    if "fulham" in clean_name:
        return TEAM_BADGES["fulham"]
    if "coventry" in clean_name:
        return TEAM_BADGES["coventry city"]
    return TEAM_BADGES.get(clean_name, "https://upload.wikimedia.org/wikipedia/commons/d/d3/Soccerball.svg")

# ------------------ STYLING (CSS) ------------------
st.markdown("""
    <style>
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
        max-width: 850px;
        margin: 0 auto;
    }
    .header-branding {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 24px;
        padding-bottom: 12px;
        border-bottom: 2px solid #21262d;
    }
    .header-branding img { height: 52px; width: auto; }
    .header-branding h1 { font-size: 28px; font-weight: 800; margin: 0; color: #f0f6fc; }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
    }
    .badge-ft { background: #1f6feb; color: #ffffff; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }
    .badge-locked { background-color: #21262d; color: #8b949e; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
    .badge-pending { background-color: rgba(56, 139, 253, 0.15); color: #58a6ff; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
    .pts-badge-green { color: #3fb950; font-weight: 700; background: rgba(46, 160, 67, 0.15); padding: 3px 8px; border-radius: 6px; }
    .pts-badge-red { color: #f85149; font-weight: 700; background: rgba(248, 81, 73, 0.15); padding: 3px 8px; border-radius: 6px; }

    .team-row { display: flex; align-items: center; justify-content: space-between; margin: 8px 0; }
    .team-badge-container { display: flex; align-items: center; gap: 8px; }
    .team-crest { width: 22px; height: 22px; object-fit: contain; }
    .team-name { font-size: 14px; font-weight: 700; color: #f0f6fc; }
    .day-header { font-size: 13px; font-weight: 700; color: #a371f7; text-transform: uppercase; margin-top: 18px; margin-bottom: 8px; border-bottom: 1px solid #21262d; }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="header-branding">
        <img src="{PL_LOGO_URL}" alt="Premier League Logo" />
        <h1>Premier League Predictor</h1>
    </div>
""", unsafe_allow_html=True)

# ------------------ AUTHENTICATION & CONFIG ------------------
@st.cache_resource
def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    elif "GOOGLE_CREDENTIALS" in os.environ:
        import json
        creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)

    gc = gspread.authorize(creds)
    return gc.open("PL Predictions")

def parse_kickoff_date(kickoff_raw):
    if not kickoff_raw:
        return None
    time_str = str(kickoff_raw).strip()
    try:
        return datetime.strptime(time_str, "%d %b %Y, %H:%M")
    except ValueError:
        try:
            clean_time = time_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_time)
        except Exception:
            return None

def is_kickoff_passed(kickoff_raw):
    dt = parse_kickoff_date(kickoff_raw)
    if not dt:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    return now_utc >= dt

def get_day_header(kickoff_raw):
    dt = parse_kickoff_date(kickoff_raw)
    if not dt:
        return str(kickoff_raw) if kickoff_raw else "Date TBD"
    return dt.strftime("%A, %d %b %Y")

def get_time_only(kickoff_raw):
    dt = parse_kickoff_date(kickoff_raw)
    if not dt:
        return ""
    return dt.strftime("%H:%M")

def calculate_points(pred_home, pred_away, act_home, act_away):
    try:
        p_h, p_a = int(pred_home), int(pred_away)
        a_h, a_a = int(act_home), int(act_away)
    except (ValueError, TypeError):
        return None

    if p_h == a_h and p_a == a_a:
        return 3
    elif (p_h > p_a and a_h > a_a) or \
         (p_h < p_a and a_h < a_a) or \
         (p_h == p_a and a_h == a_a):
        return 1
    return 0

try:
    sh = get_gsheet()
    fixtures_sheet = sh.worksheet("Fixtures Tab")
    predictions_sheet = sh.worksheet("Predictions Tab")
    
    fixtures = fixtures_sheet.get_all_records()
    raw_preds = predictions_sheet.get_all_records()

    tab_predict, tab_leaderboard = st.tabs(["📝 Match Center", "🏆 Leaderboard"])

    results_map = {}
    match_gw_map = {}
    for m in fixtures:
        m_id = str(m.get("Match ID", "")).strip()
        gw_val = str(m.get("GameWeek", "")).strip()
        status_val = str(m.get("Status", "")).strip().upper()
        h_actual = m.get("Actual Home Score", m.get("Home Score", ""))
        a_actual = m.get("Actual Away Score", m.get("Away Score", ""))

        if m_id:
            match_gw_map[m_id] = gw_val

        if status_val in ["FINISHED", "PAUSED"] or (h_actual != "" and a_actual != "" and h_actual is not None and a_actual is not None):
            try:
                results_map[m_id] = (int(h_actual), int(a_actual))
            except (ValueError, TypeError):
                pass

    user_preds_map = {}
    for p in raw_preds:
        m_id = str(p.get("Match ID", "")).strip()
        user = str(p.get("User ID", "") or p.get("User", "") or p.get("Name", "")).strip().lower()
        p_home = p.get("Predicted Home", p.get("Predicted Home Score", p.get("Home Score", "")))
        p_away = p.get("Predicted Away", p.get("Predicted Away Score", p.get("Away Score", "")))
        if m_id and user:
            user_preds_map[(m_id, user)] = (p_home, p_away)

    # ------------------ TAB 1: PREDICTIONS ------------------
    with tab_predict:
        top_c1, top_c2 = st.columns([2, 1])
        with top_c2:
            test_mode = st.toggle("🧪 Test Mode", value=False)
        
        user_name = st.text_input("Player Name / Email:", value="", placeholder="Enter your name...").strip()

        gw_list = [str(m.get("GameWeek")).strip() for m in fixtures if m.get("GameWeek")]
        gameweeks = sorted(list(set(gw_list)), key=lambda x: int(x.replace("GW", "")) if x.replace("GW", "").isdigit() else x)

        if not gameweeks:
            st.error("No Gameweeks found in sheet.")
        else:
            selected_gw = st.selectbox("Gameweek:", gameweeks)
            filtered_fixtures = [m for m in fixtures if str(m.get("GameWeek", "")).strip() == str(selected_gw).strip()]

            with st.form(key=f"gw_form_{selected_gw}_test_{test_mode}", clear_on_submit=False):
                predictions_input = {}
                has_submittable = False

                grouped_fixtures = {}
                for match in filtered_fixtures:
                    day_str = get_day_header(match.get("Kickoff Time", ""))
                    if day_str not in grouped_fixtures:
                        grouped_fixtures[day_str] = []
                    grouped_fixtures[day_str].append(match)

                for day_str, matches in grouped_fixtures.items():
                    st.markdown(f"<div class='day-header'>📅 {day_str}</div>", unsafe_allow_html=True)
                    grid_cols = st.columns(2)

                    for idx, match in enumerate(matches):
                        match_id = str(match.get("Match ID", f"match_{idx}")).strip()
                        home = match.get("Home Team", "Home")
                        away = match.get("Away Team", "Away")
                        home_crest = get_badge_url(home)
                        away_crest = get_badge_url(away)
                        
                        kickoff = match.get("Kickoff Time", "")
                        time_str = get_time_only(kickoff)
                        status_val = str(match.get("Status", "")).strip().upper()
                        
                        is_finished = (status_val in ["FINISHED", "PAUSED"]) or (match_id in results_map)
                        kickoff_passed = is_kickoff_passed(kickoff)
                        
                        user_key = (match_id, user_name.lower()) if user_name else None
                        saved_pred = user_preds_map.get(user_key) if user_key else None
                        
                        target_col = grid_cols[idx % 2]

                        with target_col:
                            with st.container(border=True):
                                match_teams_html = f"""
                                <div class="team-row">
                                    <div class="team-badge-container">
                                        <img src="{home_crest}" class="team-crest" />
                                        <span class="team-name">{home}</span>
                                    </div>
                                    <span style="color:#8b949e; font-size:12px;">vs</span>
                                    <div class="team-badge-container">
                                        <span class="team-name">{away}</span>
                                        <img src="{away_crest}" class="team-crest" />
                                    </div>
                                </div>
                                """

                                if test_mode or (not is_finished and not kickoff_passed):
                                    has_submittable = True
                                    time_label = f" • {time_str}" if time_str else ""
                                    st.markdown(f"<span class='badge-pending'>UPCOMING{time_label}</span>", unsafe_allow_html=True)
                                    st.markdown(match_teams_html, unsafe_allow_html=True)
                                    
                                    init_h = str(saved_pred[0]) if saved_pred and saved_pred[0] is not None else ""
                                    init_a = str(saved_pred[1]) if saved_pred and saved_pred[1] is not None else ""

                                    p_col1, p_col2 = st.columns(2)
                                    with p_col1:
                                        h_str = st.text_input(f"{home}", value=init_h, placeholder=home[:3].upper(), max_chars=2, key=f"home_{match_id}", label_visibility="collapsed")
                                    with p_col2:
                                        a_str = st.text_input(f"{away}", value=init_a, placeholder=away[:3].upper(), max_chars=2, key=f"away_{match_id}", label_visibility="collapsed")
                                    
                                    predictions_input[match_id] = (h_str, a_str)

                                elif is_finished:
                                    act_h, act_a = results_map.get(match_id, ("-", "-"))
                                    st.markdown("<span class='badge-ft'>FINAL RESULT</span>", unsafe_allow_html=True)
                                    st.markdown(f"""
                                    <div class="team-row" style="margin-top:8px;">
                                        <div class="team-badge-container">
                                            <img src="{home_crest}" class="team-crest" />
                                            <span class="team-name">{home}</span>
                                        </div>
                                        <div style="font-size:16px; font-weight:800; color:#a371f7;">{act_h} - {act_a}</div>
                                        <div class="team-badge-container">
                                            <span class="team-name">{away}</span>
                                            <img src="{away_crest}" class="team-crest" />
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    if saved_pred and saved_pred[0] != "" and saved_pred[1] != "":
                                        pts = calculate_points(saved_pred[0], saved_pred[1], act_h, act_a)
                                        badge_cls = "pts-badge-green" if pts is not None and pts > 0 else "pts-badge-red"
                                        st.markdown(f"<div style='font-size:12px; color:#8b949e; margin-top:4px;'>Your Pick: <code>{saved_pred[0]} - {saved_pred[1]}</code> • <span class='{badge_cls}'>+{pts} Pts</span></div>", unsafe_allow_html=True)
                                    else:
                                        st.caption("Your Pick: *No prediction submitted*")

                                else:
                                    st.markdown("<span class='badge-locked'>LOCKED</span>", unsafe_allow_html=True)
                                    st.markdown(match_teams_html, unsafe_allow_html=True)
                                    p_col1, p_col2 = st.columns(2)
                                    with p_col1:
                                        val_h = saved_pred[0] if saved_pred else "-"
                                        st.text_input(f"{home}", value=str(val_h), disabled=True, key=f"dis_h_{match_id}", label_visibility="collapsed")
                                    with p_col2:
                                        val_a = saved_pred[1] if saved_pred else "-"
                                        st.text_input(f"{away}", value=str(val_a), disabled=True, key=f"dis_a_{match_id}", label_visibility="collapsed")

                st.markdown("<br>", unsafe_allow_html=True)

                if has_submittable:
                    submit_all_btn = st.form_submit_button("🚀 Save Predictions", use_container_width=True)

                    if submit_all_btn:
                        if not user_name:
                            st.error("❌ Please enter your player name at the top before submitting!")
                        else:
                            parsed_predictions = {}
                            has_invalid = False
                            
                            for m_id, (h_val, a_val) in predictions_input.items():
                                h_clean = str(h_val).strip()
                                a_clean = str(a_val).strip()

                                if h_clean == "" and a_clean == "":
                                    continue

                                if h_clean.isdigit() and a_clean.isdigit():
                                    parsed_predictions[m_id] = (int(h_clean), int(a_clean))
                                else:
                                    has_invalid = True

                            if has_invalid:
                                st.error("❌ Please enter valid numerical scores.")
                            elif not parsed_predictions:
                                st.warning("⚠️ Enter at least one prediction score to submit.")
                            else:
                                with st.spinner("Saving predictions..."):
                                    row_map = {}
                                    for idx_r, row in enumerate(raw_preds, start=2):
                                        m_id = str(row.get("Match ID", "")).strip()
                                        u_name = str(row.get("User ID", "") or row.get("User", "") or row.get("Name", "")).strip()
                                        if m_id and u_name:
                                            row_map[(m_id, u_name.lower())] = idx_r

                                    rows_to_append = []
                                    updated_count = 0
                                    added_count = 0

                                    for m_id, (h_val, a_val) in parsed_predictions.items():
                                        key = (str(m_id).strip(), user_name.lower())
                                        pts_awarded = ""
                                        if m_id in results_map:
                                            pts = calculate_points(h_val, a_val, results_map[m_id][0], results_map[m_id][1])
                                            pts_awarded = str(pts) if pts is not None else ""

                                        if key in row_map:
                                            target_row = row_map[key]
                                            predictions_sheet.update(
                                                range_name=f"D{target_row}:F{target_row}", 
                                                values=[[h_val, a_val, pts_awarded]]
                                            )
                                            updated_count += 1
                                        else:
                                            pred_id = f"PRED_{datetime.now().strftime('%M%S')}_{m_id}"
                                            rows_to_append.append([pred_id, user_name, m_id, h_val, a_val, pts_awarded])
                                            added_count += 1

                                    if rows_to_append:
                                        predictions_sheet.append_rows(rows_to_append)

                                    st.success(f"🎉 Predictions saved! ({updated_count} updated, {added_count} new)")
                                    st.cache_resource.clear()
                else:
                    st.form_submit_button("🔒 Predictions Closed", disabled=True, use_container_width=True)

    # ------------------ TAB 2: LEADERBOARD ------------------
    with tab_leaderboard:
        st.subheader("🏆 Leaderboard Standings")

        gw_options = ["Overall Standings"] + [f"Gameweek {gw}" for gw in gameweeks]
        selected_lb_view = st.selectbox("Select View:", gw_options)

        user_scores = {}
        for idx_r, p in enumerate(raw_preds, start=2):
            m_id = str(p.get("Match ID", "")).strip()
            user = str(p.get("User ID", "") or p.get("User", "") or p.get("Name", "")).strip()
            p_home = p.get("Predicted Home", p.get("Predicted Home Score", p.get("Home Score", "")))
            p_away = p.get("Predicted Away", p.get("Predicted Away Score", p.get("Away Score", "")))

            match_gw = match_gw_map.get(m_id, "")
            if selected_lb_view != "Overall Standings":
                target_gw = selected_lb_view.replace("Gameweek ", "").strip()
                if str(match_gw).strip() != target_gw:
                    continue

            if user and m_id in results_map:
                if user not in user_scores:
                    user_scores[user] = {"Points": 0, "Exact Scores (3pts)": 0, "Correct Outcomes (1pt)": 0, "Matches Evaluated": 0}

                act_home, act_away = results_map[m_id]
                pts = calculate_points(p_home, p_away, act_home, act_away)
                if pts is None:
                    continue

                user_scores[user]["Matches Evaluated"] += 1
                if pts == 3:
                    user_scores[user]["Points"] += 3
                    user_scores[user]["Exact Scores (3pts)"] += 1
                elif pts == 1:
                    user_scores[user]["Points"] += 1
                    user_scores[user]["Correct Outcomes (1pt)"] += 1

        if user_scores:
            df = pd.DataFrame.from_dict(user_scores, orient="index")
            df = df.sort_values(by=["Points", "Exact Scores (3pts)", "Correct Outcomes (1pt)"], ascending=[False, False, False])
            df.index.name = "Player"
            
            df.reset_index(inplace=True)
            df.index = df.index + 1
            df.index.name = "Rank"
            
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Player": st.column_config.TextColumn("Player Name", width="medium"),
                    "Points": st.column_config.NumberColumn("Total Points", format="%d Pts"),
                    "Exact Scores (3pts)": st.column_config.NumberColumn("Exact (3pts)", format="%d 🎯"),
                    "Correct Outcomes (1pt)": st.column_config.NumberColumn("Outcome (1pt)", format="%d 👍"),
                    "Matches Evaluated": st.column_config.NumberColumn("Played", format="%d ⚽")
                }
            )
        else:
            st.info(f"No leaderboard standings available for {selected_lb_view}.")

except Exception as e:
    st.error(f"Error connecting to Google Sheets: {e}")
