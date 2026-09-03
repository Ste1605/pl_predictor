import os
import json
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="Premier League Predictor", 
    page_icon="🏆",
    layout="centered"
)

PL_LOGO_URL = "https://upload.wikimedia.org/wikipedia/en/f/f2/Premier_League_Logo.svg"

TEAM_BADGES = {
    "arsenal": "https://a.espncdn.com/i/teamlogos/soccer/500/359.png",
    "aston villa": "https://a.espncdn.com/i/teamlogos/soccer/500/362.png",
    "bournemouth": "https://a.espncdn.com/i/teamlogos/soccer/500/349.png",
    "brentford": "https://a.espncdn.com/i/teamlogos/soccer/500/337.png",
    "brighton": "https://a.espncdn.com/i/teamlogos/soccer/500/331.png",
    "brighton & hove albion": "https://a.espncdn.com/i/teamlogos/soccer/500/331.png",
    "chelsea": "https://a.espncdn.com/i/teamlogos/soccer/500/363.png",    
    "crystal palace": "https://a.espncdn.com/i/teamlogos/soccer/500/384.png",
    "everton": "https://a.espncdn.com/i/teamlogos/soccer/500/368.png",
    "fulham": "https://a.espncdn.com/i/teamlogos/soccer/500/370.png",
    "hull city": "https://a.espncdn.com/i/teamlogos/soccer/500/306.png",
    "ipswich town": "https://a.espncdn.com/i/teamlogos/soccer/500/373.png",
    "leeds united": "https://a.espncdn.com/i/teamlogos/soccer/500/357.png",
    "leicester city": "https://a.espncdn.com/i/teamlogos/soccer/500/375.png",
    "liverpool": "https://a.espncdn.com/i/teamlogos/soccer/500/364.png",
    "manchester city": "https://a.espncdn.com/i/teamlogos/soccer/500/382.png",
    "manchester united": "https://a.espncdn.com/i/teamlogos/soccer/500/360.png",
    "newcastle united": "https://a.espncdn.com/i/teamlogos/soccer/500/361.png",
    "nottingham forest": "https://a.espncdn.com/i/teamlogos/soccer/500/393.png",
    "southampton": "https://a.espncdn.com/i/teamlogos/soccer/500/376.png",
    "sunderland": "https://a.espncdn.com/i/teamlogos/soccer/500/366.png",
    "tottenham hotspur": "https://a.espncdn.com/i/teamlogos/soccer/500/367.png",
    "west ham united": "https://a.espncdn.com/i/teamlogos/soccer/500/371.png",
    "wolverhampton wanderers": "https://a.espncdn.com/i/teamlogos/soccer/500/380.png",
    "coventry": "https://upload.wikimedia.org/wikipedia/en/thumb/7/7b/Coventry_City_FC_crest.svg/250px-Coventry_City_FC_crest.svg.png",
    "coventry city": "https://upload.wikimedia.org/wikipedia/en/thumb/7/7b/Coventry_City_FC_crest.svg/250px-Coventry_City_FC_crest.svg.png"
}

def get_badge_url(team_name):
    clean_name = str(team_name).strip().lower()
    if clean_name in TEAM_BADGES:
        return TEAM_BADGES[clean_name]
    for key, url in TEAM_BADGES.items():
        if key in clean_name or clean_name in key:
            return url
    return "https://a.espncdn.com/i/teamlogos/soccer/500/default-team-logo.png"

SHORT_TEAM_NAMES = {
    "Brighton & Hove Albion FC": "Brighton",
    "Brighton & Hove Albion": "Brighton",
    "Wolverhampton Wanderers FC": "Wolves",
    "Wolverhampton Wanderers": "Wolves",
    "West Ham United FC": "West Ham",
    "West Ham United": "West Ham",
    "Tottenham Hotspur FC": "Tottenham",
    "Tottenham Hotspur": "Tottenham",
    "Nottingham Forest FC": "Nottingham Forest",
    "Manchester United FC": "Man United",
    "Manchester City FC": "Man City",
    "Newcastle United FC": "Newcastle",
    "Leeds United FC": "Leeds",
    "Leicester City FC": "Leicester",
    "Ipswich Town FC": "Ipswich",
    "Coventry City FC": "Coventry",
    "Hull City AFC": "Hull City",
    "Sunderland AFC": "Sunderland",
    "AFC Bournemouth": "Bournemouth",
    "Aston Villa FC": "Aston Villa",
    "Fulham FC": "Fulham",
    "Arsenal FC": "Arsenal",
    "Chelsea FC": "Chelsea",
    "Everton FC": "Everton",
    "Liverpool FC": "Liverpool",
    "Southampton FC": "Southampton"
}

