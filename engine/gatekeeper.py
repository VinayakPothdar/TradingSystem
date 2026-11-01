"""
Gatekeeper and Market Regime Module:
Evaluates Nifty 50, Midcap, Bank Nifty, and all 17 Sectoral/Thematic Indices relative to 50 DEMA and 200 EMA.
Calculates Gatekeeper Score (0 - 10), tracks underlying sector EMA status for every stock,
and provides top-performing sector rankings.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from engine.indicators import compute_dema, compute_ema

INDUSTRY_TO_SECTOR = {
    "Financial Services": ("Nifty Financial Services", "NIFTY_FIN_SERVICE.NS"),
    "Capital Goods": ("Nifty Infrastructure", "^CNXINFRA"),
    "Healthcare": ("Nifty Pharma", "^CNXPHARMA"),
    "Automobile and Auto Components": ("Nifty Auto", "^CNXAUTO"),
    "Consumer Services": ("Nifty FMCG", "^CNXFMCG"),
    "Fast Moving Consumer Goods": ("Nifty FMCG", "^CNXFMCG"),
    "Information Technology": ("Nifty IT", "^CNXIT"),
    "Chemicals": ("Nifty Pharma / Chemicals", "^CNXPHARMA"),
    "Metals & Mining": ("Nifty Metal", "^CNXMETAL"),
    "Power": ("Nifty Energy", "^CNXENERGY"),
    "Oil Gas & Consumable Fuels": ("Nifty Energy", "^CNXENERGY"),
    "Consumer Durables": ("Nifty FMCG", "^CNXFMCG"),
    "Services": ("Nifty Services", "^CNXINFRA"),
    "Construction": ("Nifty Infrastructure", "^CNXINFRA"),
    "Construction Materials": ("Nifty Infrastructure", "^CNXINFRA"),
    "Realty": ("Nifty Realty", "^CNXREALTY"),
    "Telecommunication": ("Nifty Infrastructure", "^CNXINFRA"),
    "Textiles": ("Nifty FMCG", "^CNXFMCG"),
    "Media Entertainment & Publication": ("Nifty Media", "^CNXMEDIA"),
    "Diversified": ("Nifty 50", "^NSEI"),
}


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


def load_symbol_industry_map() -> Dict[str, str]:
    """Loads Symbol -> Industry mapping from data/nifty500.csv."""
    watchlist_path = Path(__file__).resolve().parents[1] / "data" / "nifty500.csv"
    if not watchlist_path.exists():
        return {}
    try:
        df = pd.read_csv(watchlist_path)
        if "Symbol" in df.columns and "Industry" in df.columns:
            return dict(zip(df["Symbol"].astype(str).str.strip().str.upper(), df["Industry"].astype(str).str.strip()))
    except Exception:
        pass
    return {}


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


def get_all_sector_regimes(df_all: pd.DataFrame) -> Dict[str, RegimeStatus]:
    """Evaluates 50 DEMA and 200 EMA positions for all 17 sector and thematic indices."""
    sector_tickers = {
        "^NSEBANK": "Nifty Bank",
        "^CNXPSUBANK": "Nifty PSU Bank",
        "NIFTY_FIN_SERVICE.NS": "Nifty Financial Services",
        "^CNXIT": "Nifty IT",
        "^CNXAUTO": "Nifty Auto",
        "^CNXPHARMA": "Nifty Pharma",
        "^CNXFMCG": "Nifty FMCG",
        "^CNXMETAL": "Nifty Metal",
        "^CNXREALTY": "Nifty Realty",
        "^CNXENERGY": "Nifty Energy",
        "^CNXINFRA": "Nifty Infrastructure",
        "^CNXPSE": "Nifty PSE",
        "^NSEMDCP50": "Nifty Midcap 50",
        "NIFTYSMLCAP250": "Nifty Smallcap 250",
        "^CNX100": "Nifty 100",
        "^CNX200": "Nifty 200",
        "^CRSLDX": "Nifty 500",
    }
    regimes: Dict[str, RegimeStatus] = {}
    for ticker, name in sector_tickers.items():
        sub = df_all[df_all["Symbol"] == ticker]
        if sub.empty:
            sub = df_all[df_all["Symbol"] == ticker.replace("^", "")]
        if not sub.empty and len(sub) >= 50:
            status = evaluate_index_regime(sub, name, ticker)
            if status:
                regimes[ticker] = status
    return regimes


def get_sector_leaderboard(
    sector_regimes: Dict[str, RegimeStatus]
) -> Tuple[List[RegimeStatus], List[RegimeStatus], List[RegimeStatus], List[RegimeStatus]]:
    """
    Returns:
    - top_3_leaders: Top 3 performing sectors relative to 50 DEMA
    - sectors_above_50: All sectors currently trading above their 50 DEMA
    - sectors_above_200: All sectors currently trading above their 200 EMA
    - sectors_below_200: All sectors currently trading below their 200 EMA
    """
    # Filter for active sectoral & thematic indices
    pure_sectors = [s for s in sector_regimes.values() if s.symbol not in ["^CNX100", "^CNX200", "^CRSLDX"]]
    sorted_all = sorted(pure_sectors, key=lambda s: s.pct_from_50_dema, reverse=True)
    top_3 = sorted_all[:3]
    above_50 = [s for s in sorted_all if s.is_above_50_dema]
    above_200 = [s for s in sorted_all if s.is_above_200_ema]
    below_200 = [s for s in sorted_all if not s.is_above_200_ema]
    return top_3, above_50, above_200, below_200


def get_stock_sector_info(
    symbol: str,
    industry_map: Dict[str, str],
    sector_regimes: Dict[str, RegimeStatus],
) -> Tuple[str, str, str, bool]:
    """
    Returns (industry_name, sector_index_name, sector_status_label, is_sector_bullish).
    """
    sym = symbol.replace(".NS", "").upper()
    industry = industry_map.get(sym, "Diversified")
    sector_name, ticker = INDUSTRY_TO_SECTOR.get(industry, ("Nifty 50", "^NSEI"))

    regime = sector_regimes.get(ticker)
    if not regime:
        for t, r in sector_regimes.items():
            if ticker in t or r.index_name == sector_name:
                regime = r
                break

    if regime:
        if regime.is_above_50_dema:
            label = f"🟢 Above 50 DEMA ({regime.pct_from_50_dema:+.1f}%)"
            is_bullish = True
        elif regime.is_above_200_ema:
            label = f"🟡 Below 50 DEMA, Above 200 EMA ({regime.pct_from_200_ema:+.1f}%)"
            is_bullish = False
        else:
            label = f"🔴 Below 200 EMA ({regime.pct_from_200_ema:+.1f}%)"
            is_bullish = False
    else:
        label = "⚪ Sector Regime N/A"
        is_bullish = True

    return industry, sector_name, label, is_bullish


def compute_gatekeeper_score(indices_data: Dict[str, pd.DataFrame]) -> GatekeeperReport:
    """
    Computes unified Gatekeeper score (0 - 10) based on market indices.
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

    score = 7.0
    if nifty_status and midcap_status:
        pts = 0.0
        if nifty_status.is_above_50_dema:
            pts += 4.0
        elif nifty_status.is_above_200_ema:
            pts += 2.0

        if midcap_status.is_above_50_dema:
            pts += 4.0
        elif midcap_status.is_above_200_ema:
            pts += 2.0

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
