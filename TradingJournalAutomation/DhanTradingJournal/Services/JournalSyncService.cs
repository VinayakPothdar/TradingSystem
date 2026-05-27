namespace DhanTradingJournal.Services;

public class JournalSyncService
{
    private readonly IDhanClient _dhanClient;
    private readonly FifoTradeMatcher _tradeMatcher;
    private readonly ExcelExportService _excelExportService;

    public JournalSyncService(
        IDhanClient dhanClient,
        FifoTradeMatcher tradeMatcher,
        ExcelExportService excelExportService)
    {
        _dhanClient = dhanClient;
        _tradeMatcher = tradeMatcher;
        _excelExportService = excelExportService;
    }

    public async Task Run(DateOnly fromDate, DateOnly toDate)
    {
        Console.WriteLine("JOURNAL SYNC");
        Console.WriteLine("--------------------------------------\n");
        Console.WriteLine("Fetching trades from Dhan API...\n");

        var allExecutions = await _dhanClient.GetTrades(fromDate, toDate);
        Console.WriteLine($"\nTotal executions fetched: {allExecutions.Count}");

        var matchedTrades = _tradeMatcher.MatchTrades(allExecutions);
        Console.WriteLine($"Matched trades (consolidated): {matchedTrades.Count}");

        PrintSummary(matchedTrades);

        _excelExportService.SyncTrades(allExecutions);
        _excelExportService.ExportMatchedTrades(matchedTrades);
        _excelExportService.BackfillRMultipleFormulas();
    }

    private static void PrintSummary(IEnumerable<Models.MatchedTrade> matchedTrades)
    {
        Console.WriteLine("\n===== MATCHED TRADES SUMMARY =====\n");

        foreach (var trade in matchedTrades)
        {
            var pnlSign = trade.NetPnL >= 0 ? "WIN" : "LOSS";
            Console.WriteLine($"{pnlSign,-4} {trade.Symbol,-25} | " +
                              $"Entry: {trade.EntryPrice,8:F2} -> Exit: {trade.ExitPrice,8:F2} | " +
                              $"Qty: {trade.Quantity,4} | " +
                              $"Net P&L: {trade.NetPnL,10:F2} | " +
                              $"Days: {Math.Ceiling(trade.HoldingDays)}");
        }
    }
}