def get_short_name(team_name):
    clean = str(team_name).strip()
    return SHORT_TEAM_NAMES.get(clean, clean)

# ------------------ STYLING ------------------
st.markdown("""
    <style>
    .stApp {
        background-color: #f0f4f8 !important;
        color: #1e293b !important;
        max-width: 850px;
        margin: 0 auto;
    }

    .header-branding {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 24px;
        padding-bottom: 12px;
        border-bottom: 2px solid #cbd5e1;
    }
    .header-branding img { height: 52px; width: auto; }
    .header-branding h1 { font-size: 28px; font-weight: 800; margin: 0; color: #0f172a !important; }

    button[data-baseweb="tab"] { color: #0f172a !important; font-weight: 700 !important; }
    button[data-baseweb="tab"] p { color: #0f172a !important; font-weight: 700 !important; }

    div[data-testid="stCheckbox"] label p,
    div[data-testid="stWidgetLabel"] label p,
    label p { color: #0f172a !important; font-weight: 700 !important; }

    .stTextInput input, .stSelectbox div {
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    .stTextInput input {
        text-align: center !important;
        font-size: 16px !important;
        background-color: #ffffff !important;
        border-radius: 8px !important;
    }

    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 12px !important;
        align-items: center !important;
    }
    
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div {
        width: 50% !important;
        min-width: 0 !important;
        flex: 1 1 50% !important;
    }

    div[data-testid="stFormSubmitButton"] button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        border-radius: 8px !important;
        border: none !important;
    }
    div[data-testid="stFormSubmitButton"] button p { color: #ffffff !important; }
    div[data-testid="stFormSubmitButton"] button:hover { background-color: #1d4ed8 !important; color: #ffffff !important; }

    .badge-ft { background: #2563eb; color: #ffffff !important; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; display: inline-block; }
    .badge-locked { background-color: #94a3b8; color: #ffffff !important; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; display: inline-block; }
    .badge-pending { background-color: #dbeafe; color: #1e40af !important; border: 1px solid #bfdbfe; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; display: inline-block; }
    .badge-saved { background-color: #dcfce7; color: #15803d !important; border: 1px solid #86efac; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; display: inline-block; }
    
    .pts-badge-green { color: #166534 !important; font-weight: 700; background: #dcfce7; padding: 3px 8px; border-radius: 6px; }
    .pts-badge-red { color: #991b1b !important; font-weight: 700; background: #fee2e2; padding: 3px 8px; border-radius: 6px; }

    .team-row-flex { 
        display: flex !important; 
        flex-direction: row !important;
        align-items: center !important; 
        justify-content: space-between !important; 
        margin: 10px 0 !important;
        width: 100% !important;
    }
    .team-side { 
        display: flex !important; 
        flex-direction: row !important;
        align-items: center !important; 
        gap: 6px !important; 
        flex: 1 !important;
    }
    .team-side.left { justify-content: flex-start !important; }
    .team-side.right { justify-content: flex-end !important; }

    .team-crest { width: 22px; height: 22px; object-fit: contain; flex-shrink: 0; }
    .team-name { font-size: 13px; font-weight: 700; color: #1e293b !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .vs-text { color: #64748b; font-size: 12px; font-weight: 600; padding: 0 6px; flex-shrink: 0; }
    
    .day-header { font-size: 13px; font-weight: 700; color: #1d4ed8 !important; text-transform: uppercase; margin-top: 18px; margin-bottom: 8px; border-bottom: 1px solid #cbd5e1; }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="header-branding">
        <img src="{PL_LOGO_URL}" alt="Premier League Logo" />
        <h1>Premier League Predictor</h1>
    </div>
""", unsafe_allow_html=True)

if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True

