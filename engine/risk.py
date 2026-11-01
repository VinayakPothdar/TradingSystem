"""
Risk management and position sizing engine.
Strictly implements 1R Risk modeling:
- ₹1,000 Risk per trade for 50 DEMA
- ₹2,000 Risk per trade for 200 EMA
- ATR-based Stop-Loss computation
- +1.5R Breakeven ratchet level
- +2.0R Target 1 booking level
"""

import math
from dataclasses import dataclass


@dataclass
class SizingResult:
    entry_price: float
    stop_loss_price: float
    risk_per_share: float
    risk_pct: float
    target_risk_amount: float     # ₹1,000 or ₹2,000
    quantity: int
    actual_risk_amount: float
    capital_required: float
    breakeven_trigger_price: float  # +1.5R
    target_price: float            # +2.0R
    is_valid: bool
    warning_message: str = ""


def calculate_position_sizing(
    entry_price: float,
    stop_loss_price: float,
    target_risk: float = 1000.0,
    max_risk_pct: float = 0.07,
) -> SizingResult:
    """
    Computes strict 1R position sizing and key exit price targets.
    
    Formula:
    Risk Per Share = Entry - SL
    Quantity = floor(Target Risk / Risk Per Share)
    Breakeven Trigger (+1.5R) = Entry + 1.5 * Risk Per Share
    Target (+2.0R) = Entry + 2.0 * Risk Per Share
    """
    if entry_price <= 0 or stop_loss_price <= 0 or stop_loss_price >= entry_price:
        return SizingResult(
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            risk_per_share=0.0,
            risk_pct=0.0,
            target_risk_amount=target_risk,
            quantity=0,
            actual_risk_amount=0.0,
            capital_required=0.0,
            breakeven_trigger_price=0.0,
            target_price=0.0,
            is_valid=False,
            warning_message="Invalid Entry or SL price",
        )

    risk_per_share = entry_price - stop_loss_price
    risk_pct = risk_per_share / entry_price

    # Position sizing
    raw_qty = target_risk / risk_per_share
    qty = math.floor(raw_qty)

    warning = ""
    is_valid = True

    if qty < 1:
        qty = 1
        warning = f"High share price: Minimum 1 share required (Risk exceeds ₹{target_risk:,.0f})"

    actual_risk = round(qty * risk_per_share, 2)
    capital_required = round(qty * entry_price, 2)

    if risk_pct > max_risk_pct:
        warning = f"Wide base risk ({risk_pct*100:.1f}% > {max_risk_pct*100:.0f}% max allowed)"
        # Still calculate, but flag warning

    be_price = round(entry_price + (1.5 * risk_per_share), 2)
    target_price = round(entry_price + (2.0 * risk_per_share), 2)

    return SizingResult(
        entry_price=round(entry_price, 2),
        stop_loss_price=round(stop_loss_price, 2),
        risk_per_share=round(risk_per_share, 2),
        risk_pct=round(risk_pct * 100.0, 2),
        target_risk_amount=target_risk,
        quantity=qty,
        actual_risk_amount=actual_risk,
        capital_required=capital_required,
        breakeven_trigger_price=be_price,
        target_price=target_price,
        is_valid=is_valid,
        warning_message=warning,
    )
