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

# Premier League Official Team Badge Directory (Reliable PNG CDN Links)
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

# Custom UI Name Shortener
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
        background-color: #f0f4f8;
        color: #1e293b;
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
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 10px;
    }

    /* Force Centered & Bold Numbers Inside Score Fields */
    .stTextInput input {
        text-align: center !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        color: #0f172a !important;
        background-color: #f8fafc !important;
        border-radius: 8px !important;
    }

    .badge-ft { background: #2563eb; color: #ffffff; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }
    .badge-locked { background-color: #cbd5e1; color: #475569; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
    .badge-pending { background-color: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
    .badge-saved { background-color: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }
    
    .pts-badge-green { color: #166534; font-weight: 700; background: #dcfce7; padding: 3px 8px; border-radius: 6px; }
    .pts-badge-red { color: #991b1b; font-weight: 700; background: #fee2e2; padding: 3px 8px; border-radius: 6px; }

    .team-row { display: flex; align-items: center; justify-content: space-between; margin: 8px 0; }
    .team-badge-container { display: flex; align-items: center; gap: 8px; }
    .team-crest { width: 22px; height: 22px; object-fit: contain; }
    .team-name { font-size: 14px; font-weight: 700; color: #1e293b !important; white-space: nowrap; }
    .day-header { font-size: 13px; font-weight: 700; color: #1d4ed8; text-transform: uppercase; margin-top: 18px; margin-bottom: 8px; border-bottom: 1px solid #cbd5e1; }
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
        
        # --- Item 1: Persistent Name Logic ---
        query_params = st.query_params
        default_name = query_params.get("player", "")
        
        user_name = st.text_input(
            "Player Name / Email:", 
            value=default_name, 
            placeholder="Enter your name...",
            key="player_name_input"
        ).strip()
        
        if user_name and query_params.get("player") != user_name:
            st.query_params["player"] = user_name

        gw_list = [str(m.get("GameWeek")).strip() for m in fixtures if m.get("GameWeek")]
        gameweeks = sorted(list(set(gw_list)), key=lambda x: int(x.replace("GW", "")) if x.replace("GW", "").isdigit() else x)

        if not gameweeks:
            st.error("No Gameweeks found in sheet.")
        else:
            # --- Item 2: Auto-detect Next Active Gameweek ---
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
                    
                    for i in range(0, len(matches), 2):
                        pair = matches[i:i+2]
                        cols = st.columns(2)
                        
                        for idx, match in enumerate(pair):
                            match_id = str(match.get("Match ID", f"match_{i+idx}")).strip()
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

                            # --- Item 4: Dynamic Card Colors ---
                            card_bg = "#ffffff"
                            card_border = "#cbd5e1"
                            
                            if is_finished or kickoff_passed:
                                card_bg = "#f1f5f9"
                                card_border = "#94a3b8"
                            elif has_saved:
                                card_border = "#22c55e"

                            with cols[idx]:
                                # Inline style wrapper to color card containers dynamically
                                st.markdown(f"""
                                    <style>
                                    div[data-testid="stVerticalBlockBorderWrapper"]:has(#card_{match_id}) {{
                                        background-color: {card_bg} !important;
                                        border: 2px solid {card_border} !important;
                                    }}
                                    </style>
                                    <div id="card_{match_id}"></div>
                                """, unsafe_allow_html=True)

                                with st.container(border=True):
                                    match_teams_html = f"""
                                    <div class="team-row">
                                        <div class="team-badge-container">
                                            <img src="{home_crest}" class="team-crest" />
                                            <span class="team-name">{home}</span>
                                        </div>
                                        <span style="color:#64748b; font-size:12px; font-weight:600;">vs</span>
                                        <div class="team-badge-container">
                                            <span class="team-name">{away}</span>
                                            <img src="{away_crest}" class="team-crest" />
                                        </div>
                                    </div>
                                    """

                                    if test_mode or (not is_finished and not kickoff_passed):
                                        has_submittable = True
                                        time_label = f" • {time_str}" if time_str else ""
                                        
                                        if has_saved:
                                            st.markdown(f"<span class='badge-saved'>SAVED{time_label}</span>", unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"<span class='badge-pending'>UPCOMING{time_label}</span>", unsafe_allow_html=True)

                                        st.markdown(match_teams_html, unsafe_allow_html=True)
                                        
                                        init_h = str(saved_pred[0]) if saved_pred and saved_pred[0] is not None else ""
                                        init_a = str(saved_pred[1]) if saved_pred and saved_pred[1] is not None else ""

                                        p_col1, p_col2 = st.columns(2)
                                        with p_col1:
                                            h_str = st.text_input(f"{home}", value=init_h, placeholder="-", max_chars=2, key=f"home_{match_id}", label_visibility="collapsed")
                                        with p_col2:
                                            a_str = st.text_input(f"{away}", value=init_a, placeholder="-", max_chars=2, key=f"away_{match_id}", label_visibility="collapsed")
                                        
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
                                            <div style="font-size:16px; font-weight:800; color:#2563eb;">{act_h} - {act_a}</div>
                                            <div class="team-badge-container">
                                                <span class="team-name">{away}</span>
                                                <img src="{away_crest}" class="team-crest" />
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        if saved_pred and saved_pred[0] != "" and saved_pred[1] != "":
                                            pts = calculate_points(saved_pred[0], saved_pred[1], act_h, act_a)
                                            badge_cls = "pts-badge-green" if pts is not None and pts > 0 else "pts-badge-red"
                                            st.markdown(f"<div style='font-size:11px; color:#64748b; margin-top:4px;'>Your Pick: <code>{saved_pred[0]} - {saved_pred[1]}</code> • <span class='{badge_cls}'>+{pts} Pts</span></div>", unsafe_allow_html=True)
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
