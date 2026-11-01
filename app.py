"""
AVP Swing Intelligence — Modern Quantitative Trading Terminal
Clean, High-Contrast UI optimized for Mobile and Desktop.
- Top 3 Sector Leaders & Full Sector Radar (Above/Below 50 DEMA)
- Minimalist Header with Gatekeeper Market Regime
- Live Scanner: 50 DEMA (₹1k Risk) & 200 EMA (₹2k Risk)
- Grade A+ (Confirmed Higher-Low) vs Grade A (First-Touch Base)
- EMA Respect Scores & 1-Tap GTT Copy Cards
- Backtesting Hub: 8.5-Year Systematic Simulation
"""

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine.backtester import run_full_backtest
from engine.config import STRATEGIES, StrategyConfig
from engine.data import load_all_candles
from engine.gatekeeper import (
    compute_gatekeeper_score,
    get_all_sector_regimes,
    get_sector_leaderboard,
)
from engine.scanner import export_scan_to_json, run_full_scan
from engine.telegram import format_telegram_digest, send_telegram_message

APP_VERSION = "3.0"

st.set_page_config(
    page_title="AVP Swing Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Invalidate stale sessions across updates
if st.session_state.get("app_version") != APP_VERSION:
    st.session_state.clear()
    st.session_state["app_version"] = APP_VERSION

# High-Contrast Modern Dark Theme CSS
st.markdown(
    """
    <style>
    /* Dark Obsidian Background */
    .stApp {
        background-color: #080C14;
        color: #F1F5F9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Clean Top Header Bar */
    .top-header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0px 8px 0px;
        border-bottom: 1px solid #1E293B;
        margin-bottom: 16px;
    }
    .brand-title {
        font-size: 1.5em;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.5px;
    }
    .brand-subtitle {
        font-size: 0.85em;
        color: #94A3B8;
        font-weight: 500;
    }
    
    /* Sector Radar Container */
    .sector-radar-box {
        background: linear-gradient(180deg, #0F172A 0%, #0A0F1D 100%);
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 20px;
    }
    .radar-title {
        font-size: 0.82em;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #64748B;
        margin-bottom: 10px;
    }
    
    /* Leader Badges */
    .leader-badge {
        display: inline-flex;
        align-items: center;
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 6px 12px;
        margin-right: 8px;
        margin-bottom: 8px;
        font-size: 0.9em;
        font-weight: 600;
        color: #F8FAFC;
    }
    .leader-gold { border-color: #F59E0B; background-color: rgba(245, 158, 11, 0.12); color: #FCD34D; }
    .leader-silver { border-color: #94A3B8; background-color: rgba(148, 163, 184, 0.12); color: #E2E8F0; }
    .leader-bronze { border-color: #D97706; background-color: rgba(217, 119, 6, 0.12); color: #FDBA74; }
    
    .sector-pill {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.78em;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .pill-green { background-color: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .pill-red { background-color: rgba(244, 63, 94, 0.12); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.25); }

    /* Setup Cards */
    .trade-card {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 14px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .trade-card:hover {
        border-color: #38BDF8;
    }
    .card-top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .stock-ticker {
        font-size: 1.45em;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.3px;
    }
    .industry-tag {
        font-size: 0.88em;
        font-weight: 500;
        color: #38BDF8;
        margin-left: 8px;
    }
    .grade-badge-aplus {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10B981;
        border: 1px solid #10B981;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.82em;
        font-weight: 700;
    }
    .grade-badge-a {
        background-color: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
        border: 1px solid #F59E0B;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.82em;
        font-weight: 700;
    }
    .respect-badge {
        background-color: #1E293B;
        color: #E2E8F0;
        border: 1px solid #334155;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 600;
        margin-left: 6px;
    }
    
    /* Metrics Row */
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
        background-color: #090E17;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 12px 14px;
        margin-top: 10px;
    }
    .metric-cell {
        display: flex;
        flex-direction: column;
    }
    .m-label {
        font-size: 0.72em;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .m-value {
        font-size: 1.05em;
        font-weight: 700;
        color: #FFFFFF;
    }
    .m-green { color: #34D399; }
    .m-amber { color: #FBBF24; }
    .m-rose { color: #FB7185; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def get_cached_candles():
    return load_all_candles()


@st.cache_data(ttl=1800)
def get_market_data(df_all):
    indices_dict = {}
    for sym in ["^NSEI", "^NSMIDCP", "^NSEBANK", "^INDIAVIX"]:
        sub = df_all[df_all["Symbol"] == sym]
        if sub.empty:
            sub = df_all[df_all["Symbol"] == sym.replace("^", "")]
        if not sub.empty:
            indices_dict[sym] = sub.sort_values("Date").reset_index(drop=True)
    gk = compute_gatekeeper_score(indices_dict)
    sec_regimes = get_all_sector_regimes(df_all)
    top_3, above_50, below_50 = get_sector_leaderboard(sec_regimes)
    return gk, sec_regimes, top_3, above_50, below_50


df_all = get_cached_candles()
gatekeeper, sector_regimes, top_3_sectors, sectors_above_50, sectors_below_50 = get_market_data(df_all)

# --- MINIMALIST SLEEK HEADER (No Box Clutter) ---
status_badge_color = "#10B981" if gatekeeper.status == "PASS" else ("#F59E0B" if gatekeeper.status == "CAUTION" else "#F43F5E")
st.markdown(
    f"""
    <div class="top-header-bar">
        <div>
            <span class="brand-title">📈 AVP SWING INTELLIGENCE</span>
            <div class="brand-subtitle">Institutional ATH & DEMA Execution Engine • 50 DEMA (₹1k Risk) | 200 EMA (₹2k Risk)</div>
        </div>
        <div style="text-align: right;">
            <div style="display: inline-block; background-color: rgba(30, 41, 59, 0.8); border: 1px solid {status_badge_color}; border-radius: 20px; padding: 4px 12px; font-weight: 700; font-size: 0.85em; color: {status_badge_color};">
                ● Market: {gatekeeper.status} ({gatekeeper.score}/10)
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("ℹ️ What does the Gatekeeper Score mean?"):
    st.markdown(
        """
        **The Gatekeeper is your Market Traffic Light.**
        * Over **70% of individual stock breakouts fail** when the broad market (Nifty 50 & Nifty Midcap) is falling below its moving averages.
        * **🟢 PASS (8–10)**: Broad indices are cleanly above 50 DEMA. Full risk deployment.
        * **🟡 CAUTION (5–7)**: Market is pulling back near moving averages. Deploy selectively—favor **Grade A+ Confirmed Higher-Low** setups only.
        * **🔴 BLOCK (0–4)**: Market is broken below 200 EMA. Pause opening new breakout trades.
        """
    )

# --- DEDICATED SECTOR RADAR (Top 3 Leaders + Sectors Above/Below 50 DEMA) ---
top_3_html = ""
ranks = ["🥇", "🥈", "🥉"]
classes = ["leader-gold", "leader-silver", "leader-bronze"]
for i, s in enumerate(top_3_sectors):
    top_3_html += f'<div class="leader-badge {classes[i]}">{ranks[i]} {s.index_name} <b>{s.pct_from_50_dema:+.1f}%</b></div>'

above_pills_html = "".join([f'<span class="sector-pill pill-green">🟢 {s.index_name} ({s.pct_from_50_dema:+.1f}%)</span>' for s in sectors_above_50])
below_pills_html = "".join([f'<span class="sector-pill pill-red">🔴 {s.index_name} ({s.pct_from_50_dema:+.1f}%)</span>' for s in sectors_below_50])

st.markdown(
    f"""
    <div class="sector-radar-box">
        <div class="radar-title">🔥 Leading Sectors Today (Top 3 vs 50 DEMA)</div>
        <div style="margin-bottom: 12px;">{top_3_html}</div>
        <div style="font-size: 0.82em; color: #94A3B8; margin-bottom: 4px;"><b>Sectors Above 50 DEMA (Uptrend):</b></div>
        <div style="margin-bottom: 8px;">{above_pills_html if above_pills_html else '<span style=\"color:#64748B; font-size:0.8em;\">None currently</span>'}</div>
        <div style="font-size: 0.82em; color: #94A3B8; margin-bottom: 4px;"><b>Sectors Below 50 DEMA (Pulling Back / Correcting):</b></div>
        <div>{below_pills_html if below_pills_html else '<span style=\"color:#64748B; font-size:0.8em;\">None currently</span>'}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🔍 Live Scanner", "📈 Backtesting Hub", "🛡️ All Sectors Detail"])

# ==========================================
# TAB 1: LIVE SCANNER
# ==========================================
with tab1:
    col_c1, col_c2, col_c3 = st.columns([1, 1, 1])
    with col_c1:
        selected_strategy = st.selectbox(
            "Strategy Filter",
            options=["COMBINED", "50_DEMA", "200_EMA"],
            format_func=lambda x: "All Strategies (50 DEMA & 200 EMA)" if x == "COMBINED" else STRATEGIES[x].name,
        )
    with col_c2:
        grade_filter = st.radio(
            "Quality Filter",
            options=["ALL", "APLUS_ONLY"],
            format_func=lambda x: "All Valid Setups" if x == "ALL" else "⭐ Confirmed Higher-Low (A+) Only",
            horizontal=True,
        )
    with col_c3:
        send_tg = st.checkbox("📱 Also Push to Telegram", value=False)

    run_scan_btn = st.button("🚀 Run Live Scan Now", use_container_width=True, type="primary")

    cached_results = st.session_state.get("scan_results", [])
    if cached_results and not hasattr(cached_results[0], "industry"):
        st.session_state.pop("scan_results", None)

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
    if grade_filter == "APLUS_ONLY":
        results = [r for r in results if getattr(r, "grade", "A") == "A+"]

    st.markdown(f"### **Found {len(results)} Qualifying Setups**")

    if not results:
        st.info("No stocks currently match the setup criteria. Market may be extended or in consolidation.")
    else:
        for r in results:
            grade_val = getattr(r, "grade", "A")
            badge_class = "grade-badge-aplus" if grade_val == "A+" else "grade-badge-a"
            strat_id = getattr(r, "strategy_id", "50_DEMA")
            strat_label = "50 DEMA (₹1k Risk)" if strat_id == "50_DEMA" else "200 EMA (₹2k Risk)"
            ind_name = getattr(r, "industry", "General")
            sec_name = getattr(r, "sector_name", "Nifty 50")
            sec_status = getattr(r, "sector_status_label", "⚪ Sector Info N/A")

            gtt_text = (
                f"DHAN GTT ORDER:\n"
                f"Symbol: {r.symbol}\n"
                f"Sector: {ind_name} ({sec_name})\n"
                f"Trigger Price: ₹{r.entry_price}\n"
                f"Limit Price: ₹{round(r.entry_price * 1.003, 2)}\n"
                f"Stop-Loss: ₹{r.stop_loss_price}\n"
                f"Quantity: {r.quantity}\n"
                f"Target (+2R): ₹{r.target_price}"
            )

            st.markdown(
                f"""
                <div class="trade-card">
                    <div class="card-top-row">
                        <div>
                            <span class="stock-ticker">{r.symbol}</span>
                            <span class="industry-tag">● {ind_name} ({sec_name})</span>
                        </div>
                        <div>
                            <span class="{badge_class}">{grade_val} {getattr(r, 'setup_type', 'Base')}</span>
                            <span class="respect-badge">EMA Respect: {getattr(r, 'respect_score_pct', 50)}%</span>
                        </div>
                    </div>
                    <div style="font-size: 0.88em; color: #94A3B8; margin-bottom: 8px;">
                        Sector Health: <b>{sec_status}</b> • Strategy: <b style="color: #F8FAFC;">{strat_label}</b> • <i>{getattr(r, 'pattern_summary', '')}</i>
                    </div>
                    <div class="metric-strip">
                        <div class="metric-cell">
                            <span class="m-label">Buy Above (Stop-Limit)</span>
                            <span class="m-value m-green">₹{r.entry_price:,.2f}</span>
                        </div>
                        <div class="metric-cell">
                            <span class="m-label">Stop-Loss</span>
                            <span class="m-value m-rose">₹{r.stop_loss_price:,.2f} ({r.risk_pct:.1f}%)</span>
                        </div>
                        <div class="metric-cell">
                            <span class="m-label">1R Sizing</span>
                            <span class="m-value m-amber">{r.quantity} shares</span>
                        </div>
                        <div class="metric-cell">
                            <span class="m-label">Total Risk</span>
                            <span class="m-value">₹{r.actual_risk_amount:,.0f}</span>
                        </div>
                        <div class="metric-cell">
                            <span class="m-label">BE Trigger (+1.5R)</span>
                            <span class="m-value">₹{r.breakeven_trigger_price:,.2f}</span>
                        </div>
                        <div class="metric-cell">
                            <span class="m-label">Target (+2.0R)</span>
                            <span class="m-value m-green">₹{r.target_price:,.2f}</span>
                        </div>
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

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Trades", s.total_trades)
        with m2:
            st.metric("Win Rate", f"{s.win_rate_pct}%", delta=f"{s.winning_trades}W / {s.losing_trades}L")
        with m3:
            st.metric("Net Realized R", f"+{s.net_r:,.1f} R", delta=f"₹{s.net_pnl:,.0f}")
        with m4:
            st.metric("Profit Factor", f"{s.profit_factor}", delta=f"Max DD: {s.max_drawdown_r}R")

        st.markdown("### Cumulative Performance (Equity Curve)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t["ExitDate"], y=t["CumR"], mode="lines", name="Cumulative R", line=dict(color="#10B981", width=2.5)))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#080C14",
            plot_bgcolor="#0F172A",
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_title="Date",
            yaxis_title="Realized R-Multiple",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

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
    st.subheader("All 16 Sectoral Indices Detail")
    st.write("Ranked by momentum relative to 50 DEMA:")

    for s in sorted(sector_regimes.values(), key=lambda x: x.pct_from_50_dema, reverse=True):
        st_color = "#10B981" if s.is_above_50_dema else ("#F59E0B" if s.is_above_200_ema else "#F43F5E")
        st.markdown(
            f"""
            <div style="background-color: #0F172A; border-left: 5px solid {st_color}; border: 1px solid #1E293B; border-left-width: 5px; padding: 12px 16px; margin-bottom: 8px; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 700; font-size: 1.05em; color: #FFFFFF;">{s.index_name} <span style="font-weight: 400; color: #64748B; font-size: 0.85em;">({s.symbol})</span></span>
                    <span style="font-weight: 700; color: {st_color};">{s.pct_from_50_dema:+.1f}% vs 50 DEMA</span>
                </div>
                <div style="font-size: 0.85em; color: #94A3B8; margin-top: 4px;">
                    Close: ₹{s.close:,.2f} • 50 DEMA: ₹{s.dema_50:,.2f} • 200 EMA: ₹{s.ema_200:,.2f} ({s.pct_from_200_ema:+.1f}%) • State: <b style="color: {st_color};">{s.trend_state}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
