import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from itertools import combinations

st.set_page_config(page_title="WC 2026 • High Odds + High Probability", page_icon="⚽", layout="wide")

# Load secrets BEFORE running engine functions
if "ODDS_API_KEY" in st.secrets:
    os.environ["ODDS_API_KEY"] = st.secrets["ODDS_API_KEY"]
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

from engine import get_value_picks

# Apple Bento Dark Styling (Matched to high-odds aesthetic)
st.markdown("""
<style>
    :root {
        --bg:#0b0d12; --surface:#13161e; --surface2:#1a1e28; --border:#252a38;
        --accent:#f0c040; --accent2:#4a9fe8; --text:#e8eaf0; --muted:#6b7590;
        --green:#2ecc71; --red:#e74c3c; --warn:#f39c12;
    }
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-size: 14px;
    }
    .metric-pill {
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-title { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 800; }
    .metric-value { font-size: 24px; font-weight: 900; color: #ffffff; margin-top: 4px; }
    .league-badge {
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 11px; font-weight: 800; text-transform: uppercase;
        background: rgba(41, 151, 255, 0.15); color: var(--accent2);
        border: 1px solid rgba(41, 151, 255, 0.3); margin-bottom: 8px;
    }
    .edge-badge {
        background: rgba(46, 204, 113, 0.15); color: var(--green);
        border: 1px solid rgba(46, 204, 113, 0.3); padding: 3px 10px;
        border-radius: 6px; font-size: 11px; font-weight: 800;
    }
    .reason-box {
        background: rgba(0, 0, 0, 0.35);
        border-left: 3px solid var(--accent2);
        border-radius: 8px;
        padding: 12px 14px;
        color: #d1d1d6;
        font-size: 13.5px;
        line-height: 1.5;
        margin-top: 8px;
        margin-bottom: 12px;
    }
    div.stButton > button {
        background-color: var(--accent) !important; color: #000000 !important;
        border: none !important; border-radius: 8px !important;
        padding: 8px 20px !important; font-weight: 800 !important;
        font-size: 13px !important;
        transition: transform 0.15s ease !important;
    }
    div.stButton > button:hover {
        transform: translateY(-1px) !important;
    }
</style>
""", unsafe_allow_html=True)

