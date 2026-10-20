import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from itertools import combinations

st.set_page_config(page_title="Radar • Matchday Terminal", page_icon="⚽", layout="wide")

# Load secrets BEFORE running engine functions
if "ODDS_API_KEY" in st.secrets:
    os.environ["ODDS_API_KEY"] = st.secrets["ODDS_API_KEY"]
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

from engine import get_value_picks

# Apple Bento Dark Styling
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif !important;
        background-color: #0b0c10 !important;
        color: #f5f5f7 !important;
    }
    .metric-pill {
        background: rgba(26, 27, 34, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-title { font-size: 12px; color: #86868b; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { font-size: 24px; font-weight: 700; color: #ffffff; margin-top: 4px; }
    .league-badge {
        display: inline-block; padding: 4px 12px; border-radius: 100px;
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        background: rgba(0, 113, 227, 0.15); color: #2997ff;
        border: 1px solid rgba(41, 151, 255, 0.3); margin-bottom: 8px;
    }
    .edge-badge {
        background: rgba(48, 209, 88, 0.15); color: #30d158;
        border: 1px solid rgba(48, 209, 88, 0.3); padding: 4px 10px;
        border-radius: 100px; font-size: 12px; font-weight: 600;
    }
    .reason-box {
        background: rgba(0, 0, 0, 0.35);
        border-left: 3px solid #2997ff;
        border-radius: 8px;
        padding: 12px 14px;
        color: #e5e5ea;
        font-size: 14.5px;
        line-height: 1.5;
        margin-top: 8px;
        margin-bottom: 12px;
    }
    div.stButton > button {
        background-color: #0071e3 !important; color: #ffffff !important;
        border: none !important; border-radius: 100px !important;
        padding: 8px 24px !important; font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# Database Setup
conn = sqlite3.connect("bets_tracker_inr.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, bet_type TEXT,
    details TEXT, odds REAL, stake REAL, status TEXT, profit_loss REAL
)''')
conn.commit()

# Top Header & Bankroll Controls
head_left, head_mid1, head_mid2, head_right = st.columns([2, 1, 1, 1])
with head_left:
    st.markdown("<h1 style='font-size: 32px; font-weight: 700; margin-bottom: 2px;'>Radar</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #86868b; margin-bottom: 14px;'>AI Football Terminal & ₹ Bankroll Manager</p>", unsafe_allow_html=True)
with head_mid1:
    starting_bankroll = st.number_input("₹ Starting Bankroll", min_value=1000, value=25000, step=1000)
with head_mid2:
    unit_inr = st.number_input("₹ Base Stake (1 Unit)", min_value=100, max_value=10000, value=500, step=100)
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

# League Filter Pills
selected_league = st.radio(
    "Filter Competition:",
    ["All Competitions", "Champions League", "Premier League", "La Liga"],
    horizontal=True
)

filtered_df = df if selected_league == "All Competitions" else df[df["league"] == selected_league]

# KPI Bento Row (Now includes Current Bankroll)
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="metric-pill"><div class="metric-title">Current Bankroll</div><div class="metric-value" style="color:#2997ff;">₹{current_bankroll:,.0f}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-pill"><div class="metric-title">Available Picks</div><div class="metric-value">{len(filtered_df)}</div></div>', unsafe_allow_html=True)
max_edge = filtered_df["edge"].max() if not filtered_df.empty else 0.0
c3.markdown(f'<div class="metric-pill"><div class="metric-title">Top Value Edge</div><div class="metric-value" style="color:#30d158;">+{max_edge:.1f}%</div></div>', unsafe_allow_html=True)
pnl_color = "#30d158" if net_pnl_inr >= 0 else "#ff453a"
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

            with st.container(border=True):
                col_left, col_right = st.columns([4, 1])
                with col_left:
                    st.markdown(f'<span class="league-badge">2-Match Parlay #{idx+1}</span>', unsafe_allow_html=True)
                    st.subheader(f"{combo[0]['fixture']} + {combo[1]['fixture']}")
                with col_right:
                    st.markdown(f"<div style='text-align:right;'><span style='font-size:26px; font-weight:700;'>{comb_odds}x</span><br><span class='edge-badge'>+{comb_ev}% Value</span></div>", unsafe_allow_html=True)

                st.markdown(f"**Leg 1 ({combo[0]['league']}):** {combo[0]['fixture']} $\\rightarrow$ **{combo[0]['market']}** @ `{combo[0]['odds']}`")
                st.markdown(f"<div class='reason-box'>⚽ <b>Insight:</b> {combo[0]['rationale']}</div>", unsafe_allow_html=True)

                st.markdown(f"**Leg 2 ({combo[1]['league']}):** {combo[1]['fixture']} $\\rightarrow$ **{combo[1]['market']}** @ `{combo[1]['odds']}`")
                st.markdown(f"<div class='reason-box'>⚽ <b>Insight:</b> {combo[1]['rationale']}</div>", unsafe_allow_html=True)

                st.markdown(f"**Suggested Bet:** `₹{stake_inr:,}` ({stake_units}u) $\\rightarrow$ **Potential Return:** `₹{potential_win_inr:,}`")

                if st.button(f"➕ Log Parlay #{idx+1} (₹{stake_inr:,})", key=f"btn_parlay_{idx}"):
                    summary = f"{combo[0]['fixture']} ({combo[0]['market']}) + {combo[1]['fixture']} ({combo[1]['market']})"
                    c.execute("INSERT INTO bets (date, bet_type, details, odds, stake, status, profit_loss) VALUES (?,?,?,?,?,?,?)",
                              (datetime.now().strftime("%d %b %Y"), "2-Leg Parlay", summary, comb_odds, stake_inr, "Pending", 0.0))
                    conn.commit()
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
            
            with st.container(border=True):
                col_info, col_num = st.columns([4, 1])
                with col_info:
                    st.markdown(f'<span class="league-badge">{p["league"]}</span> &nbsp; `🏷️ {risk_tag}`', unsafe_allow_html=True)
                    st.markdown(f"### {p['fixture']}")
                    st.markdown(f"**Pick:** `{p['market']}` @ **{p['odds']}** *(Best price on {p['bookmaker']})*")
                with col_num:
                    st.markdown(f"<div style='text-align:right;'><span class='edge-badge'>+{p['edge']}% Value</span><p style='color:#86868b; margin-top:6px;'>Bet: ₹{stake_inr:,}</p></div>", unsafe_allow_html=True)

                st.markdown(f"<div class='reason-box'>⚽ <b>Gemini Tactical Insight:</b> {p['rationale']}</div>", unsafe_allow_html=True)
                st.caption(f"Suggested Stake: **₹{stake_inr:,}** ({p['stake']}u) • Potential Return: **₹{potential_win_inr:,}**")

                if st.button(f"➕ Log Single: {p['fixture']} (₹{stake_inr:,})", key=f"btn_single_{idx}"):
                    c.execute("INSERT INTO bets (date, bet_type, details, odds, stake, status, profit_loss) VALUES (?,?,?,?,?,?,?)",
                              (datetime.now().strftime("%d %b %Y"), "Single", f"{p['fixture']} ({p['market']})", p['odds'], stake_inr, "Pending", 0.0))
                    conn.commit()
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
                    color = "green" if row["status"] == "Won" else ("red" if row["status"] == "Lost" else "gray")
                    colC.markdown(f":{color}[**{row['status']}**]  \n**₹{row['profit_loss']:+,.0f}**")
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
