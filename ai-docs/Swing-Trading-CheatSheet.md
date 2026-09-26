# Swing Trading Desk Reference Card (1-Pager)
### Level-3 Structural Pullback Framework &bull; Fixed ₹1,000 Risk ($1\text{R}$)

---

## 1. The 10-Second Pre-Flight Test (Binary Go / No-Go)

Before clicking **BUY** on any swing candidate, verify all 5 criteria. If **any** item is NO, the trade is **immediately aborted**:

| \# | Filter Dimension | Requirement | Status |
| :---: | :--- | :--- | :---: |
| **1** | **180-Day All-Time High** | Did the stock print a fresh 52-week All-Time High within the preceding **$\le 180$ trading days**? | [ ] YES |
| **2** | **Top-Down Vector** | Is the price approaching the Support EMA **from above** (healthy pullback from ATH)? *(Approaching from below is strictly disqualified).* | [ ] YES |
| **3** | **First Bounce Rule** | Is this the **1st test** (or valid 2nd bounce with W-base)? *(3rd+ bounce is strictly disqualified).* | [ ] YES |
| **4** | **Base Confirmation** | Has a calm consolidation base of **4 to 12 daily candles** formed with a confirmed higher low (W-pattern)? *(No 1-candle hurry entries).* | [ ] YES |
| **5** | **Market & Sector Confluence** | Is the underlying sector trading **above its 200 EMA**, and has Nifty undergone a **pullback / digestion reset**? | [ ] YES |

---

## 2. The 5 Fatal Red Flags (Instant Disqualification)

If you see any of the following, **skip the stock immediately**:
1. 🚫 **3rd Test Breakdown**: Churning repeatedly at the 200 EMA ($83.3\%$ failure rate in retro).
2. 🚫 **Inverted Test**: Price rising into the 200 EMA from deep below (overhead resistance, not support).
3. 🚫 **Sector Laggard**: Stock trading below its 200 EMA while sector peers are printing highs.
4. 🚫 **Single-Candle Hurry Entry**: Trying to re-enter on a 1-day hammer or green spike without multi-day basing.
5. 🚫 **Never Average Down**: A swing trade is a discrete $1\text{R}$ probability bet. Never add to a losing swing position.

---

## 3. The 2-Gear Execution Matrix

| Setup Type | Support Moving Average | Target 1 Profit Rule | Runner Trailing Rule |
| :--- | :---: | :---: | :---: |
| **Gear 1: Deep Structural Reset** | **Daily 200 EMA** | **Clean 100% Exit at $+2.0\text{R}$** | *None* (Avoids overhead chop; banks $+2\text{R}$ cash in ~29 days). |
| **Gear 2: Momentum Leader** | **Daily 50 EMA** | **Book 50% at $+2.0\text{R}$** | **Trail remaining 50%** behind 20 EMA / base lows (captures $+10\text{R}$ compounders). |

> [!IMPORTANT]
> **Mandatory Round-Trip Protection**:  
> As soon as the trade reaches **$+1.5\text{R}$**, move your Stop-Loss to **Breakeven (Cost + Charges)** immediately. Never let a $+1.5\text{R}$ winning move retrace into a $-1\text{R}$ loss.

---

## 4. Position Sizing & Order Placement Formula

$$\text{Risk per Share} = \text{Entry Price} - \text{Stop Loss Price}$$

$$\text{Quantity to Buy} = \left\lfloor \frac{\text{₹}1,000}{\text{Risk per Share}} \right\rfloor$$

* **Stop Loss Level**: Set slightly below the base pivot low: $\text{Base Low} - (0.3 \times \text{ATR})$.
* **Breakeven Alert Level**: $\text{Entry Price} + (1.5 \times \text{Risk per Share})$.
* **Target 1 (+2.0R Level)**: $\text{Entry Price} + (2.0 \times \text{Risk per Share})$.

---

## 5. Master Autopsy Benchmarks (The Proof)

| Cohort | Trades | Win Rate | Total Net P&L | Total Realized R | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Actual Baseline Journal** | 30 | 36.7% | +₹973.79 | +0.97 R | 1.05 |
| **Filtered Playbook Model** | **18** | **72.2%** | **+₹17,362.68** | **+17.36 R** | **2.84** |

*All 30 trade notes backfilled in [MasterJournal.xlsx](file:///D:/TradingJournal/MasterJournal.xlsx) &bull; Visual dashboard in [Swing-Trade-Review-Dashboard.html](file:///d:/TradingSystem/ai-docs/Swing-Trade-Review-Dashboard.html)*