# Database Setup
db_file = "bets_tracker_inr.db"
conn = sqlite3.connect(db_file, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, bet_type TEXT,
    details TEXT, odds REAL, stake REAL, status TEXT, profit_loss REAL
)''')
conn.commit()

# Session State for Persistence
if "starting_bankroll" not in st.session_state:
    st.session_state.starting_bankroll = 500
if "unit_inr" not in st.session_state:
    st.session_state.unit_inr = 20
if "logged_bets" not in st.session_state:
    st.session_state.logged_bets = set()

# Top Header & Controls
head_left, head_mid1, head_mid2, head_right = st.columns([2, 1, 1, 1])
with head_left:
    st.markdown("<h1 style='font-size: 28px; font-weight: 900; margin-bottom: 2px; color: #fff;'>Radar 🎯</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--muted); font-size: 12px; margin-bottom: 14px;'>Smart High-Odds + High Probability Terminal</p>", unsafe_allow_html=True)
with head_mid1:
    starting_bankroll = st.number_input("₹ Starting Bankroll", min_value=100, value=st.session_state.starting_bankroll, step=50)
    st.session_state.starting_bankroll = starting_bankroll
with head_mid2:
    unit_inr = st.number_input("₹ Base Stake (1 Unit)", min_value=10, max_value=1000, value=st.session_state.unit_inr, step=10)
    st.session_state.unit_inr = unit_inr
with head_right:
    st.write("")
    if st.button("🔄 Refresh Picks"):
        if os.path.exists("latest_picks.csv"):
            os.remove("latest_picks.csv")
        st.cache_data.clear()
        st.rerun()

@st.cache_data(ttl=1800)
def load_picks():
    return get_value_picks()

df = load_picks()
bets_df = pd.read_sql_query("SELECT * FROM bets ORDER BY id DESC", conn)
settled = bets_df[bets_df["status"] != "Pending"] if not bets_df.empty else pd.DataFrame()
net_pnl_inr = settled["profit_loss"].sum() if not settled.empty else 0.0
current_bankroll = starting_bankroll + net_pnl_inr

# League Filters
selected_league = st.radio(
    "Filter Competition:",
    ["All Competitions", "Champions League", "Premier League", "La Liga"],
    horizontal=True
)

filtered_df = df if selected_league == "All Competitions" else df[df["league"] == selected_league]

# KPI Bento Row
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="metric-pill"><div class="metric-title">Current Bankroll</div><div class="metric-value" style="color:var(--accent2);">₹{current_bankroll:,.0f}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-pill"><div class="metric-title">Available Picks</div><div class="metric-value">{len(filtered_df)}</div></div>', unsafe_allow_html=True)
max_edge = filtered_df["edge"].max() if not filtered_df.empty else 0.0
c3.markdown(f'<div class="metric-pill"><div class="metric-title">Top Value Edge</div><div class="metric-value" style="color:var(--green);">+{max_edge:.1f}%</div></div>', unsafe_allow_html=True)
pnl_color = "var(--green)" if net_pnl_inr >= 0 else "var(--red)"
c4.markdown(f'<div class="metric-pill"><div class="metric-title">Net P&L</div><div class="metric-value" style="color:{pnl_color};">₹{net_pnl_inr:+,.0f}</div></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="metric-pill"><div class="metric-title">Tracked Slips</div><div class="metric-value">{len(bets_df)}</div></div>', unsafe_allow_html=True)

st.write("")
tab1, tab2, tab3, tab4 = st.tabs(["🔥 Best Parlays", "📊 Single Matches", "💰 ₹ P&L Tracker", "🤖 Ask Gemini AI Coach"])

# ================= TAB 1: PARLAYS =================
with tab1:
    picks_list = filtered_df.to_dict("records")
    valid_combos = [
        combo for combo in combinations(picks_list, 2)
        if combo[0]["fixture"] != combo[1]["fixture"]
    ][:4]

    if valid_combos:
        for idx, combo in enumerate(valid_combos):
            comb_odds = round(combo[0]["odds"] * combo[1]["odds"], 2)
            comb_prob = combo[0]["prob"] * combo[1]["prob"]
            comb_ev = round(((comb_prob * comb_odds) - 1.0) * 100, 1)
            stake_units = round(max(0.5, min(2.0, (comb_ev / 12.0))), 1)
            stake_inr = int(stake_units * unit_inr)
            potential_win_inr = int(stake_inr * comb_odds)
            parlay_key = f"Parlay #{idx+1}: {combo[0]['fixture']} + {combo[1]['fixture']}"
            is_logged = parlay_key in st.session_state.logged_bets

            with st.container(border=True):
                col_left, col_right = st.columns([4, 1])
                with col_left:
                    st.markdown(f'<span class="league-badge">2-Match Parlay #{idx+1}</span>', unsafe_allow_html=True)
                    st.markdown(f"<h3 style='font-size:16px; font-weight:800; margin-bottom:4px;'>{combo[0]['fixture']} + {combo[1]['fixture']}</h3>", unsafe_allow_html=True)
                with col_right:
                    st.markdown(f"<div style='text-align:right;'><span style='font-size:24px; font-weight:900; color:var(--accent);'>{comb_odds}×</span><br><span class='edge-badge'>+{comb_ev}% Value</span></div>", unsafe_allow_html=True)

                st.markdown(f"**Leg 1 ({combo[0]['league']}):** {combo[0]['fixture']} $\\rightarrow$ **{combo[0]['market']}** @ `{combo[0]['odds']}`")
                st.markdown(f"<div class='reason-box'>⚽ <b>Insight:</b> {combo[0]['rationale']}</div>", unsafe_allow_html=True)

                st.markdown(f"**Leg 2 ({combo[1]['league']}):** {combo[1]['fixture']} $\\rightarrow$ **{combo[1]['market']}** @ `{combo[1]['odds']}`")
                st.markdown(f"<div class='reason-box'>⚽ <b>Insight:</b> {combo[1]['rationale']}</div>", unsafe_allow_html=True)

                st.markdown(f"**Suggested Bet:** `₹{stake_inr:,}` ({stake_units}u) $\\rightarrow$ **Potential Return:** `₹{potential_win_inr:,}`")

                if is_logged:
                    st.success("✅ Logged to Tracker (Locked)")
                else:
                    if st.button(f"➕ Log Parlay #{idx+1} (₹{stake_inr:,})", key=f"btn_parlay_{idx}"):
                        summary = f"{combo[0]['fixture']} ({combo[0]['market']}) + {combo[1]['fixture']} ({combo[1]['market']})"
                        c.execute("INSERT INTO bets (date, bet_type, details, odds, stake, status, profit_loss) VALUES (?,?,?,?,?,?,?)",
                                  (datetime.now().strftime("%d %b %Y"), "2-Leg Parlay", summary, comb_odds, stake_inr, "Pending", 0.0))
                        conn.commit()
                        st.session_state.logged_bets.add(parlay_key)
                        st.rerun()
    else:
        st.info("No matches found for this filter right now.")

# ================= TAB 2: SINGLES =================
with tab2:
    if picks_list:
        for idx, p in enumerate(picks_list):
            stake_inr = int(p["stake"] * unit_inr)
            potential_win_inr = int(stake_inr * p["odds"])
            risk_tag = "🟢 Low Risk (Bank Builder)" if p["odds"] < 1.70 else ("🟡 Medium Risk (Smart Value)" if p["odds"] < 2.40 else "🔴 High Risk (Punt)")
            single_key = f"Single: {p['fixture']} ({p['market']})"
            is_logged = single_key in st.session_state.logged_bets
            
            with st.container(border=True):
                col_info, col_num = st.columns([4, 1])
                with col_info:
                    st.markdown(f'<span class="league-badge">{p["league"]}</span> &nbsp; <span style="font-size:11px; color:var(--muted)">🏷️ {risk_tag}</span>', unsafe_allow_html=True)
                    st.markdown(f"<h3 style='font-size:16px; font-weight:800; margin-bottom:4px;'>{p['fixture']}</h3>", unsafe_allow_html=True)
                    st.markdown(f"**Pick:** `{p['market']}` @ **{p['odds']}** *(Best price on {p['bookmaker']})*")
                with col_num:
                    st.markdown(f"<div style='text-align:right;'><span class='edge-badge'>+{p['edge']}% Value</span><p style='color:var(--muted); margin-top:6px; font-size:12px;'>Bet: ₹{stake_inr:,}</p></div>", unsafe_allow_html=True)

                st.markdown(f"<div class='reason-box'>⚽ <b>Gemini Tactical Insight:</b> {p['rationale']}</div>", unsafe_allow_html=True)
                st.caption(f"Suggested Stake: **₹{stake_inr:,}** ({p['stake']}u) • Potential Return: **₹{potential_win_inr:,}**")

                if is_logged:
                    st.success("✅ Logged to Tracker (Locked)")
                else:
                    if st.button(f"➕ Log Single: {p['fixture']} (₹{stake_inr:,})", key=f"btn_single_{idx}"):
                        c.execute("INSERT INTO bets (date, bet_type, details, odds, stake, status, profit_loss) VALUES (?,?,?,?,?,?,?)",
                                  (datetime.now().strftime("%d %b %Y"), "Single", f"{p['fixture']} ({p['market']})", p['odds'], stake_inr, "Pending", 0.0))
                        conn.commit()
                        st.session_state.logged_bets.add(single_key)
                        st.rerun()
    else:
        st.info("No single picks currently active for this competition.")

# ================= TAB 3: ₹ P&L TRACKER =================
with tab3:
    st.subheader("Your ₹ INR Bet Slip Ledger")
    if not bets_df.empty:
        for _, row in bets_df.iterrows():
            with st.container(border=True):
                colA, colB, colC = st.columns([5, 2, 2])
                colA.markdown(f"**{row['date']} • {row['bet_type']}**  \n{row['details']}")
                colB.markdown(f"Odds: **{row['odds']}x**  \nStaked: **₹{row['stake']:,.0f}**")
                if row["status"] == "Pending":
                    res = colC.selectbox("Result", ["Pending", "Won", "Lost", "Void"], key=f"set_{row['id']}")
                    if res != "Pending":
                        pnl = round(row["stake"] * (row["odds"] - 1), 0) if res == "Won" else (-row["stake"] if res == "Lost" else 0.0)
                        c.execute("UPDATE bets SET status=?, profit_loss=? WHERE id=?", (res, pnl, row["id"]))
                        conn.commit()
                        st.rerun()
                else:
                    color = "var(--green)" if row["status"] == "Won" else ("var(--red)" if row["status"] == "Lost" else "var(--muted)")
                    colC.markdown(f"<span style='color:{color}; font-weight:800;'>{row['status']}</span><br>**₹{row['profit_loss']:+,.0f}**", unsafe_allow_html=True)
    else:
        st.info("No bets logged yet! Click '➕ Log Single' or '➕ Log Parlay' to track your bankroll.")

# ================= TAB 4: GEMINI AI CHAT COACH =================
with tab4:
    st.subheader("🤖 Ask Your Gemini Football Betting Coach")
    st.write("Have a question about a fixture, team news, or whether a bet is worth taking? Ask Gemini right here!")

    user_query = st.text_input("Ask Gemini anything about tonight's matches or betting strategy:", placeholder="e.g., Is Real Madrid missing key players tonight?")
    if user_query:
        import requests
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            st.error("Gemini API key not found in Streamlit Secrets!")
        else:
            with st.spinner("Gemini is analyzing team tactics and stats..."):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                prompt = f"You are a friendly expert football betting analyst talking to an Indian football fan. Answer this question concisely and practically in under 60 words: {user_query}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                try:
                    res = requests.post(url, json=payload, timeout=10)
                    if res.status_code == 200:
                        ans = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        st.markdown(f"<div class='reason-box'>🤖 <b>Gemini Coach:</b> {ans}</div>", unsafe_allow_html=True)
                    else:
                        st.error("Could not reach Gemini API. Check your key.")
                except Exception as e:
                    st.error(f"Error: {e}")
