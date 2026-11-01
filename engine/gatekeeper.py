"""
Gatekeeper and Market Regime Module:
Evaluates Nifty 50, Midcap, Bank Nifty, and Sector health relative to 50 DEMA and 200 EMA.
Calculates Gatekeeper Score (0 - 10) and provides regime recommendation.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import pandas as pd
from engine.indicators import compute_dema, compute_ema


@dataclass
class RegimeStatus:
    index_name: str
    symbol: str
    close: float
    dema_50: float
    ema_200: float
    pct_from_50_dema: float
    pct_from_200_ema: float
    is_above_50_dema: bool
    is_above_200_ema: bool
    trend_state: str  # BULLISH, CAUTION, DEFENSIVE


@dataclass
class GatekeeperReport:
    score: float           # 0.0 to 10.0
    status: str            # PASS (>=6.5), CAUTION (4.5 - 6.4), BLOCK (<4.5)
    headline: str
    nifty50_status: Optional[RegimeStatus]
    midcap_status: Optional[RegimeStatus]
    regime_breakdown: Dict[str, RegimeStatus]


def evaluate_index_regime(df: Optional[pd.DataFrame], name: str, symbol: str) -> Optional[RegimeStatus]:
    """Evaluates trend and regime of an index."""
    if df is None or len(df) < 50:
        return None

    data = df.sort_values("Date").reset_index(drop=True)
    close = data["Close"]

    dema_50 = compute_dema(close, 50).iloc[-1]
    ema_200 = compute_ema(close, min(200, len(close))).iloc[-1] if len(close) >= 100 else dema_50
    curr_close = float(close.iloc[-1])

    pct_from_50 = round(((curr_close - dema_50) / dema_50) * 100.0, 2)
    pct_from_200 = round(((curr_close - ema_200) / ema_200) * 100.0, 2)

    above_50 = curr_close >= dema_50
    above_200 = curr_close >= ema_200

    if above_50 and above_200:
        trend = "BULLISH"
    elif above_200 and not above_50:
        trend = "CAUTION"
    else:
        trend = "DEFENSIVE"

    return RegimeStatus(
        index_name=name,
        symbol=symbol,
        close=round(curr_close, 2),
        dema_50=round(float(dema_50), 2),
        ema_200=round(float(ema_200), 2),
        pct_from_50_dema=pct_from_50,
        pct_from_200_ema=pct_from_200,
        is_above_50_dema=above_50,
        is_above_200_ema=above_200,
        trend_state=trend,
    )


def compute_gatekeeper_score(indices_data: Dict[str, pd.DataFrame]) -> GatekeeperReport:
    """
    Computes unified Gatekeeper score (0 - 10) based on market indices.
    Weights:
    - Nifty 50: 40%
    - Nifty Midcap: 40%
    - Bank Nifty: 20%
    """
    breakdown = {}

    def _find_df(keys):
        for k in keys:
            if k in indices_data and indices_data[k] is not None and not indices_data[k].empty:
                return indices_data[k]
        return None

    nifty_df = _find_df(["^NSEI", "CNX100", "NIFTY 50", "NSEI"])
    midcap_df = _find_df(["^NSMIDCP", "^NSEMDCP50", "NIFTY MIDCAP", "NSMIDCP", "NSEMDCP50"])
    bank_df = _find_df(["^NSEBANK", "BANKNIFTY", "NSEBANK"])

    nifty_status = evaluate_index_regime(nifty_df, "Nifty 50", "^NSEI")
    midcap_status = evaluate_index_regime(midcap_df, "Nifty Midcap", "^NSMIDCP")
    bank_status = evaluate_index_regime(bank_df, "Nifty Bank", "^NSEBANK")

    if nifty_status:
        breakdown["Nifty 50"] = nifty_status
    if midcap_status:
        breakdown["Nifty Midcap"] = midcap_status
    if bank_status:
        breakdown["Nifty Bank"] = bank_status

    score = 7.0  # Default neutral
    if nifty_status and midcap_status:
        pts = 0.0
        # Nifty 50 (max 4 pts)
        if nifty_status.is_above_50_dema:
            pts += 4.0
        elif nifty_status.is_above_200_ema:
            pts += 2.0

        # Midcap (max 4 pts)
        if midcap_status.is_above_50_dema:
            pts += 4.0
        elif midcap_status.is_above_200_ema:
            pts += 2.0

        # Bank Nifty (max 2 pts)
        if bank_status:
            if bank_status.is_above_50_dema:
                pts += 2.0
            elif bank_status.is_above_200_ema:
                pts += 1.0
        else:
            pts += 1.5

        score = round(pts, 1)

    if score >= 6.5:
        status = "PASS"
        headline = "Bullish Regime — All Clear for Swing Setups"
    elif score >= 4.5:
        status = "CAUTION"
        headline = "Neutral / Pullback Regime — Favor Confirmed Higher-Low Setups"
    else:
        status = "BLOCK"
        headline = "Defensive Regime — Market Below MAs, Avoid Aggressive Breakouts"

    return GatekeeperReport(
        score=score,
        status=status,
        headline=headline,
        nifty50_status=nifty_status,
        midcap_status=midcap_status,
        regime_breakdown=breakdown,
    )
