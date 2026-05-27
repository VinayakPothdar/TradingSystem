using ClosedXML.Excel;
using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public class ExcelExportService
{
    private readonly string _folder = @"D:\TradingJournal";
    private readonly string _filePath;

    public ExcelExportService()
    {
        Directory.CreateDirectory(_folder);
        _filePath = Path.Combine(_folder, "MasterJournal.xlsx");
    }

    public void SyncTrades(List<TradeExecution> executions)
    {
        using var workbook = OpenOrCreateWorkbook();
        var worksheet = GetOrCreateWorksheet(workbook, "Trades", CreateTradeHeaders);
        var existingTradeIds = ReadExistingTradeIds(worksheet);

        var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;
        var inserted = 0;

        foreach (var trade in executions)
        {
            var tradeId = BuildExecutionId(trade);
            if (existingTradeIds.Contains(tradeId))
                continue;

            var row = ++lastRow;
            worksheet.Cell(row, 1).Value = tradeId;
            worksheet.Cell(row, 2).Value = trade.OrderId;
            worksheet.Cell(row, 3).Value = trade.Symbol;
            worksheet.Cell(row, 4).Value = trade.TransactionType;
            worksheet.Cell(row, 5).Value = trade.Price;
            worksheet.Cell(row, 6).Value = trade.Quantity;
            worksheet.Cell(row, 7).Value = trade.Stt;
            worksheet.Cell(row, 8).Value = trade.Brokerage;
            worksheet.Cell(row, 9).Value = trade.ExchangeCharges;
            worksheet.Cell(row, 10).Value = trade.StampDuty;
            worksheet.Cell(row, 11).Value = trade.ServiceTax;
            worksheet.Cell(row, 12).Value =
                trade.Stt + trade.Brokerage + trade.ExchangeCharges + trade.StampDuty + trade.ServiceTax;
            SetDate(worksheet, row, 13, trade.Time);

            existingTradeIds.Add(tradeId);
            inserted++;
        }

        SafeSave(workbook);
        Console.WriteLine($"\nTrades sync complete | Inserted: {inserted}");
    }

    public void ExportMatchedTrades(List<MatchedTrade> matchedTrades)
    {
        using var workbook = OpenOrCreateWorkbook();
        var worksheet = GetOrCreateWorksheet(workbook, "MatchedTrades", CreateMatchedTradeHeaders);
        var existingIds = ReadExistingTradeIds(worksheet);

        var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;
        var inserted = 0;
        var existing = 0;

        foreach (var trade in matchedTrades)
        {
            if (existingIds.Contains(trade.TradeId))
            {
                existing++;
                continue;
            }

            var row = ++lastRow;
            inserted++;
            existingIds.Add(trade.TradeId);

            worksheet.Cell(row, 1).Value = trade.TradeId;
            worksheet.Cell(row, 2).Value = trade.Symbol;
            worksheet.Cell(row, 3).Value = trade.EntryPrice;
            worksheet.Cell(row, 4).Value = trade.ExitPrice;
            worksheet.Cell(row, 5).Value = trade.Quantity;
            worksheet.Cell(row, 6).Value = trade.GrossPnL;
            worksheet.Cell(row, 7).Value = trade.Charges;
            worksheet.Cell(row, 8).Value = trade.NetPnL;
            SetDate(worksheet, row, 9, trade.BuyTime);
            SetDate(worksheet, row, 10, trade.SellTime);
            worksheet.Cell(row, 11).Value = Math.Ceiling(trade.HoldingDays);
            worksheet.Cell(row, 13).FormulaA1 = $"=IF(L{row}=\"\", \"\", C{row}-L{row})";
            worksheet.Cell(row, 14).FormulaA1 = $"=IF(L{row}=\"\",\"\",H{row}/((C{row}-L{row})*E{row}))";
        }

        worksheet.Columns().AdjustToContents();
        ApplyRMultipleFormatting(worksheet);

        SafeSave(workbook);
        Console.WriteLine($"\nMatchedTrades sync complete | Inserted: {inserted} | Existing: {existing}");
    }

    public void ExportScreenerResults(List<StockScreenResult> results)
    {
        using var workbook = OpenOrCreateWorkbook();
        var sheetName = $"Scan_{DateTime.Today:yyyy-MM-dd}";

        if (workbook.Worksheets.Any(x => x.Name == sheetName))
            workbook.Worksheet(sheetName).Delete();

        var worksheet = workbook.Worksheets.Add(sheetName);
        CreateScreenerHeaders(worksheet);

        var row = 2;
        foreach (var result in results)
        {
            worksheet.Cell(row, 1).Value = result.Grade;
            worksheet.Cell(row, 2).Value = result.Symbol;
            worksheet.Cell(row, 3).Value = result.CurrentPrice;
            worksheet.Cell(row, 4).Value = result.Ema200;
            worksheet.Cell(row, 5).Value = result.PriceVsEma200Pct;
            worksheet.Cell(row, 6).Value = ToYesNo(result.AthWithin63Days);
            worksheet.Cell(row, 7).Value = ToYesNo(result.AboveEma200);
            worksheet.Cell(row, 8).Value = ToYesNo(result.Ema200Rising);
            worksheet.Cell(row, 9).Value = ToYesNo(result.WithinEmaZone);
            worksheet.Cell(row, 10).Value = result.BaseScore;
            worksheet.Cell(row, 11).Value = ToYesNo(result.BaseTightRange);
            worksheet.Cell(row, 12).Value = ToYesNo(result.BaseVolumeDryUp);
            worksheet.Cell(row, 13).Value = ToYesNo(result.BaseHigherLows);
            worksheet.Cell(row, 14).Value = ToYesNo(result.BaseSupportConfluence);
            worksheet.Cell(row, 15).Value = ToYesNo(result.BaseCalmCandles);
            worksheet.Cell(row, 16).Value = ToYesNo(result.BaseMultipleTouches);

            if (result.PassesMandatoryRules)
                worksheet.Row(row).Style.Fill.BackgroundColor = GetGradeColor(result.Grade);

            row++;
        }

        worksheet.Columns().AdjustToContents();
        SafeSave(workbook);

        var aCount = results.Count(r => r.Grade == StockScreenResultGrades.A);
        var bCount = results.Count(r => r.Grade == StockScreenResultGrades.B);
        Console.WriteLine($"\nScreener export complete | A-grade: {aCount} | B-grade: {bCount} | Sheet: {sheetName}");
    }

    public void BackfillRMultipleFormulas()
    {
        using var workbook = OpenOrCreateWorkbook();

        if (!workbook.Worksheets.Any(x => x.Name == "MatchedTrades"))
        {
            Console.WriteLine("MatchedTrades sheet not found.");
            return;
        }

        var worksheet = workbook.Worksheet("MatchedTrades");
        var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;
        var updated = 0;

        for (var row = 2; row <= lastRow; row++)
        {
            var riskCell = worksheet.Cell(row, 13);
            var rMultipleCell = worksheet.Cell(row, 14);

            if (!string.IsNullOrWhiteSpace(riskCell.FormulaA1))
                continue;

            riskCell.FormulaA1 = $"=IF(L{row}=\"\",\"\",C{row}-L{row})";
            rMultipleCell.FormulaA1 = $"=IF(L{row}=\"\",\"\",H{row}/((C{row}-L{row})*E{row}))";
            updated++;
        }

        ApplyRMultipleFormatting(worksheet);
        SafeSave(workbook);
        Console.WriteLine($"Backfill complete | Rows updated: {updated}");
    }

    private void SafeSave(XLWorkbook workbook)
    {
        var tempPath = Path.Combine(Path.GetDirectoryName(_filePath)!, "MasterJournal_temp.xlsx");

        workbook.SaveAs(tempPath);

        if (File.Exists(_filePath))
            File.Delete(_filePath);

        File.Move(tempPath, _filePath);
    }

    private XLWorkbook OpenOrCreateWorkbook() =>
        File.Exists(_filePath) ? new XLWorkbook(_filePath) : new XLWorkbook();

    private static IXLWorksheet GetOrCreateWorksheet(
        XLWorkbook workbook,
        string sheetName,
        Action<IXLWorksheet> createHeaders)
    {
        if (workbook.Worksheets.Any(x => x.Name == sheetName))
            return workbook.Worksheet(sheetName);

        var worksheet = workbook.Worksheets.Add(sheetName);
        createHeaders(worksheet);
        return worksheet;
    }

    private static HashSet<string> ReadExistingTradeIds(IXLWorksheet worksheet)
    {
        var set = new HashSet<string>();
        var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;

        for (var row = 2; row <= lastRow; row++)
        {
            var id = worksheet.Cell(row, 1).GetString();
            if (!string.IsNullOrWhiteSpace(id))
                set.Add(id);
        }

        return set;
    }

    private static string BuildExecutionId(TradeExecution trade) =>
        $"{trade.OrderId}|{trade.Symbol}|{trade.TransactionType}|{trade.Price}|{trade.Quantity}|{trade.Time:O}";

    private static void SetDate(IXLWorksheet worksheet, int row, int col, DateTime value)
    {
        worksheet.Cell(row, col).Value = value;
        worksheet.Cell(row, col).Style.DateFormat.Format = "dd MMM yyyy HH:mm";
    }

    private static void CreateTradeHeaders(IXLWorksheet worksheet)
    {
        var headers = new[]
        {
            "TradeId", "OrderId", "Symbol", "TransactionType", "Price", "Quantity", "STT",
            "Brokerage", "ExchangeCharges", "StampDuty", "ServiceTax", "TotalCharges", "ExchangeTime"
        };

        WriteHeaders(worksheet, headers);
    }

    private static void CreateMatchedTradeHeaders(IXLWorksheet worksheet)
    {
        var headers = new[]
        {
            "TradeId", "Symbol", "EntryPrice", "ExitPrice", "Quantity", "GrossPnL", "Charges",
            "NetPnL", "BuyTime", "SellTime", "HoldingDays", "StopLossPrice", "RiskAmount",
            "R-Multiple", "Grade (W/L)", "MaxPriceAfterExit", "ObservedTrailR", "Notes"
        };

        WriteHeaders(worksheet, headers);
    }

    private static void CreateScreenerHeaders(IXLWorksheet worksheet)
    {
        var headers = new[]
        {
            "Grade", "Symbol", "Price", "200 EMA", "% vs EMA", "ATH<63d", "Above EMA",
            "EMA Rising", "In Zone", "Base Score", "TightRange", "VolDryUp", "HigherLows",
            "Support", "CalmCandle", "MultiTouch"
        };

        WriteHeaders(worksheet, headers);
    }

    private static void WriteHeaders(IXLWorksheet worksheet, IReadOnlyList<string> headers)
    {
        for (var i = 0; i < headers.Count; i++)
            worksheet.Cell(1, i + 1).Value = headers[i];

        StyleHeaderRow(worksheet);
    }

    private static void StyleHeaderRow(IXLWorksheet worksheet)
    {
        var row = worksheet.Row(1);
        row.Style.Font.Bold = true;
        row.Style.Fill.BackgroundColor = XLColor.FromArgb(27, 42, 74);
        row.Style.Font.FontColor = XLColor.White;
    }

    private static void ApplyRMultipleFormatting(IXLWorksheet worksheet)
    {
        var rMultipleRange = worksheet.Range("N2:N1000");
        rMultipleRange.AddConditionalFormat()
            .WhenIsTrue("N2>0")
            .Fill.SetBackgroundColor(XLColor.FromArgb(198, 239, 206));
        rMultipleRange.AddConditionalFormat()
            .WhenIsTrue("N2<0")
            .Fill.SetBackgroundColor(XLColor.FromArgb(255, 199, 206));
    }

    private static XLColor GetGradeColor(string grade) =>
        grade switch
        {
            StockScreenResultGrades.A => XLColor.FromArgb(198, 239, 206),
            StockScreenResultGrades.B => XLColor.FromArgb(255, 242, 204),
            _ => XLColor.FromArgb(255, 199, 206)
        };

    private static string ToYesNo(bool value) => value ? "Yes" : "No";
}
