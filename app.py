import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from itertools import combinations
from engine import get_value_picks, generate_ai_tactical_rationale

st.set_page_config(page_title="Radar • Matchday Terminal", page_icon="⚽", layout="wide")

# Connect Secrets
if "ODDS_API_KEY" in st.secrets:
    os.environ["ODDS_API_KEY"] = st.secrets["ODDS_API_KEY"]
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

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
    .metric-value { font-size: 26px; font-weight: 700; color: #ffffff; margin-top: 4px; }
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
        padding: 10px 14px;
        color: #d1d1d6;
        font-size: 14px;
        line-height: 1.5;
        margin-top: 8px;
        margin-bottom: 12px;
    }
    div.stButton > button {
        background-color: #0071e3 !important; color: #ffffff !important;
        border: none !important; border-radius: 100px !important;
        padding: 8px 24px !important; font-weight: 600 !important;
        transition: 0.2s ease !important;
    }
    div.stButton > button:hover {
        background-color: #0077ed !important;
        transform: scale(1.02) !important;
    }
</style>
""", unsafe_allow_html=True)

# Database Setup
conn = sqlite3.connect("bets_tracker.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, bet_type TEXT,
    details TEXT, odds REAL, stake REAL, status TEXT, profit_loss REAL
)''')
conn.commit()

st.markdown("<h1 style='font-size: 34px; font-weight: 700; margin-bottom: 2px;'>Radar</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #86868b; margin-bottom: 22px;'>Automated +EV Football Intelligence & Bankroll Manager</p>", unsafe_allow_html=True)

@st.cache_data(ttl=1800)
def load_picks():
    if os.path.exists("latest_picks.csv"):
        try:
            df_csv = pd.read_csv("latest_picks.csv")
            if not df_csv.empty:
                return df_csv
        except Exception:
            pass
    return get_value_picks()

df = load_picks()
bets_df = pd.read_sql_query("SELECT * FROM bets ORDER BY id DESC", conn)
settled = bets_df[bets_df["status"] != "Pending"] if not bets_df.empty else pd.DataFrame()
net_pnl = settled["profit_loss"].sum() if not settled.empty else 0.0

# KPI Bento Row
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="metric-pill"><div class="metric-title">Active Value Picks</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-pill"><div class="metric-title">Top Value Edge</div><div class="metric-value" style="color:#30d158;">+{df["edge"].max():.1f}%</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-pill"><div class="metric-title">Realized Bankroll</div><div class="metric-value" style="color:#2997ff;">{net_pnl:+.2f}u</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-pill"><div class="metric-title">Tracked Bets</div><div class="metric-value">{len(bets_df)}</div></div>', unsafe_allow_html=True)

st.write("")
tab1, tab2, tab3 = st.tabs(["🔥 Recommended Parlays", "📊 Single Value Bets", "💰 P&L & Bankroll Tracker"])

# ================= TAB 1: PARLAYS =================
with tab1:
    picks_list = df.to_dict("records")
    if len(picks_list) >= 2:
        for idx, combo in enumerate(list(combinations(picks_list, 2))[:3]):
            comb_odds = round(combo[0]["odds"] * combo[1]["odds"], 2)
            comb_prob = combo[0]["prob"] * combo[1]["prob"]
            comb_ev = round(((comb_prob * comb_odds) - 1.0) * 100, 1)
            stake = round(max(0.5, min(2.5, (comb_ev / 10.0))), 1)

            with st.container(border=True):
                col_left, col_right = st.columns([4, 1])
                with col_left:
                    st.markdown(f'<span class="league-badge">2-Leg Value Acca #{idx+1}</span>', unsafe_allow_html=True)
                    st.subheader(f"{combo[0]['fixture']} + {combo[1]['fixture']}")
                with col_right:
                    st.markdown(f"<div style='text-align:right;'><span style='font-size:26px; font-weight:700;'>{comb_odds}x</span><br><span class='edge-badge'>+{comb_ev}% EV</span></div>", unsafe_allow_html=True)

                st.markdown(f"**Leg 1:** `{combo[0]['league']}` — **{combo[0]['fixture']}** (`{combo[0]['market']}` @ {combo[0]['odds']})")
                st.markdown(f"<div class='reason-box'>💡 <b>Why this leg:</b> {combo[0]['rationale']}</div>", unsafe_allow_html=True)

                st.markdown(f"**Leg 2:** `{combo[1]['league']}` — **{combo[1]['fixture']}** (`{combo[1]['market']}` @ {combo[1]['odds']})")
                st.markdown(f"<div class='reason-box'>💡 <b>Why this leg:</b> {combo[1]['rationale']}</div>", unsafe_allow_html=True)

                st.caption(f"Suggested Allocation: **{stake} Units**")

                if st.button(f"Log Parlay #{idx+1} to Tracker", key=f"btn_parlay_{idx}"):
                    summary = f"{combo[0]['fixture']} ({combo[0]['market']}) + {combo[1]['fixture']} ({combo[1]['market']})"
                    c.execute("INSERT INTO bets (date, bet_type, details, odds, stake, status, profit_loss) VALUES (?,?,?,?,?,?,?)",
                              (datetime.now().strftime("%Y-%m-%d"), "2-Leg Parlay", summary, comb_odds, stake, "Pending", 0.0))
                    conn.commit()
                    st.success("✅ Logged Parlay to Tracker!")
                    st.rerun()

# ================= TAB 2: SINGLES =================
with tab2:
    for idx, p in enumerate(picks_list):
        with st.container(border=True):
            col_info, col_num = st.columns([4, 1])
            with col_info:
                st.markdown(f'<span class="league-badge">{p["league"]}</span>', unsafe_allow_html=True)
                st.markdown(f"### {p['fixture']}")
                st.markdown(f"**Market:** `{p['market']}` @ **{p['odds']}** (Bookmaker: {p['bookmaker']})")
            with col_num:
                st.markdown(f"<div style='text-align:right;'><span class='edge-badge'>+{p['edge']}% EV</span><p style='color:#86868b; margin-top:6px;'>Stake: {p['stake']}u</p></div>", unsafe_allow_html=True)

            st.markdown(f"<div class='reason-box'>💡 <b>Why this bet:</b> {p['rationale']}</div>", unsafe_allow_html=True)

            if st.button(f"Log Bet: {p['fixture']}", key=f"btn_single_{idx}"):
                c.execute("INSERT INTO bets (date, bet_type, details, odds, stake, status, profit_loss) VALUES (?,?,?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d"), "Single", f"{p['fixture']} ({p['market']})", p['odds'], p['stake'], "Pending", 0.0))
                conn.commit()
                st.success("✅ Logged Single to Tracker!")
                st.rerun()

# ================= TAB 3: TRACKER =================
with tab3:
    st.subheader("Your Bet Slip Ledger")
    if not bets_df.empty:
        for _, row in bets_df.iterrows():
            with st.container(border=True):
                colA, colB, colC = st.columns([5, 2, 2])
                colA.markdown(f"**{row['date']} • {row['bet_type']}**  \n{row['details']}")
                colB.markdown(f"**{row['odds']}x** (`{row['stake']}u staked`)")
                if row["status"] == "Pending":
                    res = colC.selectbox("Settle Result", ["Pending", "Won", "Lost", "Void"], key=f"set_{row['id']}")
                    if res != "Pending":
                        pnl = round(row["stake"] * (row["odds"] - 1), 2) if res == "Won" else (-row["stake"] if res == "Lost" else 0.0)
                        c.execute("UPDATE bets SET status=?, profit_loss=? WHERE id=?", (res, pnl, row["id"]))
                        conn.commit()
                        st.rerun()
                else:
                    color = "green" if row["status"] == "Won" else ("red" if row["status"] == "Lost" else "gray")
                    colC.markdown(f":{color}[**{row['status']}**] ({row['profit_loss']:+.2f}u)")
    else:
        st.info("No bets logged yet. Click 'Log to Tracker' on any parlay or single.")
