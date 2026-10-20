import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from itertools import combinations
from engine import get_value_picks

st.set_page_config(page_title="Radar • Matchday Terminal", page_icon="⚽", layout="wide")

if "ODDS_API_KEY" in st.secrets:
    os.environ["ODDS_API_KEY"] = st.secrets["ODDS_API_KEY"]
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif !important;
        background-color: #0b0c10 !important;
        color: #f5f5f7 !important;
    }
    .bento-card {
        background: rgba(26, 27, 34, 0.72);
        backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 24px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    }
    .metric-pill {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.07);
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
        border: 1px solid rgba(41, 151, 255, 0.3); margin-bottom: 10px;
    }
    .edge-badge {
        background: rgba(48, 209, 88, 0.15); color: #30d158;
        border: 1px solid rgba(48, 209, 88, 0.3); padding: 4px 10px;
        border-radius: 100px; font-size: 12px; font-weight: 600;
    }
    .rationale-text {
        color: #a1a1a6; font-size: 14px; line-height: 1.5;
        margin-top: 8px; padding-left: 12px;
        border-left: 2px solid rgba(255, 255, 255, 0.15);
    }
    div.stButton > button {
        background-color: #0071e3 !important; color: #ffffff !important;
        border: none !important; border-radius: 100px !important;
        padding: 8px 22px !important; font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

conn = sqlite3.connect("bets_tracker.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, bet_type TEXT,
    details TEXT, odds REAL, stake REAL, status TEXT, profit_loss REAL
)''')
conn.commit()

st.markdown("<h1 style='font-size: 36px; font-weight: 700; margin-bottom: 4px;'>Radar</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #86868b; margin-bottom: 24px;'>Automated +EV Football Intelligence • PL, La Liga, UCL</p>", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_picks():
    if os.path.exists("latest_picks.csv"):
        df_csv = pd.read_csv("latest_picks.csv")
        if not df_csv.empty:
            return df_csv
    return get_value_picks()

df = load_picks()
bets_df = pd.read_sql_query("SELECT * FROM bets ORDER BY id DESC", conn)
settled = bets_df[bets_df["status"] != "Pending"] if not bets_df.empty else pd.DataFrame()
net_pnl = settled["profit_loss"].sum() if not settled.empty else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="metric-pill"><div class="metric-title">Active Picks</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-pill"><div class="metric-title">Max EV Edge</div><div class="metric-value" style="color:#30d158;">+{df["edge"].max():.1f}%</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-pill"><div class="metric-title">Realized P&L</div><div class="metric-value" style="color:#2997ff;">{net_pnl:+.2f}u</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-pill"><div class="metric-title">Tracked Slips</div><div class="metric-value">{len(bets_df)}</div></div>', unsafe_allow_html=True)

st.write("")
tab1, tab2, tab3 = st.tabs(["🔥 Recommended Parlays", "📊 Single Value Bets", "💰 P&L & Bankroll Tracker"])

with tab1:
    picks_list = df.to_dict("records")
    if len(picks_list) >= 2:
        for idx, combo in enumerate(list(combinations(picks_list, 2))[:3]):
            comb_odds = round(combo[0]["odds"] * combo[1]["odds"], 2)
            comb_prob = combo[0]["prob"] * combo[1]["prob"]
            comb_ev = round(((comb_prob * comb_odds) - 1.0) * 100, 1)
            stake = round(max(0.5, min(2.5, (comb_ev / 10.0))), 1)

            st.markdown(f"""
            <div class="bento-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                    <div>
                        <span class="league-badge">2-Leg Value Acca #{idx+1}</span>
                        <h3 style="margin:0;">{combo[0]['fixture']} + {combo[1]['fixture']}</h3>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:28px; font-weight:700;">{comb_odds}x</span><br>
                        <span class="edge-badge">+{comb_ev}% EV</span>
                    </div>
                </div>
                <div style="background:rgba(0,0,0,0.28); border-radius:16px; padding:14px; margin-bottom:10px;">
                    <strong>Leg 1: [{combo[0]['league']}] {combo[0]['fixture']}</strong> — <span style="color:#2997ff;">{combo[0]['market']} @ {combo[0]['odds']}</span> ({combo[0]['bookmaker']})
                    <div class="rationale-text">💡 {combo[0]['rationale']}</div>
                </div>
                <div style="background:rgba(0,0,0,0.28); border-radius:16px; padding:14px; margin-bottom:12px;">
                    <strong>Leg 2: [{combo[1]['league']}] {combo[1]['fixture']}</strong> — <span style="color:#2997ff;">{combo[1]['market']} @ {combo[1]['odds']}</span> ({combo[1]['bookmaker']})
                    <div class="rationale-text">💡 {combo[1]['rationale']}</div>
                </div>
                <span style="font-size:13px; color:#86868b;">Recommended Kelly Stake: <strong style="color:#fff;">{stake} Units</strong></span>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Log Parlay #{idx+1} to Tracker", key=f"p_{idx}"):
                summary = f"{combo[0]['fixture']} ({combo[0]['market']}) + {combo[1]['fixture']} ({combo[1]['market']})"
                c.execute("INSERT INTO bets (date, bet_type, details, odds, stake, status, profit_loss) VALUES (?,?,?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d"), "2-Leg Parlay", summary, comb_odds, stake, "Pending", 0.0))
                conn.commit()
                st.rerun()

with tab2:
    for idx, p in enumerate(picks_list):
        st.markdown(f"""
        <div class="bento-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="league-badge">{p['league']}</span>
                    <h3 style="margin:2px 0;">{p['fixture']}</h3>
                    <span style="color:#2997ff; font-weight:600;">{p['market']} @ {p['odds']} ({p['bookmaker']})</span>
                </div>
                <div style="text-align:right;">
                    <span class="edge-badge">+{p['edge']}% EV</span>
                    <p style="color:#86868b; font-size:12px; margin-top:6px;">Stake: {p['stake']}u</p>
                </div>
            </div>
            <div class="rationale-text">💡 {p['rationale']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Log Single: {p['fixture']}", key=f"s_{idx}"):
            c.execute("INSERT INTO bets (date, bet_type, details, odds, stake, status, profit_loss) VALUES (?,?,?,?,?,?,?)",
                      (datetime.now().strftime("%Y-%m-%d"), "Single", f"{p['fixture']} ({p['market']})", p['odds'], p['stake'], "Pending", 0.0))
            conn.commit()
            st.rerun()

with tab3:
    if not bets_df.empty:
        for _, row in bets_df.iterrows():
            colA, colB, colC = st.columns([5, 2, 2])
            colA.markdown(f"**{row['date']} • {row['bet_type']}**  \n{row['details']}")
            colB.markdown(f"**{row['odds']}x** (`{row['stake']}u`)")
            if row["status"] == "Pending":
                res = colC.selectbox("Settle", ["Pending", "Won", "Lost", "Void"], key=f"set_{row['id']}")
                if res != "Pending":
                    pnl = round(row["stake"] * (row["odds"] - 1), 2) if res == "Won" else (-row["stake"] if res == "Lost" else 0.0)
                    c.execute("UPDATE bets SET status=?, profit_loss=? WHERE id=?", (res, pnl, row["id"]))
                    conn.commit()
                    st.rerun()
            else:
                colC.markdown(f"**{row['status']}** (`{row['profit_loss']:+.2f}u`)")
            st.divider()
    else:
        st.info("No bets logged yet. Click 'Log to Tracker' on any parlay or single pick.")
