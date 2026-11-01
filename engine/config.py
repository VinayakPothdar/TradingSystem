"""
Central configuration for TradingSystem Engine.
Defines parameters for 50 DEMA (₹1k risk) and 200 EMA (₹2k risk) strategies.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class StrategyConfig:
    id: str
    name: str
    ma_type: Literal["DEMA", "EMA", "SMA"]
    ma_period: int
    default_risk: float               # 1R Risk amount (₹1,000 for 50 DEMA, ₹2,000 for 200 EMA)
    max_base_contraction: float       # Max base width, e.g. 0.07 (7%)
    min_base_length: int              # Min bars in consolidation
    max_base_length: int              # Max bars in consolidation
    stop_atr_mult: float              # Multiplier below base low (0.3 ATR)
    breakeven_trigger_r: float        # Move SL to Entry at +1.5R Peak
    target_r: float                   # Book 50% at +2.0R
    ath_lookback_days: int            # True ATH window (e.g. 180 bars)
    ma_tolerance_pct: float           # Proximity to MA (e.g. 0.015 = 1.5%)
    # Higher-Low Confirmation Parameters
    hl_min_jump_pct: float            # Min reaction rally from first EMA touch (e.g. 0.03 = 3%)
    hl_max_lookback: int              # Max bars for T1 -> H1 -> T2 sequence


STRATEGY_50_DEMA = StrategyConfig(
    id="50_DEMA",
    name="50 DEMA Pullback",
    ma_type="DEMA",
    ma_period=50,
    default_risk=1000.0,              # ₹1,000 1R Risk
    max_base_contraction=0.07,         # 7.0% Max Base Contraction
    min_base_length=3,
    max_base_length=8,
    stop_atr_mult=0.3,
    breakeven_trigger_r=1.5,
    target_r=2.0,
    ath_lookback_days=180,
    ma_tolerance_pct=0.015,            # ±1.5% from 50 DEMA
    hl_min_jump_pct=0.03,              # 3% reaction jump
    hl_max_lookback=25,
)

STRATEGY_200_EMA = StrategyConfig(
    id="200_EMA",
    name="200 EMA Pullback",
    ma_type="EMA",
    ma_period=200,
    default_risk=2000.0,              # ₹2,000 1R Risk
    max_base_contraction=0.07,         # 7.0% Max Base Contraction
    min_base_length=4,
    max_base_length=12,
    stop_atr_mult=0.3,
    breakeven_trigger_r=1.5,
    target_r=2.0,
    ath_lookback_days=180,
    ma_tolerance_pct=0.020,            # ±2.0% from 200 EMA
    hl_min_jump_pct=0.04,              # 4% reaction jump
    hl_max_lookback=35,
)

STRATEGIES = {
    "50_DEMA": STRATEGY_50_DEMA,
    "200_EMA": STRATEGY_200_EMA,
}

# Market & Sector Indices for Gatekeeper
KEY_INDICES = {
    "NIFTY_50": "^NSEI",
    "NIFTY_BANK": "^NSEBANK",
    "NIFTY_MIDCAP_150": "^NSMIDCP",
    "NIFTY_SMALLCAP_250": "^CNXSC",
    "INDIA_VIX": "^INDIAVIX",
}
