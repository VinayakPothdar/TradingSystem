"""
Swing Intelligence Mobile Web App:
- Live Scanner: 50 DEMA (₹1k risk) and 200 EMA (₹2k risk)
- Grade A+ (Confirmed Higher-Low) vs Grade A (First-Touch Base)
- EMA Respect Score & GTT Copy Cards
- Underlying Sector Name & Sector EMA Position
- Backtesting Hub: 8.5-year simulation, equity curves, trade logs
- Gatekeeper: Macro market & Sectoral regime scoring
"""

import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from engine.backtester import run_full_backtest
from engine.config import STRATEGIES, StrategyConfig
from engine.data import load_all_candles
from engine.gatekeeper import compute_gatekeeper_score, get_all_sector_regimes
from engine.scanner import export_scan_to_json, run_full_scan
from engine.telegram import format_telegram_digest, send_telegram_message

# Page Configuration for Mobile
st.set_page_config(
    page_title="Swing Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling for Mobile Dark Theme
st.markdown(
    """
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 10px; }
    .setup-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .badge-a-plus {
        background-color: #238636;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 600;
    }
    .badge-a {
        background-color: #d29922;
        color: black;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 600;
    }
    .badge-respect {
        background-color: #1f6feb;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8em;
    }
    .badge-sector {
        background-color: #21262d;
        color: #e6edf3;
        border: 1px solid #30363d;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 0.8em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def get_cached_candles():
    return load_all_candles()


@st.cache_data(ttl=1800)
def get_market_regime(df_all):
    indices_dict = {}
    for sym in ["^NSEI", "^NSMIDCP", "^NSEBANK", "^INDIAVIX"]:
        sub_df = df_all[df_all["Symbol"] == sym.replace("^", "")]
        if sub_df.empty:
            sub_df = df_all[df_all["Symbol"] == sym]
        if not sub_df.empty:
            indices_dict[sym] = sub_df.sort_values("Date").reset_index(drop=True)
    return compute_gatekeeper_score(indices_dict)


# --- MAIN APP HEADER ---
df_all = get_cached_candles()
gatekeeper = get_market_regime(df_all)
sector_regimes = get_all_sector_regimes(df_all)

st.title("📈 Swing Intelligence")
st.caption(f"Institutional ATH & DEMA Swing System • {gatekeeper.headline}")

# Metric Banner
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Gatekeeper Score", f"{gatekeeper.score}/10", delta=gatekeeper.status)
with c2:
    st.metric("50 DEMA Risk (1R)", "₹1,000", help="High-momentum swing sizing")
with c3:
    st.metric("200 EMA Risk (1R)", "₹2,000", help="Deep-value mean-reversion sizing")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["🔍 Live Scanner", "📈 Backtesting Hub", "🛡️ Sector Gatekeeper"])

# ==========================================
# TAB 1: LIVE SCANNER
# ==========================================
with tab1:
    st.subheader("Upcoming Setups (EOD & On-Demand)")

    # Controls
    col_ctrl1, col_ctrl2 = st.columns([1, 1])
    with col_ctrl1:
        selected_strategy = st.selectbox(
            "Strategy Filter",
            options=["COMBINED", "50_DEMA", "200_EMA"],
            format_func=lambda x: "All Strategies (50 & 200)" if x == "COMBINED" else STRATEGIES[x].name,
        )
    with col_ctrl2:
        grade_filter = st.radio(
            "Quality Filter",
            options=["ALL", "APLUS_ONLY"],
            format_func=lambda x: "All Valid Setups" if x == "ALL" else "⭐ Confirmed Higher-Low (A+) Only",
            horizontal=True,
        )

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        run_scan_btn = st.button("🚀 Run Live Scan Now", use_container_width=True, type="primary")
    with col_btn2:
        send_tg = st.checkbox("📱 Also Push to Telegram", value=False)

    # State management for scan results
    if "scan_results" not in st.session_state or run_scan_btn:
        with st.spinner("Scanning Nifty 500 stocks across True ATH, DEMA pullbacks & Sectors..."):
            strat_arg = None if selected_strategy == "COMBINED" else selected_strategy
            raw_results = run_full_scan(df_all, strategy_id=strat_arg)
            st.session_state["scan_results"] = raw_results

            if send_tg and raw_results:
                msg = format_telegram_digest(raw_results, gatekeeper)
                send_telegram_message(msg)
                st.success("Alert sent to Telegram!")

    results = st.session_state.get("scan_results", [])

    # Apply Grade filter
    if grade_filter == "APLUS_ONLY":
        results = [r for r in results if r.grade == "A+"]

    st.write(f"**Found {len(results)} qualifying setups:**")

    if not results:
        st.info("No stocks currently match the setup criteria. Market may be extended or in consolidation.")
    else:
        for r in results:
            badge_class = "badge-a-plus" if r.grade == "A+" else "badge-a"
            strat_label = "50 DEMA (₹1k)" if r.strategy_id == "50_DEMA" else "200 EMA (₹2k)"

            gtt_text = (
                f"DHAN GTT ORDER:\n"
                f"Symbol: {r.symbol}\n"
                f"Sector: {r.industry} ({r.sector_name})\n"
                f"Trigger Price: ₹{r.entry_price}\n"
                f"Limit Price: ₹{round(r.entry_price * 1.003, 2)}\n"
                f"Stop-Loss: ₹{r.stop_loss_price}\n"
                f"Quantity: {r.quantity}\n"
                f"Target (+2R): ₹{r.target_price}"
            )

            st.markdown(
                f"""
                <div class="setup-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <div>
                            <span style="font-size: 1.3em; font-weight: bold; color: #58a6ff;">{r.symbol}</span>
                            <span style="color: #8b949e; font-size: 0.9em; margin-left: 6px;">• <b>{r.industry}</b> ({r.sector_name})</span>
                        </div>
                        <div>
                            <span class="{badge_class}">{r.grade} {r.setup_type}</span>
                            <span class="badge-respect">EMA Respect: {r.respect_score_pct}%</span>
                        </div>
                    </div>
                    <div style="font-size: 0.88em; color: #8b949e; margin-bottom: 10px;">
                        Sector EMA: <b>{r.sector_status_label}</b> • Strategy: <b>{strat_label}</b> • Pattern: <i>{r.pattern_summary}</i>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; margin-bottom: 12px;">
                        <div><b>Buy (Stop-Limit):</b> ₹{r.entry_price:,.2f}</div>
                        <div><b>Stop-Loss:</b> ₹{r.stop_loss_price:,.2f} ({r.risk_pct:.1f}%)</div>
                        <div><b>1R Sizing:</b> <span style="color: #3fb950; font-weight: bold;">{r.quantity} shares</span></div>
                        <div><b>Total Risk:</b> ₹{r.actual_risk_amount:,.0f}</div>
                        <div><b>BE Trigger (+1.5R):</b> ₹{r.breakeven_trigger_price:,.2f}</div>
                        <div><b>Target (+2.0R):</b> ₹{r.target_price:,.2f}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander(f"📋 Copy GTT Parameters for {r.symbol}"):
                st.code(gtt_text, language="text")

# ==========================================
# TAB 2: BACKTESTING HUB
# ==========================================
with tab2:
    st.subheader("8.5-Year Systematic Simulation Hub")
    st.caption("2018 – Present • 50 DEMA (₹1k Risk) vs 200 EMA (₹2k Risk)")

    bt_strat = st.selectbox(
        "Select Backtest Strategy",
        options=["COMBINED", "50_DEMA", "200_EMA"],
        format_func=lambda x: "Combined Portfolio (50 DEMA + 200 EMA)" if x == "COMBINED" else STRATEGIES[x].name,
        key="bt_strat_select",
    )

    if st.button("🔄 Run Backtest Simulation", type="primary", use_container_width=True):
        with st.spinner("Simulating multi-stock trades across 8.5 years of historical candles..."):
            summary, trades_df = run_full_backtest(df_all, strategy_id=bt_strat)
            st.session_state["bt_summary"] = summary
            st.session_state["bt_trades"] = trades_df

    if st.session_state.get("bt_summary"):
        s = st.session_state["bt_summary"]
        t = st.session_state["bt_trades"]

        # KPI Metrics
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Trades", s.total_trades)
        with m2:
            st.metric("Win Rate", f"{s.win_rate_pct}%", delta=f"{s.winning_trades}W / {s.losing_trades}L")
        with m3:
            st.metric("Net Realized R", f"+{s.net_r:,.1f} R", delta=f"₹{s.net_pnl:,.0f}")
        with m4:
            st.metric("Profit Factor", f"{s.profit_factor}", delta=f"Max DD: {s.max_drawdown_r}R")

        # Equity Curve Chart
        st.markdown("### Cumulative Performance (Equity Curve)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t["ExitDate"], y=t["CumR"], mode="lines", name="Cumulative R", line=dict(color="#3fb950", width=2)))
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_title="Date",
            yaxis_title="Realized R-Multiple",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Trade Log Table
        st.markdown("### Historical Trade Log")
        search_sym = st.text_input("Filter by Symbol (e.g. HAL, DIXON, RELIANCE)", "").strip().upper()
        display_df = t if not search_sym else t[t["Symbol"].str.contains(search_sym)]
        st.dataframe(
            display_df[["Symbol", "Strategy", "Grade", "EntryDate", "EntryPrice", "ExitDate", "ExitPrice", "Quantity", "RealizedR", "RealizedPnL", "ExitReason"]],
            use_container_width=True,
            height=350,
        )
    else:
        st.info("Click 'Run Backtest Simulation' above to simulate 8.5 years of trades in real-time.")

# ==========================================
# TAB 3: SECTOR GATEKEEPER
# ==========================================
with tab3:
    st.subheader("Market & Sector Regime Gatekeeper")
    st.markdown(f"### Overall Recommendation: **{gatekeeper.status}**")
    st.write(gatekeeper.headline)

    st.markdown("#### Broad Market Indices")
    for name, stat in gatekeeper.regime_breakdown.items():
        state_color = "🟢" if stat.trend_state == "BULLISH" else ("🟡" if stat.trend_state == "CAUTION" else "🔴")
        st.markdown(
            f"""
            <div class="setup-card">
                <b>{state_color} {name}</b> ({stat.symbol})<br>
                Close: ₹{stat.close:,.2f} • 50 DEMA: ₹{stat.dema_50:,.2f} ({stat.pct_from_50_dema:+.1f}%) • 200 EMA: ₹{stat.ema_200:,.2f} ({stat.pct_from_200_ema:+.1f}%)<br>
                State: <b>{stat.trend_state}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### All Sectoral Indices (50 DEMA Health)")
    for ticker, stat in sector_regimes.items():
        state_color = "🟢" if stat.is_above_50_dema else ("🟡" if stat.is_above_200_ema else "🔴")
        st.markdown(
            f"""
            <div style="background-color: #161b22; border-left: 4px solid {'#238636' if stat.is_above_50_dema else '#da3633'}; padding: 8px 12px; margin-bottom: 6px; border-radius: 4px;">
                <b>{state_color} {stat.index_name}</b> ({ticker}): {stat.pct_from_50_dema:+.1f}% vs 50 DEMA • {stat.pct_from_200_ema:+.1f}% vs 200 EMA
            </div>
            """,
            unsafe_allow_html=True,
        )
