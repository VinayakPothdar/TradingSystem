"""
Telegram Bot Notification Module:
Formats and sends the Unified Daily 6:00 PM Digest to the user's phone.
Supports rich Markdown/HTML styling for 50 DEMA (@ ₹1k) and 200 EMA (@ ₹2k).
"""

import os
from typing import List, Optional
import requests

from engine.gatekeeper import GatekeeperReport
from engine.scanner import ScanResult


def format_telegram_digest(
    results: List[ScanResult],
    gatekeeper: Optional[GatekeeperReport] = None,
    dashboard_url: str = "https://avp-trading.streamlit.app",
) -> str:
    """Formats scan results into a clean, professional Telegram message."""
    date_str = results[0].last_candle_date if results else "Today"

    # Header & Market Regime
    lines = [
        f"🚀 *SWING SCANNER DIGEST — {date_str}*",
    ]

    if gatekeeper:
        lines.append(f"🛡️ *Market Regime*: {gatekeeper.headline} (Score: {gatekeeper.score}/10)")
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    dema50_setups = [r for r in results if r.strategy_id == "50_DEMA"]
    ema200_setups = [r for r in results if r.strategy_id == "200_EMA"]

    # 1. 50 DEMA Section
    lines.append("🔥 *50 DEMA HIGH-MOMENTUM SWINGS* (1R = ₹1,000)")
    if dema50_setups:
        for r in dema50_setups[:5]:  # Top 5
            grade_badge = "🟢 *Grade A+ (Confirmed HL)*" if r.grade == "A+" else "🟡 *Grade A (First-Touch)*"
            lines.append(
                f"\n📌 *{r.symbol}* — {grade_badge}\n"
                f"• *Pattern*: {r.pattern_summary}\n"
                f"• *50 DEMA Respect*: {r.respect_score_pct}% ({r.respect_grade})\n"
                f"• *Buy Above*: ₹{r.entry_price:,.2f} (Stop-Limit)\n"
                f"• *Stop-Loss*: ₹{r.stop_loss_price:,.2f} ({r.risk_pct:.1f}% risk)\n"
                f"• *1R Sizing*: *{r.quantity} shares* (Risk: ₹{r.actual_risk_amount:,.0f})\n"
                f"• *BE Trigger (+1.5R)*: ₹{r.breakeven_trigger_price:,.2f} | *Target (+2R)*: ₹{r.target_price:,.2f}"
            )
    else:
        lines.append("*(No qualifying 50 DEMA setups today)*")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")

    # 2. 200 EMA Section
    lines.append("🛡️ *200 EMA DEEP VALUE SWINGS* (1R = ₹2,000)")
    if ema200_setups:
        for r in ema200_setups[:5]:  # Top 5
            grade_badge = "🟢 *Grade A+ (Confirmed HL)*" if r.grade == "A+" else "🟡 *Grade A (First-Touch)*"
            lines.append(
                f"\n📌 *{r.symbol}* — {grade_badge}\n"
                f"• *Pattern*: {r.pattern_summary}\n"
                f"• *200 EMA Respect*: {r.respect_score_pct}% ({r.respect_grade})\n"
                f"• *Buy Above*: ₹{r.entry_price:,.2f} (Stop-Limit)\n"
                f"• *Stop-Loss*: ₹{r.stop_loss_price:,.2f} ({r.risk_pct:.1f}% risk)\n"
                f"• *1R Sizing*: *{r.quantity} shares* (Risk: ₹{r.actual_risk_amount:,.0f})\n"
                f"• *BE Trigger (+1.5R)*: ₹{r.breakeven_trigger_price:,.2f} | *Target (+2R)*: ₹{r.target_price:,.2f}"
            )
    else:
        lines.append("*(No qualifying 200 EMA setups today)*")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📱 [Open Mobile Dashboard]({dashboard_url})")

    return "\n".join(lines)


def send_telegram_message(
    message: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """
    Sends message to Telegram via Bot API.
    Reads token & chat_id from environment variables if not provided.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat:
        print("[WARN] Telegram Bot Token or Chat ID not configured. Message preview:")
        print(message)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            print("[INFO] Telegram notification sent successfully!")
            return True
        else:
            print(f"[ERROR] Failed to send Telegram message: {resp.status_code} | {resp.text}")
            return False
    except Exception as ex:
        print(f"[ERROR] Telegram request failed: {ex}")
        return False
