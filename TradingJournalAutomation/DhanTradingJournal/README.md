# Dhan Trading Journal

Dhan Trading Journal is a local console application for maintaining a personal trading journal, screening Indian equities, and preparing the codebase for historical backtesting.

The application has two separate jobs:

1. Sync executed trades from Dhan into an Excel trading journal.
2. Screen a watchlist using daily OHLCV candles, 200 EMA context, and base-quality rules.

The journal flow can work with Dhan Trading API access. The screener and future backtester require historical candles, which currently come through Dhan's Data API provider.

## Project Structure

```text
TradingJournalAutomation/
  DhanTradingJournal/
    Models/
      HistoricalData.cs
      MatchedTrade.cs
      StockScreenResult.cs
      TradeExecution.cs
    Security/
      DhanCredentialProvider.cs
      DhanCredentials.cs
    Services/
      DhanClient.cs
      DhanHistoricalDataProvider.cs
      ExcelExportService.cs
      FifoTradeMatcher.cs
      IHistoricalDataProvider.cs
      IDhanClient.cs
      JournalSyncService.cs
      ScreenerWorkflow.cs
      StockScreener.cs
      WatchlistProvider.cs
    Program.cs
```

## Credential Model

The app intentionally does not store the Dhan access token in source code.

It expects:

- `DHAN_CLIENT_ID` as a Windows user environment variable.
- Dhan access token typed manually every time the app starts.

Set the client ID once from PowerShell:

```powershell
[Environment]::SetEnvironmentVariable("DHAN_CLIENT_ID", "your-client-id", "User")
```

Close and reopen the terminal or IDE after setting it.

At runtime, the app prompts:

```text
Enter Dhan access token:
```

The token is read using hidden console input and is not echoed to the terminal.

## Journal Sync Flow

The journal sync flow is coordinated by `JournalSyncService`.

Flow:

```text
DhanClient.GetTrades
  -> TradeExecution models
  -> FifoTradeMatcher
  -> MatchedTrade models
  -> ExcelExportService
  -> D:\TradingJournal\MasterJournal.xlsx
```

The `Trades` sheet stores raw executions.

The `MatchedTrades` sheet stores FIFO-matched closed trades with:

- Entry price
- Exit price
- Quantity
- Gross P&L
- Charges
- Net P&L
- Buy time
- Sell time
- Holding days
- Trade Type (Swing/Positional, preserved on sync for manual entry)
- Stop-loss column for manual entry
- Risk amount formula
- R-multiple formula
- Observation columns for post-exit review

Existing matched trades are updated in place without overwriting manual values (Trade Type, stop-loss, grade, notes, and observations).

Three dedicated `Stats` sheets provide automated performance metrics for each category:
- **`Stats - All Trades`**: Complete historical portfolio performance.
- **`Stats - Swing`**: Dedicated metrics dynamically filtered for trades marked as `Swing`.
- **`Stats - Positional`**: Dedicated metrics dynamically filtered for trades marked as `Positional`.

Key metrics calculated dynamically via Excel formulas:
- Total, Profitable, and Losing Trades
- Win Rate (System Accuracy)
- Max Profit & Max Loss
- Profit Factor
- Average Gain, Average Loss, and Risk-Reward (RR)
- Mean, Median, Standard Deviation, and Skewness
- Trade Expectancy (R)
- Average Holding Days (Winners vs. Losers)

## FIFO Trade Matching

`FifoTradeMatcher` matches BUY and SELL executions per symbol in chronological order.

It handles partial exits by matching sell quantity against the oldest open buy quantity first.

After matching, it consolidates split exits from the same entry into one row using:

- Symbol
- Entry price
- Buy date

This keeps the journal readable when one position exits across multiple sell executions.

## Screener Flow

The screener flow is coordinated by `ScreenerWorkflow`.

Flow:

```text
WatchlistProvider
  -> StockScreener
  -> IHistoricalDataProvider
  -> StockScreenResult
  -> ExcelExportService
```

The current watchlist lives in:

```text
Services/WatchlistProvider.cs
```

Each instrument needs:

- `SecurityId`
- `Symbol`
- `ExchangeSegment`

Example:

```csharp
new() { SecurityId = "11536", Symbol = "TATASTEEL", ExchangeSegment = "NSE_EQ" }
```

## Screener Rules

The screener fetches roughly one year of daily candles and evaluates:

- ATH within the last 63 trading days, with 0.5% tolerance.
- Current price above 200 EMA.
- 200 EMA rising versus 10 trading days ago.
- Current price within +/-10% of 200 EMA.

If the mandatory rules pass, it scores base quality out of 6:

