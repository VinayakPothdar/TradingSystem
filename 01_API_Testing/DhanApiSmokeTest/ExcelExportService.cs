using ClosedXML.Excel;
using DhanApiSmokeTest.Models;

namespace DhanApiSmokeTest.Services;

public class ExcelExportService
{
    private readonly string _folder = @"D:\TradingJournal";
    private readonly string _filePath;

    public ExcelExportService()
    {
        Directory.CreateDirectory(_folder);
        _filePath = Path.Combine(_folder, "MasterJournal.xlsx");
    }

    // =========================================================
    // RAW TRADES
    // =========================================================

    public void SyncTrades(List<TradeExecution> executions)
    {
        using var workbook = OpenOrCreateWorkbook();

        var worksheet = GetOrCreateWorksheet(
            workbook,
            "Trades",
            CreateTradeHeaders);

        var existingTradeIds = ReadExistingTradeIds(worksheet);

        int lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;
        int inserted = 0;

        foreach (var trade in executions)
        {
            var tradeId = BuildExecutionId(trade);

            if (existingTradeIds.Contains(tradeId))
                continue;

            int row = ++lastRow;

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

        Console.WriteLine($"\n✅ Trades Sync Complete | Inserted: {inserted}");
    }

    // =========================================================
    // MATCHED TRADES
    // =========================================================

    public void ExportMatchedTrades(List<MatchedTrade> matchedTrades)
    {
        using var workbook = OpenOrCreateWorkbook();

        var worksheet = GetOrCreateWorksheet(
            workbook,
            "MatchedTrades",
            CreateMatchedTradeHeaders);

        var existingIds = ReadExistingTradeIds(worksheet);

        int lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;

        int inserted = 0;
        int updated = 0;

        foreach (var trade in matchedTrades)
        {
            bool exists = existingIds.Contains(trade.TradeId);

            int row = exists
                ? FindRow(worksheet, trade.TradeId)
                : ++lastRow;

            if (exists)
                updated++;
            else
            {
                inserted++;
                existingIds.Add(trade.TradeId);
            }

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
        }

        SafeSave(workbook);

        Console.WriteLine($"\n✅ MatchedTrades Sync Complete | Inserted: {inserted} | Updated: {updated}");
    }

    // =========================================================
    // SAFETY SAVE (ATOMIC)
    // =========================================================

    private void SafeSave(XLWorkbook workbook)
    {
        var tempPath = Path.Combine(
            Path.GetDirectoryName(_filePath)!,
            "MasterJournal_temp.xlsx"
        );

        workbook.SaveAs(tempPath);

        if (File.Exists(_filePath))
            File.Delete(_filePath);

        File.Move(tempPath, _filePath);
    }

    // =========================================================
    // HELPERS
    // =========================================================

    private XLWorkbook OpenOrCreateWorkbook()
    {
        return File.Exists(_filePath)
            ? new XLWorkbook(_filePath)
            : new XLWorkbook();
    }

    private IXLWorksheet GetOrCreateWorksheet(
        XLWorkbook workbook,
        string sheetName,
        Action<IXLWorksheet> createHeaders)
    {
        if (workbook.Worksheets.Any(x => x.Name == sheetName))
            return workbook.Worksheet(sheetName);

        var ws = workbook.Worksheets.Add(sheetName);
        createHeaders(ws);
        return ws;
    }

    private HashSet<string> ReadExistingTradeIds(IXLWorksheet ws)
    {
        var set = new HashSet<string>();

        int lastRow = ws.LastRowUsed()?.RowNumber() ?? 1;

        for (int i = 2; i <= lastRow; i++)
        {
            var id = ws.Cell(i, 1).GetString();

            if (!string.IsNullOrWhiteSpace(id))
                set.Add(id);
        }

        return set;
    }

    private int FindRow(IXLWorksheet ws, string tradeId)
    {
        int lastRow = ws.LastRowUsed()?.RowNumber() ?? 1;

        for (int i = 2; i <= lastRow; i++)
        {
            if (ws.Cell(i, 1).GetString() == tradeId)
                return i;
        }

        return lastRow + 1;
    }

    private static string BuildExecutionId(TradeExecution t)
    {
        return $"{t.OrderId}|{t.Symbol}|{t.TransactionType}|{t.Price}|{t.Quantity}|{t.Time:O}";
    }

    private void SetDate(IXLWorksheet ws, int row, int col, DateTime dt)
    {
        ws.Cell(row, col).Value = dt;
        ws.Cell(row, col).Style.DateFormat.Format = "dd MMM yyyy HH:mm";
    }

    // =========================================================
    // HEADERS
    // =========================================================

    private void CreateTradeHeaders(IXLWorksheet ws)
    {
        ws.Cell(1, 1).Value = "TradeId";
        ws.Cell(1, 2).Value = "OrderId";
        ws.Cell(1, 3).Value = "Symbol";
        ws.Cell(1, 4).Value = "TransactionType";
        ws.Cell(1, 5).Value = "Price";
        ws.Cell(1, 6).Value = "Quantity";
        ws.Cell(1, 7).Value = "STT";
        ws.Cell(1, 8).Value = "Brokerage";
        ws.Cell(1, 9).Value = "ExchangeCharges";
        ws.Cell(1, 10).Value = "StampDuty";
        ws.Cell(1, 11).Value = "ServiceTax";
        ws.Cell(1, 12).Value = "TotalCharges";
        ws.Cell(1, 13).Value = "ExchangeTime";
    }

    private void CreateMatchedTradeHeaders(IXLWorksheet ws)
    {
        ws.Cell(1, 1).Value = "TradeId";
        ws.Cell(1, 2).Value = "Symbol";
        ws.Cell(1, 3).Value = "EntryPrice";
        ws.Cell(1, 4).Value = "ExitPrice";
        ws.Cell(1, 5).Value = "Quantity";
        ws.Cell(1, 6).Value = "GrossPnL";
        ws.Cell(1, 7).Value = "Charges";
        ws.Cell(1, 8).Value = "NetPnL";
        ws.Cell(1, 9).Value = "BuyTime";
        ws.Cell(1, 10).Value = "SellTime";
        ws.Cell(1, 11).Value = "HoldingDays";
    }
}