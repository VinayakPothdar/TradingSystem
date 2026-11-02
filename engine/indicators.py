"""
Technical indicators and price action patterns:
- True Lifetime ATH (cummax)
- DEMA / EMA calculation
- ATR calculation
- Moving Average Respect Score (EMA Affinity)
- Higher-Low (HL) Confirmation Pattern Detector
"""

import numpy as np
import pandas as pd


def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculates Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def compute_dema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates Double Exponential Moving Average (DEMA).
    DEMA = 2 * EMA - EMA(EMA)
    """
    ema1 = compute_ema(series, period)
    ema2 = compute_ema(ema1, period)
    return 2 * ema1 - ema2


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Average True Range (ATR)."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def enrich_candles(df: pd.DataFrame, ath_lookback_days: int = 180) -> pd.DataFrame:
    """
    Enriches candle DataFrame with:
    - 50 DEMA, 200 EMA
    - ATR 14
    - True Lifetime ATH (cummax) & Days Since ATH
    """
    data = df.copy()
    if not isinstance(data.index, pd.DatetimeIndex):
        if "Date" in data.columns:
            data["Date"] = pd.to_datetime(data["Date"])
            data = data.sort_values("Date").reset_index(drop=True)

    data["DEMA_50"] = compute_dema(data["Close"], 50)
    data["EMA_200"] = compute_ema(data["Close"], 200)
    data["ATR_14"] = compute_atr(data, 14)

    # True Lifetime ATH
    data["Lifetime_ATH"] = data["High"].cummax()
    
    # Track when the last ATH occurred
    is_ath = (data["High"] >= data["Lifetime_ATH"] - 1e-4)
    ath_indices = np.where(is_ath, data.index, np.nan)
    data["Last_ATH_Index"] = pd.Series(ath_indices, index=data.index).ffill()
    data["Bars_Since_ATH"] = data.index - data["Last_ATH_Index"]
    data["Is_ATH_Active"] = data["Bars_Since_ATH"] <= ath_lookback_days

    return data


def compute_ma_respect_score(df: pd.DataFrame, ma_col: str, lookback_bars: int = 250) -> dict:
    """
    Evaluates whether this stock respected the specified Moving Average in the past.
    Returns:
    - respect_pct: Percentage of touches that bounced successfully (e.g. 80.0)
    - total_touches: Number of pullback touches identified
    - successful_bounces: Number of touches that rallied >= 4% without closing > 2% below MA
    - avg_bounce_pct: Average return on successful bounces
    - grade: 'HIGH' (>=75%), 'MODERATE' (50-74%), 'POOR' (<50%)
    """
    if len(df) < 60 or ma_col not in df.columns:
        return {"respect_pct": 0.0, "total_touches": 0, "successful_bounces": 0, "avg_bounce_pct": 0.0, "grade": "UNKNOWN"}

    recent = df.tail(lookback_bars).copy().reset_index(drop=True)
    ma = recent[ma_col]
    low = recent["Low"]
    close = recent["Close"]
    high = recent["High"]

    # Condition for touching MA: Low is within ±1.5% of MA, but didn't open below it
    touch_mask = (low <= ma * 1.015) & (low >= ma * 0.97)

    # Cluster consecutive touch bars together
    touches = []
    i = 0
    n = len(recent)
    while i < n - 15:
        if touch_mask.iloc[i]:
            touch_idx = i
            # Find the local trough in this touch window (up to 4 consecutive bars)
            window_end = min(i + 4, n - 15)
            trough_idx = low.iloc[i:window_end].idxmin()
            trough_price = low.iloc[trough_idx]
            touch_ma = ma.iloc[trough_idx]

            # Evaluate next 15 bars for bounce
            forward_window = recent.iloc[trough_idx + 1 : trough_idx + 16]
            max_forward_high = forward_window["High"].max()
            min_forward_close = forward_window["Close"].min()

            # Success: rallied by at least +4.0% above trough before closing > 2% below MA
            rallied = (max_forward_high - trough_price) / trough_price >= 0.04
            held_ma = min_forward_close >= touch_ma * 0.98

            success = rallied and held_ma
            bounce_return = ((max_forward_high - trough_price) / trough_price) * 100.0 if success else 0.0

            touches.append({"success": success, "return": bounce_return})
            # Skip forward so we don't count the same pullback twice
            i = trough_idx + 10
        else:
            i += 1

    if not touches:
        return {"respect_pct": 50.0, "total_touches": 0, "successful_bounces": 0, "avg_bounce_pct": 0.0, "grade": "NEUTRAL"}

    successful = [t for t in touches if t["success"]]
    respect_pct = round((len(successful) / len(touches)) * 100.0, 1)
    avg_bounce = round(float(np.mean([t["return"] for t in successful])), 1) if successful else 0.0

    if respect_pct >= 75.0:
        grade = "HIGH"
    elif respect_pct >= 50.0:
        grade = "MODERATE"
    else:
        grade = "POOR"

    return {
        "respect_pct": respect_pct,
        "total_touches": len(touches),
        "successful_bounces": len(successful),
        "avg_bounce_pct": avg_bounce,
        "grade": grade,
    }


def detect_higher_low_pattern(df: pd.DataFrame, ma_col: str, lookback: int = 25, min_jump_pct: float = 0.03) -> dict:
    """
    Detects the 'Touch -> Jump -> Higher Low (HL)' Confirmation Pattern.
    Pattern sequence:
    1. First Trough (T1): Low tests MA zone (Low within ±2% of MA)
    2. Reaction Peak (H1): Price rallies >= min_jump_pct (e.g. 3-4%) above T1
    3. Higher Low (T2): Price pulls back, but holds above T1 (T2 > T1)
    4. Base High: The breakout trigger above the consolidation / H1
    """
    if len(df) < lookback or ma_col not in df.columns:
        return {"has_higher_low": False, "grade": "A"}

    window = df.tail(lookback).copy().reset_index(drop=True)
    ma = window[ma_col]
    low = window["Low"]
    high = window["High"]
    close = window["Close"]
    n = len(window)

    # Search for T1 in the earlier half of the window
    # T1 must be a touch of MA
    t1_candidates = []
    for i in range(0, n - 6):
        if low.iloc[i] <= ma.iloc[i] * 1.02:
            t1_candidates.append(i)

    if not t1_candidates:
        return {"has_higher_low": False, "grade": "A"}

    # Take the most prominent early touch as T1
    t1_idx = min(t1_candidates, key=lambda idx: low.iloc[idx])
    t1_price = low.iloc[t1_idx]

    # Look for Peak H1 after T1
    if t1_idx >= n - 4:
        return {"has_higher_low": False, "grade": "A"}

    h1_slice = high.iloc[t1_idx + 1 : n - 2]
    if h1_slice.empty:
        return {"has_higher_low": False, "grade": "A"}

    h1_idx = h1_slice.idxmax()
    h1_price = high.iloc[h1_idx]

    # Check if reaction rally was significant
    jump_pct = (h1_price - t1_price) / t1_price
    if jump_pct < min_jump_pct:
        return {"has_higher_low": False, "grade": "A"}

    # Look for Higher Low T2 after H1
    if h1_idx >= n - 1:
        return {"has_higher_low": False, "grade": "A"}

    t2_slice = low.iloc[h1_idx + 1 : n]
    if t2_slice.empty:
        return {"has_higher_low": False, "grade": "A"}

    t2_idx = t2_slice.idxmin()
    t2_price = low.iloc[t2_idx]

    # Verify that T2 > T1 (Higher Low held above initial touch)
    if t2_price > t1_price * 1.002:  # Held at least 0.2% above T1
        # Confirmation found!
        hl_buffer_pct = round(((t2_price - t1_price) / t1_price) * 100.0, 2)
        return {
            "has_higher_low": True,
            "grade": "A+",
            "t1_price": round(float(t1_price), 2),
            "h1_price": round(float(h1_price), 2),
            "t2_price": round(float(t2_price), 2),
            "jump_pct": round(jump_pct * 100.0, 1),
            "hl_buffer_pct": hl_buffer_pct,
            "pattern_summary": f"HL: ₹{t2_price:.1f} &gt; T1: ₹{t1_price:.1f} (+{hl_buffer_pct:.1f}%)",
        }

    return {"has_higher_low": False, "grade": "A"}