if st.session_state.show_welcome:
    with st.expander("👋 Welcome to Premier League Predictor! (Click to expand info)", expanded=True):
        st.write("""
        Welcome! Select or add your player name, set a 4-digit PIN to secure your account, predict scorelines for upcoming matches, and save your picks before kickoff.
        
        * **3 Points:** Exact scoreline prediction.
        * **1 Point:** Correct match outcome (Win/Loss/Draw).
        """)
        if st.button("Don't show this again", key="dismiss_welcome"):
            st.session_state.show_welcome = False
            st.rerun()

# --- Submission Confirmation Modal ---
@st.dialog("🎉 Predictions Saved!")
def show_confirmation_modal(user_name, predictions_dict, selected_gw):
    st.write(f"Great job, **{user_name}**! Here is a summary of your saved predictions for **{selected_gw}**:")
    
    summary_data = []
    for idx, (m_id, (h_val, a_val)) in enumerate(predictions_dict.items(), start=1):
        summary_data.append({
            "Match": f"{selected_gw} - Match {idx}",
            "Your Pick": f"{h_val} - {a_val}"
        })
    
    st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)
    st.success("Your picks are safely locked in Google Sheets!")
    if st.button("Close", use_container_width=True):
        st.rerun()

# ------------------ AUTHENTICATION & CONFIG ------------------
def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    elif "GOOGLE_CREDENTIALS" in os.environ:
        creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)

    gc = gspread.authorize(creds)
    return gc.open("PL Predictions")

# --- DATE & TIMEZONE HELPERS ---
def parse_kickoff_date(kickoff_raw):
    if not kickoff_raw:
        return None
    time_str = str(kickoff_raw).strip()
    
    dt = None
    try:
        dt = datetime.strptime(time_str, "%d %b %Y, %H:%M")
    except ValueError:
        try:
            clean_time = time_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_time)
        except Exception:
            return None

    if dt and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(ZoneInfo("Europe/Dublin"))

