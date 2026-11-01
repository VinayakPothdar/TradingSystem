"""
Unified Scanner Engine:
Scans Nifty 500 stocks for:
1. 50 DEMA Pullbacks (1R = ₹1,000 Risk)
2. 200 EMA Pullbacks (1R = ₹2,000 Risk)

Strict Institutional Filters:
- True Lifetime ATH made within 5 to 90 days (50 DEMA) or 5 to 180 days (200 EMA)
- 50 DEMA > 200 EMA (Bullish Trend Alignment)
- Close > 200 EMA * 0.97
- Base Contraction (4-8 bars, 1.5% <= risk_pct <= 7.5%)
- Grade A+ (Confirmed Higher-Low) vs Grade A (First-Touch Base)
- Moving Average Respect Score (EMA Affinity)
- Underlying Sector EMA Position & Industry Tracking
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from engine.config import STRATEGIES, StrategyConfig
from engine.gatekeeper import (
    get_all_sector_regimes,
    get_stock_sector_info,
    load_symbol_industry_map,
    RegimeStatus,
)
from engine.indicators import (
    compute_ma_respect_score,
    detect_higher_low_pattern,
    enrich_candles,
)
from engine.risk import calculate_position_sizing


@dataclass
class ScanResult:
    symbol: str
    strategy_id: str
    strategy_name: str
    industry: str                # e.g. "Metals & Mining"
    sector_name: str             # e.g. "Nifty Metal"
    sector_status_label: str     # e.g. "🟢 Above 50 DEMA (+3.8%)"
    is_sector_bullish: bool
    grade: str                   # 'A+' (Confirmed Higher-Low) or 'A' (First-Touch Base)
    setup_type: str              # 'Confirmed Higher-Low Pivot' or 'First-Touch Base'
    current_price: float
    ma_value: float
    dist_from_ma_pct: float
    entry_price: float           # Stop-Limit Entry (Base High)
    stop_loss_price: float       # Stop-Loss (Base Low or HL - 0.3 ATR)
    risk_per_share: float
    risk_pct: float
    quantity: int                # Strict 1R sizing
    target_risk_amount: float    # ₹1,000 or ₹2,000
    actual_risk_amount: float
    breakeven_trigger_price: float  # +1.5R
    target_price: float            # +2.0R
    base_length: int
    base_range_pct: float
    respect_score_pct: float     # Historical bounce win rate on this EMA
    respect_grade: str           # HIGH, MODERATE, POOR
    pattern_summary: str
    last_candle_date: str
    bars_since_ath: int
    ath_price: float
    corr_from_ath_pct: float


def scan_single_stock(
    df: pd.DataFrame,
    symbol: str,
    strategy: StrategyConfig,
    industry_map: Dict[str, str],
    sector_regimes: Dict[str, RegimeStatus],
) -> Optional[ScanResult]:
    """Evaluates a single stock DataFrame against a strategy configuration."""
    if df is None or len(df) < 220:
        return None

    # Enrich candles with 50 DEMA, 200 EMA, ATR, True ATH
    enriched = enrich_candles(df, ath_lookback_days=strategy.ath_lookback_days)
    if enriched.empty:
        return None

    latest = enriched.iloc[-1]
    curr_close = float(latest["Close"])
    curr_low = float(latest["Low"])
    curr_atr = float(latest["ATR_14"])
    dema_50 = float(latest["DEMA_50"])
    ema_200 = float(latest["EMA_200"])
    ath_price = float(latest["Lifetime_ATH"])
    bars_since_ath = int(latest["Bars_Since_ATH"]) if not np.isnan(latest["Bars_Since_ATH"]) else 999

    # Filter 1: Pullback window from True ATH
    max_ath_days = 90 if strategy.id == "50_DEMA" else 180
    if not (5 <= bars_since_ath <= max_ath_days):
        return None

    # Filter 2: Macro Trend Alignment
    if curr_close < ema_200 * 0.97:
        return None
    if strategy.id == "50_DEMA" and dema_50 < ema_200:
        return None

    # Filter 3: Proximity to Support MA
    sup_val = dema_50 if strategy.id == "50_DEMA" else ema_200
    dist_pct = ((curr_close - sup_val) / sup_val) * 100.0
    if not (-3.0 <= dist_pct <= 3.8):
        return None

    # Filter 4: Prior 20 bars held above MA
    prior_window = enriched.iloc[max(0, len(enriched) - 21) : -1]
    if prior_window["Close"].mean() < sup_val * 0.98:
        return None

    # Filter 5: Base Contraction (Last 4 to 8 bars)
    base_window = enriched.tail(strategy.max_base_length)
    if len(base_window) < strategy.min_base_length:
        return None

    base_high = float(base_window["High"].max())
    base_low = float(base_window["Low"].min())
    base_range = (base_high - base_low) / base_low

    if base_range > strategy.max_base_contraction:
        return None

    # Filter 6: Higher-Low Confirmation Pattern
    ma_col = "DEMA_50" if strategy.id == "50_DEMA" else "EMA_200"
    hl_res = detect_higher_low_pattern(
        enriched,
        ma_col=ma_col,
        lookback=strategy.hl_max_lookback,
        min_jump_pct=strategy.hl_min_jump_pct,
    )

    grade = hl_res.get("grade", "A")
    has_hl = hl_res.get("has_higher_low", False)

    if has_hl and "t2_price" in hl_res:
        effective_low = hl_res["t2_price"]
        setup_type = "Confirmed Higher-Low Pivot"
        pattern_summary = hl_res.get("pattern_summary", "Higher Low Held")
    else:
        effective_low = base_low
        setup_type = "First-Touch Base Contraction"
        pattern_summary = f"{len(base_window)}-bar base ({base_range*100:.1f}%)"

    entry_price = round(base_high + 0.05, 2)
    sl_price = round(effective_low - (strategy.stop_atr_mult * curr_atr), 2)

    risk_per_share = entry_price - sl_price
    if risk_per_share <= 0:
        return None

    risk_pct = (risk_per_share / entry_price) * 100.0
    if not (1.5 <= risk_pct <= 7.5):
        return None

    # Position sizing
    sizing = calculate_position_sizing(
        entry_price=entry_price,
        stop_loss_price=sl_price,
        target_risk=strategy.default_risk,
        max_risk_pct=strategy.max_base_contraction,
    )

    if not sizing.is_valid or sizing.quantity < 1:
        return None

    # Moving Average Respect Score
    respect = compute_ma_respect_score(enriched, ma_col=ma_col, lookback_bars=250)

    # Sector & Industry Info
    industry, sector_name, sector_status, is_sector_bullish = get_stock_sector_info(
        symbol, industry_map, sector_regimes
    )

    candle_date = str(latest["Date"])[:10] if "Date" in latest else ""
    corr_pct = round(((curr_close - ath_price) / ath_price) * 100.0, 1)

    return ScanResult(
        symbol=symbol,
        strategy_id=strategy.id,
        strategy_name=strategy.name,
        industry=industry,
        sector_name=sector_name,
        sector_status_label=sector_status,
        is_sector_bullish=is_sector_bullish,
        grade=grade,
        setup_type=setup_type,
        current_price=round(curr_close, 2),
        ma_value=round(sup_val, 2),
        dist_from_ma_pct=round(dist_pct, 2),
        entry_price=sizing.entry_price,
        stop_loss_price=sizing.stop_loss_price,
        risk_per_share=sizing.risk_per_share,
        risk_pct=round(risk_pct, 2),
        quantity=sizing.quantity,
        target_risk_amount=sizing.target_risk_amount,
        actual_risk_amount=sizing.actual_risk_amount,
        breakeven_trigger_price=sizing.breakeven_trigger_price,
        target_price=sizing.target_price,
        base_length=len(base_window),
        base_range_pct=round(base_range * 100.0, 2),
        respect_score_pct=respect["respect_pct"],
        respect_grade=respect["grade"],
        pattern_summary=pattern_summary,
        last_candle_date=candle_date,
        bars_since_ath=bars_since_ath,
        ath_price=round(ath_price, 2),
        corr_from_ath_pct=corr_pct,
    )


def run_full_scan(df_all: pd.DataFrame, strategy_id: Optional[str] = None) -> List[ScanResult]:
    """
    Scans all stocks in df_all across selected strategy (or both 50 DEMA & 200 EMA).
    Returns list of ScanResult sorted by Grade (A+ first) and Respect Score.
    """
    strategies_to_run = (
        [STRATEGIES[strategy_id]] if strategy_id and strategy_id in STRATEGIES else list(STRATEGIES.values())
    )

    industry_map = load_symbol_industry_map()
    sector_regimes = get_all_sector_regimes(df_all)

    symbols = df_all["Symbol"].unique()
    results: List[ScanResult] = []

    for strat in strategies_to_run:
        for sym in symbols:
            if str(sym).startswith("^"):
                continue
            stock_df = df_all[df_all["Symbol"] == sym].sort_values("Date").reset_index(drop=True)
            res = scan_single_stock(stock_df, str(sym), strat, industry_map, sector_regimes)
            if res:
                results.append(res)

    results.sort(
        key=lambda r: (0 if r.grade == "A+" else 1, -r.respect_score_pct, r.risk_pct)
    )
    return results


def export_scan_to_json(results: List[ScanResult], output_path: Path) -> None:
    """Exports scan results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(r) for r in results]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