- Base range <= 15%
- Base volume less than 50% of prior trend volume
- At least 2 higher lows inside the base
- Price within 3% of 200 EMA support
- Calm candles
- Multiple support touches

Grades:

- `A`: mandatory rules pass and base score is 6
- `B`: mandatory rules pass and base score is 4 or 5
- `WAIT`: mandatory rules pass but base score is below 4
- `FAIL`: mandatory rules do not pass

## Historical Data Provider

The app now separates historical candle data behind this interface:

```csharp
public interface IHistoricalDataProvider
{
    Task<List<HistoricalCandle>> GetDailyCandles(
        ScreenerInstrument instrument,
        DateTime from,
        DateTime to);
}
```

`StockScreener` depends on `IHistoricalDataProvider`, not directly on Dhan.

This means the same screener and future backtester can use different data sources:

- `DhanHistoricalDataProvider`
- `CsvHistoricalDataProvider`
- future cached local database provider

The active provider is selected in `Program.cs`:

```csharp
var historicalDataProvider = new CsvHistoricalDataProvider(
    Path.Combine(AppContext.BaseDirectory, "Data", "Historical", "Yahoo"));
var screenerWorkflow = new ScreenerWorkflow(
    new StockScreener(historicalDataProvider),
    excelExportService);
```

To add another provider later, create a new class that implements `IHistoricalDataProvider`, then replace that one construction line.

Example shape:

```csharp
public class CsvHistoricalDataProvider : IHistoricalDataProvider
{
    public Task<List<HistoricalCandle>> GetDailyCandles(
        ScreenerInstrument instrument,
        DateTime from,
        DateTime to)
    {
        // Load candles from local CSV files.
    }
}
```

## Yahoo CSV Cache

The recommended historical-data flow is:

```text
Python downloader
  -> Yahoo Finance / yfinance
  -> local CSV cache
  -> CsvHistoricalDataProvider
  -> screener and future backtester
```

The downloader script is:

```text
Tools/download_yahoo_history.py
```

It reads:

```text
Data/Watchlists/nifty500.csv
```

and writes one CSV per Yahoo symbol:

```text
Data/Historical/Yahoo/RELIANCE.NS.csv
Data/Historical/Yahoo/TATASTEEL.NS.csv
```

Each historical CSV uses this format:

```csv
Date,Open,High,Low,Close,Volume
2024-01-01,100,105,99,104,1234567
```

Install Python dependencies:

```powershell
py -m pip install yfinance pandas
```

Test with the first 5 stocks:

```powershell
py .\TradingJournalAutomation\DhanTradingJournal\Tools\download_yahoo_history.py --limit 5 --start 2019-01-01
```

Download all Nifty 500 history:

```powershell
py .\TradingJournalAutomation\DhanTradingJournal\Tools\download_yahoo_history.py --start 2019-01-01
```

After the cache exists, run the C# app normally. The stock screener will read from `Data/Historical/Yahoo` instead of calling Dhan's paid historical data API.

## Why Historical Data Matters

Historical data turns the system from a live-only journal into a research engine.

It can validate:

- Win rate of 200 EMA base breakout setups
- Average winner and loser R-multiple
- Base score thresholds
- Whether +/-5% or +/-10% around 200 EMA works better
- Market mode rules, such as avoiding trades when Nifty is weak
- Re-entry rules after stop-outs
- Trailing stop behavior
- Sector rotation patterns
- Portfolio drawdowns and loss streaks

The live 30-trade experiment validates execution discipline. Historical backtesting validates whether the strategy has structural expectancy.

## Current Limitation

Dhan historical candles require Data API access. If the account is not subscribed, the screener will show an error similar to:

```text
Historical fetch failed ... User has not subscribed to Data APIs
```

Journal sync can still work if Trading API access is available.

## Build

From the repository root:

```powershell
dotnet build .\TradingSystem.sln
```

Expected result:

```text
Build succeeded.
0 Warning(s)
0 Error(s)
```

## Run

From the project folder:

```powershell
dotnet run --project .\TradingJournalAutomation\DhanTradingJournal\DhanTradingJournal.csproj
```

Menu:

```text
1 - Sync journal
2 - Run stock screener
3 - Both
```

Output workbook:

```text
D:\TradingJournal\MasterJournal.xlsx
```

## Next Backtesting Direction

The next natural step is to add a `Backtesting` workflow that reuses:

- `IHistoricalDataProvider`
- `HistoricalCandle`
- `StockScreener.CalculateEma`
- base scoring logic
- Excel export

Initial backtest scope:

- One symbol
- Long-only
- 200 EMA base breakout
- fixed initial stop
- fixed R exit or trailing stop
- export each simulated trade with R-multiple

After that, add:

- market mode filter
- re-entry validation
- sector index filters
- portfolio simulation
