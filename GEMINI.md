# Workspace Rules & Permissions — TradingSystem

## 1. Risk Modeling & Stop-Loss (1R = ₹1,000)
* **Default 1R Risk**: The trader risks a fixed **₹1,000 per trade (1R = ₹1k)** across all swing trades (~0.5% of active capital).
* **Automatic Stop-Loss (SL) Computation**:
  * Manual entry of StopLossPrice is optional.
  * When `StopLossPrice` is not provided:
    * Implied 1R risk per share = `₹1,000 / Quantity`
    * Implied Stop-Loss Price = `EntryPrice - (₹1,000 / Quantity)`
    * Realized R-Multiple = `NetPnL / 1,000`
    * Max Favorable Excursion (Peak R) = `((PeakPrice - EntryPrice) * Quantity) / 1,000`
    * Max Adverse Excursion (Heat R) = `((TroughPrice - EntryPrice) * Quantity) / 1,000`
  * When `StopLossPrice` is explicitly provided, use `EntryPrice - StopLossPrice` for per-share risk.
* **Round-Trip Failure Rule**: A trade is diagnosed as a round-trip failure if and only if:
  $$\text{Net PnL} < 0 \quad \text{AND} \quad \text{Peak R} \ge 1.5\text{R}$$

## 2. File Access Permissions & Default Paths
* **Master Journal**: Full read/write access is granted to `D:\TradingJournal\MasterJournal.xlsx`.
* **Historical Candle CSVs**: Full read/write access is granted to all stock and index candle CSV files in:
  * `d:\TradingSystem\TradingJournalAutomation\DhanTradingJournal\Data\Historical\Yahoo\*.csv`
  * `d:\TradingSystem\TradingJournalAutomation\DhanTradingJournal\bin\Debug\net8.0\Data\Historical\Yahoo\*.csv`
* **Watchlists & Aliases**: Full read/write access is granted to:
  * `d:\TradingSystem\TradingJournalAutomation\DhanTradingJournal\Data\Watchlists\*.csv`

## 3. Excel Process Termination Permission
* **Explicit Permission Granted**: Whenever `MasterJournal.xlsx` is open or locked by Microsoft Excel (`EXCEL.EXE`), the agent and automation tools have permission to terminate `EXCEL.EXE` (`taskkill /F /IM excel.exe`) to obtain uninterrupted read/write access.