def is_kickoff_passed(kickoff_raw):
    dt = parse_kickoff_date(kickoff_raw)
    if not dt:
        return False
    now_local = datetime.now(ZoneInfo("Europe/Dublin"))
    return now_local >= dt

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

    tab_predict, tab_view_all, tab_leaderboard = st.tabs(["📝 Match Center", "👀 View All Picks", "🏆 Leaderboard"])

    results_map = {}
    match_gw_map = {}
    match_details_map = {}
    for m in fixtures:
        m_id = str(m.get("Match ID", "")).strip()
        gw_val = str(m.get("GameWeek", "")).strip()
        status_val = str(m.get("Status", "")).strip().upper()
        h_actual = m.get("Actual Home Score", m.get("Home Score", ""))
        a_actual = m.get("Actual Away Score", m.get("Away Score", ""))

        if m_id:
            match_gw_map[m_id] = gw_val
            match_details_map[m_id] = {
                "Home": get_short_name(m.get("Home Team", "Home")),
                "Away": get_short_name(m.get("Away Team", "Away")),
                "GameWeek": gw_val
            }

        if status_val in ["FINISHED", "PAUSED"] or (h_actual != "" and a_actual != "" and h_actual is not None and a_actual is not None):
            try:
                results_map[m_id] = (int(h_actual), int(a_actual))
            except (ValueError, TypeError):
                pass

    user_preds_map = {}
    known_users = set()
    user_pin_map = {}
    
    for p in raw_preds:
        m_id = str(p.get("Match ID", "")).strip()
        user = str(p.get("User ID", "") or p.get("User", "") or p.get("Name", "")).strip()
        p_home = p.get("Predicted Home", p.get("Predicted Home Score", p.get("Home Score", "")))
        p_away = p.get("Predicted Away", p.get("Predicted Away Score", p.get("Away Score", "")))
        pin_val = str(p.get("PIN", "")).strip()

        if user:
            known_users.add(user)
            u_clean = user.strip().lower()
            if pin_val:
                user_pin_map[u_clean] = pin_val
            if m_id:
                user_preds_map[(m_id, u_clean)] = (str(p_home).strip(), str(p_away).strip())

    user_list = sorted(list(known_users))

    gw_list = [str(m.get("GameWeek")).strip() for m in fixtures if m.get("GameWeek")]
    gameweeks = sorted(list(set(gw_list)), key=lambda x: int(x.replace("GW", "")) if x.replace("GW", "").isdigit() else x)

    # ------------------ TAB 1: PREDICTIONS ------------------
    with tab_predict:
        top_c1, top_c2 = st.columns([2, 1])
        with top_c2:
            test_mode = st.toggle("🧪 Test Mode", value=False)
        
        p_col1, p_col2 = st.columns([2, 1])
        user_name = ""
        entered_pin = ""
        is_authenticated = False
        is_new_player = False

        with p_col1:
            if user_list:
                options = ["-- Select Name --"] + user_list + ["+ Add New Player"]
                selected_user = st.selectbox("Player Name:", options, key="player_select")
                if selected_user == "+ Add New Player":
                    user_name = st.text_input("Enter New Name:", placeholder="Type name...", key="new_player_input").strip()
                    is_new_player = True
                elif selected_user != "-- Select Name --":
                    user_name = selected_user.strip()
            else:
                user_name = st.text_input("Player Name:", placeholder="Enter your name...", key="player_text_input").strip()
                is_new_player = True

        with p_col2:
            if user_name:
                stored_pin = user_pin_map.get(user_name.lower())
                if is_new_player or not stored_pin:
                    entered_pin = st.text_input("Create 4-Digit PIN:", type="password", max_chars=4, key="pin_create_input").strip()
                    if len(entered_pin) == 4 and entered_pin.isdigit():
                        is_authenticated = True
                    elif entered_pin:
                        st.warning("⚠️ Enter 4 numbers")
                else:
                    entered_pin = st.text_input("Enter 4-Digit PIN:", type="password", max_chars=4, key="pin_login_input").strip()
                    if entered_pin == stored_pin:
                        is_authenticated = True
                        st.success("🔓 Authenticated")
                    elif entered_pin:
                        st.error("❌ Invalid PIN")

        if not gameweeks:
            st.error("No Gameweeks found in sheet.")
        else:
            default_gw = gameweeks[0]
            for gw in gameweeks:
                gw_matches = [m for m in fixtures if str(m.get("GameWeek", "")).strip() == str(gw).strip()]
                has_unfinished = any(
                    str(m.get("Status", "")).strip().upper() not in ["FINISHED", "PAUSED"] 
                    and not is_kickoff_passed(m.get("Kickoff Time", ""))
                    for m in gw_matches
                )
                if has_unfinished:
                    default_gw = gw
                    break

            default_idx = gameweeks.index(default_gw) if default_gw in gameweeks else 0
            selected_gw = st.selectbox("Gameweek:", gameweeks, index=default_idx)
            filtered_fixtures = [m for m in fixtures if str(m.get("GameWeek", "")).strip() == str(selected_gw).strip()]

            if not is_authenticated and user_name:
                st.info("🔒 Enter your correct 4-Digit PIN above to unlock and view your predictions.")

            # Form key bound strictly to authentication status
            form_key = f"gw_form_{selected_gw}_test_{test_mode}_auth_{is_authenticated}_{user_name.lower()}"
            with st.form(key=form_key, clear_on_submit=False):
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
                    
                    for match in matches:
                        match_id = str(match.get("Match ID", "")).strip()
                        raw_home = match.get("Home Team", "Home")
                        raw_away = match.get("Away Team", "Away")
                        
                        home = get_short_name(raw_home)
                        away = get_short_name(raw_away)
                        
                        home_crest = get_badge_url(raw_home)
                        away_crest = get_badge_url(raw_away)
                        
                        kickoff = match.get("Kickoff Time", "")
                        time_str = get_time_only(kickoff)
                        status_val = str(match.get("Status", "")).strip().upper()
                        
                        is_finished = (status_val in ["FINISHED", "PAUSED"]) or (match_id in results_map)
                        kickoff_passed = is_kickoff_passed(kickoff)
                        
                        user_key = (match_id, user_name.lower()) if user_name else None
                        saved_pred = user_preds_map.get(user_key) if user_key else None
                        has_saved = saved_pred is not None and str(saved_pred[0]).strip() != "" and str(saved_pred[1]).strip() != ""

                        card_bg = "#ffffff"
                        card_border = "#cbd5e1"
                        
                        if is_finished or kickoff_passed:
                            card_bg = "#e2e8f0"
                            card_border = "#94a3b8"
                        elif has_saved:
                            card_bg = "#f0fdf4"
                            card_border = "#86efac"

                        match_teams_html = f"""
                        <div class="team-row-flex">
                            <div class="team-side left">
                                <img src="{home_crest}" class="team-crest" />
                                <span class="team-name">{home}</span>
                            </div>
                            <span class="vs-text">vs</span>
                            <div class="team-side right">
                                <span class="team-name">{away}</span>
                                <img src="{away_crest}" class="team-crest" />
                            </div>
                        </div>
                        """

                        if test_mode or (not is_finished and not kickoff_passed):
                            has_submittable = True
                            time_label = f" • {time_str}" if time_str else ""
                            
                            badge_html = f"<span class='badge-saved'>SAVED{time_label}</span>" if has_saved else f"<span class='badge-pending'>UPCOMING{time_label}</span>"

                            init_h = str(saved_pred[0]) if (saved_pred and saved_pred[0] is not None) else ""
                            init_a = str(saved_pred[1]) if (saved_pred and saved_pred[1] is not None) else ""

                            val_h = init_h if is_authenticated else ""
                            val_a = init_a if is_authenticated else ""

                            st.markdown(f"""
                            <div style="background-color: {card_bg}; border: 1.5px solid {card_border}; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);">
                                {badge_html}
                                {match_teams_html}
                            """, unsafe_allow_html=True)

                            p_col1, p_col2 = st.columns(2)
                            with p_col1:
                                h_str = st.text_input(f"{home}", value=val_h, placeholder="-", max_chars=2, key=f"h_{match_id}_{user_name.lower()}_auth_{is_authenticated}", label_visibility="collapsed", disabled=not is_authenticated)
                            with p_col2:
                                a_str = st.text_input(f"{away}", value=val_a, placeholder="-", max_chars=2, key=f"a_{match_id}_{user_name.lower()}_auth_{is_authenticated}", label_visibility="collapsed", disabled=not is_authenticated)
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                            predictions_input[match_id] = (h_str, a_str)

                        elif is_finished:
                            act_h, act_a = results_map.get(match_id, ("-", "-"))
                            
                            pick_html = ""
                            if saved_pred and saved_pred[0] != "" and saved_pred[1] != "":
                                pts = calculate_points(saved_pred[0], saved_pred[1], act_h, act_a)
                                badge_cls = "pts-badge-green" if pts is not None and pts > 0 else "pts-badge-red"
                                pick_html = f"<div style='font-size:12px; color:#475569; margin-top:6px;'>Your Pick: <b>{saved_pred[0]} - {saved_pred[1]}</b> • <span class='{badge_cls}'>+{pts} Pts</span></div>"
                            else:
                                pick_html = "<div style='font-size:12px; color:#64748b; margin-top:6px;'>Your Pick: <i>No prediction submitted</i></div>"

                            st.markdown(f"""
                            <div style="background-color: {card_bg}; border: 1.5px solid {card_border}; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03);">
                                <div><span class='badge-ft'>FINAL RESULT</span></div>
                                <div class="team-row-flex" style="margin-top:8px;">
                                    <div class="team-side left">
                                        <img src="{home_crest}" class="team-crest" />
                                        <span class="team-name">{home}</span>
                                    </div>
                                    <div style="font-size:16px; font-weight:800; color:#2563eb; padding:0 6px;">{act_h} - {act_a}</div>
                                    <div class="team-side right">
                                        <span class="team-name">{away}</span>
                                        <img src="{away_crest}" class="team-crest" />
                                    </div>
                                </div>
                                {pick_html}
                            </div>
                            """, unsafe_allow_html=True)

                        else:
                            val_h = saved_pred[0] if saved_pred and saved_pred[0] != "" else "-"
                            val_a = saved_pred[1] if saved_pred and saved_pred[1] != "" else "-"
                            
                            st.markdown(f"""
                            <div style="background-color: {card_bg}; border: 1.5px solid {card_border}; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03);">
                                <div><span class='badge-locked'>LOCKED</span></div>
                                {match_teams_html}
                                <div style='font-size:12px; color:#475569; margin-top:6px;'>Your Pick: <b>{val_h} - {val_a}</b></div>
                            </div>
                            """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                if has_submittable:
                    submit_all_btn = st.form_submit_button("🚀 Save Predictions", use_container_width=True, disabled=not is_authenticated)

                    if submit_all_btn:
                        if not user_name:
                            st.error("❌ Please select or enter your player name at the top before submitting!")
                        elif not is_authenticated:
                            st.error("❌ Please enter your valid 4-digit PIN to submit.")
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

                                    for m_id, (h_val, a_val) in parsed_predictions.items():
                                        key = (str(m_id).strip(), user_name.lower())
                                        pts_awarded = ""
                                        if m_id in results_map:
                                            pts = calculate_points(h_val, a_val, results_map[m_id][0], results_map[m_id][1])
                                            pts_awarded = str(pts) if pts is not None else ""

                                        if key in row_map:
                                            target_row = row_map[key]
                                            predictions_sheet.update(
                                                range_name=f"D{target_row}:G{target_row}", 
                                                values=[[h_val, a_val, pts_awarded, entered_pin]]
                                            )
                                        else:
                                            pred_id = f"PRED_{datetime.now().strftime('%M%S')}_{m_id}"
                                            rows_to_append.append([pred_id, user_name, m_id, h_val, a_val, pts_awarded, entered_pin])

                                    if rows_to_append:
                                        predictions_sheet.append_rows(rows_to_append)

                                    st.toast("🎉 Predictions saved successfully!", icon="⚽")
                                    show_confirmation_modal(user_name, parsed_predictions, selected_gw)
                else:
                    st.form_submit_button("🔒 Predictions Closed", disabled=True, use_container_width=True)

    # ------------------ TAB 2: READ-ONLY VIEW ALL PICKS ------------------
    with tab_view_all:
        st.subheader("👀 All Submitted Predictions")
        if gameweeks:
            selected_view_gw = st.selectbox("Select Gameweek:", gameweeks, key="all_picks_gw")
            
            gw_fixtures = [m for m in fixtures if str(m.get("GameWeek", "")).strip() == str(selected_view_gw).strip()]
            
            if not gw_fixtures:
                st.info(f"No fixtures found for {selected_view_gw}.")
            else:
                preds_by_match = {}
                for p in raw_preds:
                    m_id = str(p.get("Match ID", "")).strip()
                    user = str(p.get("User ID", "") or p.get("User", "") or p.get("Name", "")).strip()
                    p_home = p.get("Predicted Home", p.get("Predicted Home Score", p.get("Home Score", "")))
                    p_away = p.get("Predicted Away", p.get("Predicted Away Score", p.get("Away Score", "")))
                    
                    if m_id and user and str(p_home).strip() != "" and str(p_away).strip() != "":
                        if m_id not in preds_by_match:
                            preds_by_match[m_id] = []
                        preds_by_match[m_id].append({
                            "Player": user,
                            "Prediction": f"{p_home} - {p_away}"
                        })

                has_any_picks = False
                for match in gw_fixtures:
                    m_id = str(match.get("Match ID", "")).strip()
                    home = get_short_name(match.get("Home Team", "Home"))
                    away = get_short_name(match.get("Away Team", "Away"))
                    time_str = get_time_only(match.get("Kickoff Time", ""))
                    
                    match_picks = preds_by_match.get(m_id, [])
                    
                    if match_picks:
                        has_any_picks = True
                        with st.expander(f"⚽ **{home} vs {away}** ({time_str if time_str else 'TBD'}) — *{len(match_picks)} picks*", expanded=True):
                            df_match_picks = pd.DataFrame(match_picks)
                            st.dataframe(
                                df_match_picks, 
                                use_container_width=True, 
                                hide_index=True,
                                column_config={
                                    "Player": st.column_config.TextColumn("Player Name", width="medium"),
                                    "Prediction": st.column_config.TextColumn("Predicted Score", width="small")
                                }
                            )

                if not has_any_picks:
                    st.info(f"No predictions submitted yet for any matches in {selected_view_gw}.")

    # ------------------ TAB 3: LEADERBOARD ------------------
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
