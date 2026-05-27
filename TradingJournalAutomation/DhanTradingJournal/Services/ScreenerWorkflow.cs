using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public class ScreenerWorkflow
{
    private readonly StockScreener _stockScreener;
    private readonly ExcelExportService _excelExportService;

    public ScreenerWorkflow(StockScreener stockScreener, ExcelExportService excelExportService)
    {
        _stockScreener = stockScreener;
        _excelExportService = excelExportService;
    }

    public async Task Run()
    {
        Console.WriteLine("\nSTOCK SCREENER");
        Console.WriteLine("--------------------------------------\n");

        var watchlist = WatchlistProvider.GetDefaultWatchlist();

        if (watchlist.Count == 0)
        {
            Console.WriteLine("Watchlist is empty. Add stocks in WatchlistProvider.cs");
            return;
        }

        Console.WriteLine($"Screening {watchlist.Count} stocks...\n");

        var results = await _stockScreener.ScreenAll(watchlist);
        PrintResults(results);

        _excelExportService.ExportScreenerResults(results);
    }

    private static void PrintResults(List<StockScreenResult> results)
    {
        Console.WriteLine("\n===== SCREENER RESULTS =====\n");
        Console.WriteLine($"{"Grade",-10} {"Symbol",-25} {"Price",8} {"EMA200",8} {"% EMA",7} {"Base",5}");
        Console.WriteLine(new string('-', 70));

        foreach (var result in results)
        {
            Console.WriteLine(
                $"{result.Grade,-10} {result.Symbol,-25} " +
                $"{result.CurrentPrice,8:F2} {result.Ema200,8:F2} " +
                $"{result.PriceVsEma200Pct,6:F1}% " +
                $"{result.BaseScore}/6");
        }

        var aGrade = results.Where(r => r.Grade == StockScreenResultGrades.A).ToList();
        var bGrade = results.Where(r => r.Grade == StockScreenResultGrades.B).ToList();

        Console.WriteLine($"\nA-Grade setups: {aGrade.Count}");
        foreach (var result in aGrade)
            Console.WriteLine($"   {result.Symbol} | Base: {result.BaseScore}/6 | Price: {result.CurrentPrice:F2}");

        Console.WriteLine($"\nB-Grade setups: {bGrade.Count}");
        foreach (var result in bGrade)
            Console.WriteLine($"   {result.Symbol} | Base: {result.BaseScore}/6 | Price: {result.CurrentPrice:F2}");
    }
}
