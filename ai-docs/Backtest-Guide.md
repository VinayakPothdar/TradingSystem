# Swing Strategy Backtesting Engine — User Guide
### How to Configure, Tweak & Experiment Across Nifty 500 Stocks

---

## 1. Architecture Overview

The backtesting system is built with a **Configuration-Driven Architecture**. You **never** have to write or modify Python code to test new ideas or tweak rules.

```text
[ Strategy-Playbook.md ]  <--- Documents the trading philosophy & chart visuals
         │
         ▼
[ strategy_config.yaml ]  <--- THE CONTROL DASHBOARD (Edit parameters in seconds)
         │
         ▼
[ backtest_engine.py ]    <--- Execution engine (Applies math, trailing SL, P&L)
         │
         ▼
[ run_backtest.py ]       <--- Runs test across 535 stocks & prints performance report
         │
         ▼
[ backtest_trades_log.csv ] <--- Full trade-by-trade audit log with exact entry/exit/R
```

---

## 2. Where the Files Live

| File | Path | Purpose |
| :--- | :--- | :--- |
| **Config File** | [strategy_config.yaml](file:///d:/TradingSystem/Backtesting/strategy_config.yaml) | **The primary file you edit** to change rules or test variations. |
| **Runner Script** | [run_backtest.py](file:///d:/TradingSystem/Backtesting/run_backtest.py) | Executes the test and displays the summary report. |
| **Engine Code** | [backtest_engine.py](file:///d:/TradingSystem/Backtesting/backtest_engine.py) | Reusable simulation logic (data loader, indicator math, execution). |
| **Trade Audit Log** | `d:\TradingSystem\Backtesting\backtest_trades_log.csv` | Exported list of every trade generated with entry, exit, P&L, and R. |

---

## 3. How to Tweak Strategy Parameters

Open [strategy_config.yaml](file:///d:/TradingSystem/Backtesting/strategy_config.yaml) in your editor. Every parameter has clear, plain-English comments:

### A. Testing 50 EMA vs. 200 EMA Support
If you want to test whether catching momentum pullbacks at the **50 EMA** outperforms deep pullbacks at the **200 EMA**:
```yaml
# To test 200 EMA (Deep structural reset):
support_ema: 200
ath_lookback_days: 180
require_primary_trend_above_200: true

# To test 50 EMA (Intermediate momentum pullback):
support_ema: 50
ath_lookback_days: 90                  # Shorter lookback for fast leaders
require_primary_trend_above_200: true  # Ensures stock is still in Stage 2 uptrend
```

### B. Testing 1st Bounce vs. Allowing 2nd/3rd Bounces
To see how much the edge decays if you take 2nd or 3rd bounces:
```yaml
# Only pristine 1st tests (A+ setups):
max_allowed_bounces: 1

# Allow 1st and 2nd tests:
max_allowed_bounces: 2

# Allow any bounce (baseline without exhaustion filter):
max_allowed_bounces: 99
```

### C. Testing Profit Targets (2.0R vs. 2.5R vs. 3.0R)
To test whether banking profits earlier or letting them stretch higher works best:
```yaml
# Current baseline:
target_1_r: 2.0
target_1_size_pct: 0.50     # Book 50%

# Test stretching Target 1:
target_1_r: 2.5
target_1_size_pct: 0.50
```

### D. Testing the Breakeven Trigger
To see the mathematical impact of moving SL to breakeven at $+1.5\text{R}$:
```yaml
# Standard Breakeven rule:
breakeven_trigger_r: 1.5

# Tighter breakeven (at +1.0R):
breakeven_trigger_r: 1.0

# Disable Breakeven (let full SL ride):
breakeven_trigger_r: 999.0
```

### E. Testing Market Timing (Nifty Filter)
```yaml
# Only buy during Nifty pullback/reset (slingshot mode):
enable_nifty_filter: true
nifty_condition: "pullback"

# Buy whenever Nifty is above 200 EMA:
enable_nifty_filter: true
nifty_condition: "above_200"

# No market filter (test stock-only setups):
enable_nifty_filter: false
```

---

## 4. How to Run the Backtest

Whenever you want to run the backtest or test a new configuration, you can either:
1. **Ask the Agent**: *"Run the backtest with the current config"* or *"Change support to 50 EMA and run the backtest"*.
2. **Run from Terminal**:
   ```powershell
   & "C:\Users\LENOVO\AppData\Local\Python\bin\python.exe" "d:\TradingSystem\Backtesting\run_backtest.py"
   ```

The script scans all 535 stocks in ~30–45 seconds and outputs:
* **Total Completed Trades & Win Rate**
* **Target 1 (+2.0R) Hit Rate**
* **Total Realized R-Multiple & Expectancy**
* **Profit Factor & Average Holding Days**
* **Exit Reason Breakdown (StopLoss vs. Breakeven vs. TrailSL)**
* **Runner Distribution (How many peaked $\ge +3\text{R}, +5\text{R}, +7\text{R}$)**
* **Detailed CSV export** saved to `d:\TradingSystem\Backtesting\backtest_trades_log.csv`
