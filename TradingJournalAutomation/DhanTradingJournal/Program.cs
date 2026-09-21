using DhanTradingJournal.Security;
using DhanTradingJournal.Services;

Console.WriteLine("Dhan Trading Journal & Historical Data Engine");
Console.WriteLine("=============================================\n");

var excelExportService = new ExcelExportService();
var historicalDataProvider = new CsvHistoricalDataProvider(
    Path.Combine(AppContext.BaseDirectory, "Data", "Historical", "Yahoo"));
var screenerWorkflow = new ScreenerWorkflow(
    new StockScreener(historicalDataProvider),
    excelExportService);
var tradeReviewService = new TradeReviewService();
var candleSyncService = new HistoricalDataSyncService();

Console.WriteLine("What would you like to do?");
Console.WriteLine("  1 - Sync Dhan Journal (Orders & Trades)");
Console.WriteLine("  2 - Run Stock Screener (A/B Setup Scanner)");
Console.WriteLine("  3 - Both (Sync Dhan Journal & Screener)");
Console.WriteLine("  4 - Review & Autopsy Swing Trades (30-Trade Block)");
Console.WriteLine("  5 - Full Run (Sync Journal -> Review Autopsy)");
Console.WriteLine("  -------------------------------------------------------------");
Console.WriteLine("  Historical Candle Sync (Yahoo Finance):");
Console.WriteLine("  6 - Sync Traded Stocks from MatchedTrades");
Console.WriteLine("  7 - Sync All Market Indices (31 NSE Broad & Sectoral Indices)");
Console.WriteLine("  8 - Sync Custom Stocks (Enter comma-separated tickers)");
Console.WriteLine("  9 - Sync All Stocks (Nifty 500 Universe)");
Console.WriteLine("  10 - Sync Both Indices + Traded Stocks");
Console.Write("\nEnter choice (1-10): ");

var choice = Console.ReadLine()?.Trim() ?? "4";
Console.WriteLine();

try
{
    if (choice is "1" or "3" or "5")
    {
        var credentials = DhanCredentialProvider.GetCredentials();
        if (string.IsNullOrWhiteSpace(credentials.ClientId) ||
            string.IsNullOrWhiteSpace(credentials.AccessToken))
        {
            return;
        }

        using var httpClient = new HttpClient();
        IDhanClient dhanClient = new DhanClient(httpClient, credentials.AccessToken, credentials.ClientId);
        var journalSyncService = new JournalSyncService(
            dhanClient,
            new FifoTradeMatcher(),
            excelExportService);

        var fromDate = new DateOnly(2026, 4, 1);
        var toDate = DateOnly.FromDateTime(DateTime.Today);
        await journalSyncService.Run(fromDate, toDate);
    }

    if (choice is "2" or "3")
    {
        await screenerWorkflow.Run();
    }

    if (choice is "4" or "5")
    {
        excelExportService.BackfillRMultipleFormulas();
        var (results, summary) = tradeReviewService.RunReview("Swing");
        excelExportService.ExportTradeReview(results, summary, "TradeReview - Swing", "Swing Trading");
    }

    if (choice == "6")
    {
        candleSyncService.RunSync("matched");
    }

    if (choice == "7")
    {
        candleSyncService.RunSync("indices");
    }

    if (choice == "8")
    {
        Console.Write("Enter comma-separated stock symbols (e.g. BEL, TVSMOTOR, RELIANCE): ");
        var symbols = Console.ReadLine()?.Trim() ?? "";
        if (!string.IsNullOrWhiteSpace(symbols))
        {
            candleSyncService.RunSync("custom", symbols);
        }
        else
        {
            Console.WriteLine("No symbols entered. Aborting custom sync.");
        }
    }

    if (choice == "9")
    {
        candleSyncService.RunSync("all");
    }

    if (choice == "10")
    {
        candleSyncService.RunSync("both");
    }
}
catch (Exception ex)
{
    Console.WriteLine($"\nRun failed: {ex.Message}");
}

Console.WriteLine("\n====================");
Console.WriteLine("Done - check D:\\TradingJournal\\MasterJournal.xlsx");
