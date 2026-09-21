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
        EnsureMatchedTradeColumns(worksheet);

        // FIX: MatchedTrade.TradeId is built upstream from Symbol+EntryPrice+BuyTime only, so
        // a single buy lot closed across multiple partial exits (e.g. 50% booked at 2R, rest
        // trailed out later) produces multiple MatchedTrade records sharing the SAME TradeId.
        // Rather than writing each leg as its own row (which would double-count a single
        // trade in Stats-sheet metrics like Win Rate/Expectancy), every leg for a given
        // TradeId is aggregated into ONE row: quantities summed, exit price weighted by
        // quantity, PnL summed, and HoldingDays measured to the final exit.
        //
        // The matcher is assumed to return the full matched history on every sync (this is
        // why the original code checked for pre-existing TradeIds at all), so aggregation is
        // recomputed from scratch each run and existing rows are updated in place rather than
        // appended to. Only the auto-computed columns (EntryPrice..HoldingDays) are touched;
        // user-maintained columns (Trade Type, StopLossPrice, Grade, MaxPriceAfterExit, ObservedTrailR,
        // Notes) are never overwritten by the sync.
        var existingRows = ReadExistingMatchedTradeRows(worksheet);

        var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;
        var inserted = 0;
        var updated = 0;

        var groups = matchedTrades.GroupBy(t => t.TradeId);

        foreach (var group in groups)
        {
            var legs = group.OrderBy(l => l.SellTime).ToList();
            var totalQty = legs.Sum(l => l.Quantity);

            var aggregate = new
            {
                TradeId = group.Key,
                Symbol = legs[0].Symbol,
                EntryPrice = legs[0].EntryPrice,
                ExitPrice = legs.Sum(l => l.ExitPrice * l.Quantity) / totalQty,
                Quantity = totalQty,
                GrossPnL = legs.Sum(l => l.GrossPnL),
                Charges = legs.Sum(l => l.Charges),
                NetPnL = legs.Sum(l => l.NetPnL),
                BuyTime = legs[0].BuyTime,
                SellTime = legs[^1].SellTime,
                HoldingDays = Math.Ceiling((legs[^1].SellTime - legs[0].BuyTime).TotalDays)
            };

            int row;
            if (existingRows.TryGetValue(aggregate.TradeId, out var existingRow))
            {
                row = existingRow;
                updated++;
            }
            else
            {
                row = ++lastRow;
                worksheet.Cell(row, 1).Value = aggregate.TradeId;
                worksheet.Cell(row, 2).Value = aggregate.Symbol;
                worksheet.Cell(row, 14).FormulaA1 = $"=IF(M{row}<>\"\", C{row}-M{row}, ROUND(1000/E{row}, 2))";
                worksheet.Cell(row, 15).FormulaA1 = $"=IF(M{row}<>\"\", H{row}/((C{row}-M{row})*E{row}), ROUND(H{row}/1000, 2))";
                inserted++;
            }

            worksheet.Cell(row, 3).Value = aggregate.EntryPrice;
            worksheet.Cell(row, 4).Value = aggregate.ExitPrice;
            worksheet.Cell(row, 5).Value = aggregate.Quantity;
            worksheet.Cell(row, 6).Value = aggregate.GrossPnL;
            worksheet.Cell(row, 7).Value = aggregate.Charges;
            worksheet.Cell(row, 8).Value = aggregate.NetPnL;
            SetDate(worksheet, row, 9, aggregate.BuyTime);
            SetDate(worksheet, row, 10, aggregate.SellTime);
            worksheet.Cell(row, 11).Value = aggregate.HoldingDays;
        }

        worksheet.Columns().AdjustToContents();
        ApplyRMultipleFormatting(worksheet);

        SafeSave(workbook);
        Console.WriteLine($"\nMatchedTrades sync complete | Inserted: {inserted} | Updated: {updated}");
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
        EnsureMatchedTradeColumns(worksheet);
        var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;
        var updated = 0;

        for (var row = 2; row <= lastRow; row++)
        {
            var riskCell = worksheet.Cell(row, 14);
            var rMultipleCell = worksheet.Cell(row, 15);

            riskCell.FormulaA1 = $"=IF(M{row}<>\"\", C{row}-M{row}, ROUND(1000/E{row}, 2))";
            rMultipleCell.FormulaA1 = $"=IF(M{row}<>\"\", H{row}/((C{row}-M{row})*E{row}), ROUND(H{row}/1000, 2))";
            updated++;
        }

        ApplyRMultipleFormatting(worksheet);
        SafeSave(workbook);
        Console.WriteLine($"Backfill complete | Rows updated: {updated}");
    }

    public void EnsureStatsSheets()
    {
        using var workbook = OpenOrCreateWorkbook();

        // Remove legacy combined Stats sheet if present
        var legacyStats = workbook.Worksheets.FirstOrDefault(w => w.Name == "Stats");
        legacyStats?.Delete();

        BuildCategoryStatsSheet(workbook, "Stats - All Trades", "All Trades", null);
        BuildCategoryStatsSheet(workbook, "Stats - Swing", "Swing", "Swing");
        BuildCategoryStatsSheet(workbook, "Stats - Positional", "Positional", "Positional");

        SafeSave(workbook);
        Console.WriteLine("Stats sheets updated: 'Stats - All Trades', 'Stats - Swing', 'Stats - Positional'.");
    }

    public void EnsureStatsSheet() => EnsureStatsSheets();

    public void ExportTradeReview(
        List<TradeReviewResult> results,
        WinnersLosersComparison summary,
        string sheetName = "TradeReview - Swing",
        string categoryTitle = "Swing Trading")
    {
        using var workbook = OpenOrCreateWorkbook();

        // Remove legacy combined TradeReview if present
        var legacy = workbook.Worksheets.FirstOrDefault(w => w.Name == "TradeReview");
        legacy?.Delete();

        var worksheet = workbook.Worksheets.FirstOrDefault(w => w.Name == sheetName)
                        ?? workbook.Worksheets.Add(sheetName);

        worksheet.Clear();

        // 1. Title Block
        worksheet.Cell(1, 1).Value = $"Trade Review & Autopsy Diagnostic — {categoryTitle} ({results.Count}-Trade Block)";
        worksheet.Cell(1, 1).Style.Font.Bold = true;
        worksheet.Cell(1, 1).Style.Font.FontSize = 15;
        worksheet.Cell(1, 1).Style.Font.FontColor = XLColor.FromArgb(27, 42, 74);

        worksheet.Cell(2, 1).Value = $"Quantitative autopsy diagnosing execution quality, MFE/MAE excursion, technical posture, market regime, and post-exit follow-through for {categoryTitle}";
        worksheet.Cell(2, 1).Style.Font.Italic = true;
        worksheet.Cell(2, 1).Style.Font.FontSize = 10;
        worksheet.Cell(2, 1).Style.Font.FontColor = XLColor.FromArgb(90, 90, 90);

        var navyHeader = XLColor.FromArgb(27, 42, 74);
        var winGreen = XLColor.FromArgb(46, 125, 50);
        var lossRed = XLColor.FromArgb(198, 40, 40);
        var softGreen = XLColor.FromArgb(198, 239, 206);
        var softRed = XLColor.FromArgb(255, 199, 206);
        var softYellow = XLColor.FromArgb(255, 242, 204);

        // 2. Winners vs Losers Diagnostic Comparison Table (Row 4)
        worksheet.Cell(4, 1).Value = "Diagnostic Metric";
        worksheet.Cell(4, 2).Value = $"Winners (n = {summary.WinnersCount})";
        worksheet.Cell(4, 3).Value = $"Losers (n = {summary.LosersCount})";
        worksheet.Cell(4, 4).Value = "Diagnostic Delta / Edge Analysis";

        worksheet.Cell(4, 1).Style.Fill.BackgroundColor = navyHeader;
        worksheet.Cell(4, 1).Style.Font.FontColor = XLColor.White;
        worksheet.Cell(4, 1).Style.Font.Bold = true;

        worksheet.Cell(4, 2).Style.Fill.BackgroundColor = winGreen;
        worksheet.Cell(4, 2).Style.Font.FontColor = XLColor.White;
        worksheet.Cell(4, 2).Style.Font.Bold = true;

        worksheet.Cell(4, 3).Style.Fill.BackgroundColor = lossRed;
        worksheet.Cell(4, 3).Style.Font.FontColor = XLColor.White;
        worksheet.Cell(4, 3).Style.Font.Bold = true;

        worksheet.Cell(4, 4).Style.Fill.BackgroundColor = navyHeader;
        worksheet.Cell(4, 4).Style.Font.FontColor = XLColor.White;
        worksheet.Cell(4, 4).Style.Font.Bold = true;

        var compRows = new (string Metric, string WinVal, string LossVal, string Delta)[]
        {
            ("Total Net PnL", $"₹{summary.WinnersPnL:N2}", $"₹{summary.LosersPnL:N2}", $"Net System PnL: ₹{summary.TotalPnL:N2} | Profit Factor: {summary.ProfitFactor:F2}"),
            ("Win Rate (%)", $"{summary.WinRatePct:F1}%", $"{100m - summary.WinRatePct:F1}%", $"{summary.WinnersCount} Wins vs {summary.LosersCount} Losses ({summary.TotalTrades} total closed)"),
            ("Average Return (%)", $"{summary.AvgReturnPctWinners:F2}%", $"{summary.AvgReturnPctLosers:F2}%", $"Winners outgain losers by {Math.Abs(summary.AvgReturnPctWinners) - Math.Abs(summary.AvgReturnPctLosers):F2}% per trade"),
            ("Average Realized R-Multiple", $"{summary.AvgRealizedRWinners:F2}R", $"{summary.AvgRealizedRLosers:F2}R", $"Risk/Reward realized: {Math.Abs(summary.AvgRealizedRWinners / (summary.AvgRealizedRLosers == 0 ? 1 : summary.AvgRealizedRLosers)):F2}x"),
            ("Average Peak Potential (MFE in R)", $"{summary.AvgPeakRWinners:F2}R", $"{summary.AvgPeakRLosers:F2}R", "How far trades ran in profit: Losers rarely had upside traction"),
            ("Average Peak Gain (MFE in %)", $"{summary.AvgPeakPctWinners:F2}%", $"{summary.AvgPeakPctLosers:F2}%", $"Winners peaked at +{summary.AvgPeakPctWinners:F1}%; Losers peaked at only +{summary.AvgPeakPctLosers:F1}%"),
            ("Average In-Trade Heat (MAE in R)", $"{summary.AvgHeatRWinners:F2}R", $"{summary.AvgHeatRLosers:F2}R", $"Losers suffered {Math.Abs(summary.AvgHeatRLosers) / Math.Max(0.01m, Math.Abs(summary.AvgHeatRWinners)):F1}x more adverse heat than winners"),
            ("Average Intra-Trade Drawdown (MAE %)", $"{summary.AvgHeatPctWinners:F2}%", $"{summary.AvgHeatPctLosers:F2}%", "Winners stayed tight; losers immediately broke down"),
            ("Average Profit Capture Efficiency (%)", $"{summary.AvgCaptureEfficiencyPct:F1}%", "0.0%", "Winners captured over half of peak excursion before exit"),
            ("Round-Trip Failures (Up >= 1.4R to Loss)", "0 trades", $"{summary.RoundTripFailuresCount} trades", $"CRITICAL LEAK: ₹{Math.Abs(summary.RoundTripLostPnL):N2} lost from trades previously in profit"),
            ("Average Breakout Volume Ratio (Entry)", $"{summary.AvgVolumeRatioWinners:F2}x", $"{summary.AvgVolumeRatioLosers:F2}x", $"Winners had {summary.AvgVolumeRatioWinners / Math.Max(0.01m, summary.AvgVolumeRatioLosers):F1}x stronger institutional volume surge"),
            ("% Trades with Volume Surge (>= 1.4x)", $"{summary.PctVolumeSurgeWinners:F1}%", $"{summary.PctVolumeSurgeLosers:F1}%", "High breakout volume strongly correlates with winning trades"),
            ("% Trades Above 200 EMA (at Entry)", $"{summary.PctAbove200EmaWinners:F1}%", $"{summary.PctAbove200EmaLosers:F1}%", "Long-term trend posture at time of entry"),
            ("Average Distance from 200 EMA (%)", $"{summary.AvgDistanceTo200EmaWinners:F1}%", $"{summary.AvgDistanceTo200EmaLosers:F1}%", "Checks if entry was chasing an overextended rally"),
            ("% Trades with Market Tailwind (Nifty > 20 EMA)", $"{summary.PctMarketTailwindWinners:F1}%", $"{summary.PctMarketTailwindLosers:F1}%", "Trading with the wind at your back vs fighting market correction"),
            ("Average Holding Period (Days)", $"{summary.AvgHoldingDaysWinners:F1} days", $"{summary.AvgHoldingDaysLosers:F1} days", "Holding discipline: winners given room, losers cut or held"),
            ("Average Post-Exit 20-Day Run (R)", $"{summary.AvgPostExitMaxRWinners:F2}R", $"{summary.AvgPostExitMaxRLosers:F2}R", "Measures opportunity cost after exit"),
            ("Premature Exits (Surged >= 1.8R after Sell)", $"{summary.LeftMoneyOnTableCount} trades", "-", "Left significant upside on the table (choked winners)"),
            ("Disciplined Exits (Saved from Drawdown)", $"{summary.ExitSavedFromDrawdownCount} trades", "-", "Disciplined stops that protected capital from deeper slides")
        };

        var curRow = 5;
        foreach (var item in compRows)
        {
            worksheet.Cell(curRow, 1).Value = item.Metric;
            worksheet.Cell(curRow, 2).Value = item.WinVal;
            worksheet.Cell(curRow, 3).Value = item.LossVal;
            worksheet.Cell(curRow, 4).Value = item.Delta;

            worksheet.Cell(curRow, 1).Style.Font.Bold = true;

            if (curRow % 2 == 1)
            {
                worksheet.Range(curRow, 1, curRow, 4).Style.Fill.BackgroundColor = XLColor.FromArgb(248, 249, 250);
            }

            curRow++;
        }

        // 3. Top Failure Modes Breakdown Table
        curRow += 2;
        worksheet.Cell(curRow, 1).Value = "Top Failure Modes Breakdown (Why Losers Failed)";
        worksheet.Cell(curRow, 1).Style.Font.Bold = true;
        worksheet.Cell(curRow, 1).Style.Font.FontSize = 12;
        worksheet.Cell(curRow, 1).Style.Font.FontColor = navyHeader;

        curRow++;
        worksheet.Cell(curRow, 1).Value = "Failure Mode";
        worksheet.Cell(curRow, 2).Value = "Trades Affected";
        worksheet.Cell(curRow, 3).Value = "Total Lost PnL";
        worksheet.Cell(curRow, 4).Value = "Mechanism & Prescription";
        worksheet.Range(curRow, 1, curRow, 4).Style.Font.Bold = true;
        worksheet.Range(curRow, 1, curRow, 4).Style.Fill.BackgroundColor = navyHeader;
        worksheet.Range(curRow, 1, curRow, 4).Style.Font.FontColor = XLColor.White;

        curRow++;
        foreach (var fm in summary.FailureModes)
        {
            worksheet.Cell(curRow, 1).Value = fm.Mode;
            worksheet.Cell(curRow, 2).Value = fm.Count;
            worksheet.Cell(curRow, 3).Value = fm.TotalLostPnL;
            worksheet.Cell(curRow, 3).Style.NumberFormat.Format = "₹#,##0.00";
            worksheet.Cell(curRow, 4).Value = fm.Description;

            if (fm.Mode.Contains("Round-Trip", StringComparison.OrdinalIgnoreCase))
            {
                worksheet.Range(curRow, 1, curRow, 4).Style.Fill.BackgroundColor = softYellow;
                worksheet.Cell(curRow, 1).Style.Font.Bold = true;
            }

            curRow++;
        }

        // 4. Individual Trade Autopsy Log Table
        curRow += 2;
        worksheet.Cell(curRow, 1).Value = "Individual Trade Autopsy Log";
        worksheet.Cell(curRow, 1).Style.Font.Bold = true;
        worksheet.Cell(curRow, 1).Style.Font.FontSize = 12;
        worksheet.Cell(curRow, 1).Style.Font.FontColor = navyHeader;

        curRow++;
        var logHeaders = new[]
        {
            "TradeId", "Symbol", "Type", "Entry Price", "Exit Price", "Qty", "Net PnL",
            "Return %", "Realized R", "Peak Price (MFE)", "Peak R", "Max Heat (MAE R)",
            "Capture Eff %", "Entry vs 200 EMA", "Breakout Vol Ratio", "Market Regime (Nifty)",
            "Post-Exit 20d Max R", "Diagnosis Category", "Autopsy Notes & Takeaway"
        };

        for (var i = 0; i < logHeaders.Length; i++)
        {
            worksheet.Cell(curRow, i + 1).Value = logHeaders[i];
        }
        worksheet.Range(curRow, 1, curRow, logHeaders.Length).Style.Font.Bold = true;
        worksheet.Range(curRow, 1, curRow, logHeaders.Length).Style.Fill.BackgroundColor = navyHeader;
        worksheet.Range(curRow, 1, curRow, logHeaders.Length).Style.Font.FontColor = XLColor.White;

        curRow++;
        foreach (var r in results.OrderByDescending(r => r.BuyTime))
        {
            worksheet.Cell(curRow, 1).Value = r.TradeId;
            worksheet.Cell(curRow, 2).Value = r.Symbol;
            worksheet.Cell(curRow, 3).Value = r.TradeType;
            worksheet.Cell(curRow, 4).Value = r.EntryPrice;
            worksheet.Cell(curRow, 5).Value = r.ExitPrice;
            worksheet.Cell(curRow, 6).Value = r.Quantity;
            worksheet.Cell(curRow, 7).Value = r.NetPnL;
            worksheet.Cell(curRow, 8).Value = r.ReturnPct / 100m;

            if (r.RealizedR.HasValue)
            {
                worksheet.Cell(curRow, 9).Value = r.RealizedR.Value;
                worksheet.Cell(curRow, 9).Style.NumberFormat.Format = "0.00\"R\"";
            }
            else worksheet.Cell(curRow, 9).Value = "-";

            worksheet.Cell(curRow, 10).Value = r.PeakPriceDuringTrade;

            if (r.MaxFavorableExcursionR.HasValue)
            {
                worksheet.Cell(curRow, 11).Value = r.MaxFavorableExcursionR.Value;
                worksheet.Cell(curRow, 11).Style.NumberFormat.Format = "0.00\"R\"";
            }
            else worksheet.Cell(curRow, 11).Value = "-";

            if (r.MaxAdverseExcursionR.HasValue)
            {
                worksheet.Cell(curRow, 12).Value = r.MaxAdverseExcursionR.Value;
                worksheet.Cell(curRow, 12).Style.NumberFormat.Format = "0.00\"R\"";
            }
            else worksheet.Cell(curRow, 12).Value = "-";

            if (r.CaptureEfficiencyPct.HasValue)
            {
                worksheet.Cell(curRow, 13).Value = r.CaptureEfficiencyPct.Value / 100m;
                worksheet.Cell(curRow, 13).Style.NumberFormat.Format = "0.0%";
            }
            else worksheet.Cell(curRow, 13).Value = "-";

            if (r.PriceVs200EmaPct.HasValue)
            {
                worksheet.Cell(curRow, 14).Value = r.PriceVs200EmaPct.Value / 100m;
                worksheet.Cell(curRow, 14).Style.NumberFormat.Format = "0.0%";
            }
            else worksheet.Cell(curRow, 14).Value = "-";

            worksheet.Cell(curRow, 15).Value = r.BreakoutVolumeRatio.HasValue ? $"{r.BreakoutVolumeRatio.Value:F2}x" : "-";
            worksheet.Cell(curRow, 16).Value = r.MarketRegime;
            worksheet.Cell(curRow, 17).Value = r.PostExitMaxR.HasValue ? $"{r.PostExitMaxR.Value:F2}R" : "-";
            worksheet.Cell(curRow, 18).Value = r.DiagnosisCategory;
            worksheet.Cell(curRow, 19).Value = r.AutopsyNotes;

            worksheet.Cell(curRow, 4).Style.NumberFormat.Format = "#,##0.00";
            worksheet.Cell(curRow, 5).Style.NumberFormat.Format = "#,##0.00";
            worksheet.Cell(curRow, 7).Style.NumberFormat.Format = "₹#,##0.00";
            worksheet.Cell(curRow, 8).Style.NumberFormat.Format = "0.0%";
            if (r.RealizedR.HasValue) worksheet.Cell(curRow, 9).Style.NumberFormat.Format = "0.00\"R\"";
            worksheet.Cell(curRow, 10).Style.NumberFormat.Format = "#,##0.00";
            if (r.MaxFavorableExcursionR.HasValue) worksheet.Cell(curRow, 11).Style.NumberFormat.Format = "0.00\"R\"";
            if (r.MaxAdverseExcursionR.HasValue) worksheet.Cell(curRow, 12).Style.NumberFormat.Format = "0.00\"R\"";
            if (r.CaptureEfficiencyPct.HasValue) worksheet.Cell(curRow, 13).Style.NumberFormat.Format = "0.0%";
            if (r.PriceVs200EmaPct.HasValue) worksheet.Cell(curRow, 14).Style.NumberFormat.Format = "0.0%";

            if (r.NetPnL > 0)
            {
                worksheet.Cell(curRow, 7).Style.Fill.BackgroundColor = softGreen;
                worksheet.Cell(curRow, 8).Style.Fill.BackgroundColor = softGreen;
                worksheet.Cell(curRow, 9).Style.Fill.BackgroundColor = softGreen;
            }
            else
            {
                worksheet.Cell(curRow, 7).Style.Fill.BackgroundColor = softRed;
                worksheet.Cell(curRow, 8).Style.Fill.BackgroundColor = softRed;
                worksheet.Cell(curRow, 9).Style.Fill.BackgroundColor = softRed;
            }

            if (r.IsRoundTripFailure)
            {
                worksheet.Cell(curRow, 11).Style.Fill.BackgroundColor = softYellow;
                worksheet.Cell(curRow, 18).Style.Fill.BackgroundColor = softYellow;
                worksheet.Cell(curRow, 18).Style.Font.Bold = true;
            }

            curRow++;
        }

        // Generous column widths so NO ##### clipping occurs
        worksheet.Column(1).Width = 38;
        worksheet.Column(2).Width = 24;
        worksheet.Column(3).Width = 14;
        worksheet.Column(4).Width = 16;
        worksheet.Column(5).Width = 16;
        worksheet.Column(6).Width = 12;
        worksheet.Column(7).Width = 18;
        worksheet.Column(8).Width = 14;
        worksheet.Column(9).Width = 14;
        worksheet.Column(10).Width = 16;
        worksheet.Column(11).Width = 14;
        worksheet.Column(12).Width = 16;
        worksheet.Column(13).Width = 16;
        worksheet.Column(14).Width = 18;
        worksheet.Column(15).Width = 18;
        worksheet.Column(16).Width = 24;
        worksheet.Column(17).Width = 20;
        worksheet.Column(18).Width = 28;
        worksheet.Column(19).Width = 72;

        SafeSave(workbook);
        Console.WriteLine($"TradeReview sheet exported successfully with {results.Count} trades analyzed.");
    }

    private static void BuildCategoryStatsSheet(
        XLWorkbook workbook,
        string sheetName,
        string categoryTitle,
        string? tradeTypeFilter)
    {
        var worksheet = workbook.Worksheets.FirstOrDefault(w => w.Name == sheetName)
                        ?? workbook.Worksheets.Add(sheetName);

        worksheet.Clear();

        // Title and Subtitle
        worksheet.Cell(1, 1).Value = $"Trade Journal — Performance Stats ({categoryTitle})";
        worksheet.Cell(1, 1).Style.Font.Bold = true;
        worksheet.Cell(1, 1).Style.Font.FontSize = 14;
        worksheet.Cell(1, 1).Style.Font.FontColor = XLColor.FromArgb(27, 42, 74);

        worksheet.Cell(2, 1).Value = "Auto-updates from MatchedTrades — just rerun sync, no manual edits needed";
        worksheet.Cell(2, 1).Style.Font.Italic = true;
        worksheet.Cell(2, 1).Style.Font.FontSize = 10;
        worksheet.Cell(2, 1).Style.Font.FontColor = XLColor.FromArgb(90, 90, 90);

        // Header Row (Row 4)
        worksheet.Cell(4, 1).Value = "Metric";
        worksheet.Cell(4, 2).Value = "Value";

        var headerRange = worksheet.Range("A4:B4");
        headerRange.Style.Font.Bold = true;
        headerRange.Style.Fill.BackgroundColor = XLColor.FromArgb(27, 42, 74);
        headerRange.Style.Font.FontColor = XLColor.White;

        var softGreen = XLColor.FromArgb(198, 239, 206);
        var softRed = XLColor.FromArgb(255, 199, 206);

        string fCountClosed, fCountWin, fCountLoss, fTotalPnl, fMaxProfit, fMaxLoss, fProfitFactor,
               fAvgLoss, fAvgGain, fMean, fMedian, fStdev, fSkew, fHoldWin, fHoldLoss;

        if (tradeTypeFilter == null)
        {
            fCountClosed = "=COUNT(MatchedTrades!H2:H100000)";
            fCountWin = "=COUNTIF(MatchedTrades!H2:H100000,\">0\")";
            fCountLoss = "=COUNTIF(MatchedTrades!H2:H100000,\"<0\")";
            fTotalPnl = "=SUM(MatchedTrades!H2:H100000)";
            fMaxProfit = "=IFERROR(MAX(MatchedTrades!H2:H100000),0)";
            fMaxLoss = "=IFERROR(MIN(MatchedTrades!H2:H100000),0)";
            fProfitFactor = "=IFERROR(SUMIF(MatchedTrades!H2:H100000,\">0\")/ABS(SUMIF(MatchedTrades!H2:H100000,\"<0\")),\"\")";
            fAvgLoss = "=IFERROR(AVERAGEIF(MatchedTrades!H2:H100000,\"<0\"),0)";
            fAvgGain = "=IFERROR(AVERAGEIF(MatchedTrades!H2:H100000,\">0\"),0)";
            fMean = "=IFERROR(AVERAGE(MatchedTrades!H2:H100000),0)";
            fMedian = "=IFERROR(MEDIAN(MatchedTrades!H2:H100000),0)";
            fStdev = "=IFERROR(STDEV(MatchedTrades!H2:H100000),0)";
            fSkew = "=IFERROR(SKEW(MatchedTrades!H2:H100000),0)";
            fHoldWin = "=IFERROR(AVERAGEIFS(MatchedTrades!K2:K100000,MatchedTrades!H2:H100000,\">0\"),0)";
            fHoldLoss = "=IFERROR(AVERAGEIFS(MatchedTrades!K2:K100000,MatchedTrades!H2:H100000,\"<0\"),0)";
        }
        else
        {
            fCountClosed = $"=COUNTIFS(MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\"<>\")";
            fCountWin = $"=COUNTIFS(MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\">0\")";
            fCountLoss = $"=COUNTIFS(MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\"<0\")";
            fTotalPnl = $"=SUMIFS(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\")";
            fMaxProfit = $"=IFERROR(MAXIFS(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\"),0)";
            fMaxLoss = $"=IFERROR(MINIFS(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\"),0)";
            fProfitFactor = $"=IFERROR(SUMIFS(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\">0\")/ABS(SUMIFS(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\"<0\")),\"\")";
            fAvgLoss = $"=IFERROR(AVERAGEIFS(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\"<0\"),0)";
            fAvgGain = $"=IFERROR(AVERAGEIFS(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\">0\"),0)";
            fMean = $"=IFERROR(AVERAGEIFS(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\"),0)";
            fMedian = $"=IFERROR(MEDIAN(FILTER(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000=\"{tradeTypeFilter}\")),0)";
            fStdev = $"=IFERROR(STDEV(FILTER(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000=\"{tradeTypeFilter}\")),0)";
            fSkew = $"=IFERROR(SKEW(FILTER(MatchedTrades!H2:H100000,MatchedTrades!L2:L100000=\"{tradeTypeFilter}\")),0)";
            fHoldWin = $"=IFERROR(AVERAGEIFS(MatchedTrades!K2:K100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\">0\"),0)";
            fHoldLoss = $"=IFERROR(AVERAGEIFS(MatchedTrades!K2:K100000,MatchedTrades!L2:L100000,\"{tradeTypeFilter}\",MatchedTrades!H2:H100000,\"<0\"),0)";
        }

        SetSingleStatRow(worksheet, 5, "Total Closed Trades", fCountClosed, "#,##0");
        SetSingleStatRow(worksheet, 6, "Profitable Trades", fCountWin, "#,##0", softGreen);
        SetSingleStatRow(worksheet, 7, "Losing Trades", fCountLoss, "#,##0", softRed);
        SetSingleStatRow(worksheet, 8, "System Accuracy (Win Rate)", "=IF(B5>0,B6/B5,0)", "0.0%");
        SetSingleStatRow(worksheet, 9, "Total Profit/Loss", fTotalPnl, "#,##0.00");
        SetSingleStatRow(worksheet, 10, "Max Profit", fMaxProfit, "#,##0.00", softGreen);
        SetSingleStatRow(worksheet, 11, "Max Loss", fMaxLoss, "#,##0.00", softRed);
        SetSingleStatRow(worksheet, 12, "Profit Factor", fProfitFactor, "0.00");
        SetSingleStatRow(worksheet, 13, "Average Loss", fAvgLoss, "#,##0.00");
        SetSingleStatRow(worksheet, 14, "Average Gain", fAvgGain, "#,##0.00");
        SetSingleStatRow(worksheet, 15, "RR (Avg Gain / Avg Loss)", "=IF(B13=0,\"\",ABS(B14/B13))", "0.00", softGreen);
        SetSingleStatRow(worksheet, 16, "Mean (Net P&L)", fMean, "#,##0.00");
        SetSingleStatRow(worksheet, 17, "Median (Net P&L)", fMedian, "#,##0.00");
        SetSingleStatRow(worksheet, 18, "Standard Deviation", fStdev, "#,##0.00");
        SetSingleStatRow(worksheet, 19, "Coefficient of Variation", "=IF(B16=0,\"\",ABS(B18/B16))", "0.00");
        SetSingleStatRow(worksheet, 20, "Skewness", fSkew, "0.000", softGreen);
        SetSingleStatRow(worksheet, 21, "Expectancy (Mean/AvgLoss, R)", "=IF(B13=0,\"\",ABS(B16/B13))", "0.00", softGreen);
        SetSingleStatRow(worksheet, 22, "Avg Holding Days (Winners)", fHoldWin, "0.0", softGreen);
        SetSingleStatRow(worksheet, 23, "Avg Holding Days (Losers)", fHoldLoss, "0.0", softRed);

        // Footnote in Row 25
        worksheet.Cell(25, 1).Value =
            "Win-rate cell is green when >=33.3% (breakeven at standard 1:2 R:R). Profit Factor / RR green when >=1.0. Auto-updates as you tag trades in MatchedTrades.";
        worksheet.Cell(25, 1).Style.Font.Italic = true;
        worksheet.Cell(25, 1).Style.Font.FontSize = 9;
        worksheet.Cell(25, 1).Style.Font.FontColor = XLColor.FromArgb(120, 120, 120);

        // Gridlines & borders
        var tableRange = worksheet.Range("A4:B23");
        tableRange.Style.Border.InsideBorder = XLBorderStyleValues.Thin;
        tableRange.Style.Border.InsideBorderColor = XLColor.FromArgb(220, 220, 220);
        tableRange.Style.Border.OutsideBorder = XLBorderStyleValues.Thin;
        tableRange.Style.Border.OutsideBorderColor = XLColor.FromArgb(180, 180, 180);

        worksheet.Range("A5:A23").Style.Font.Bold = true;
        worksheet.Range("B5:B23").Style.Alignment.Horizontal = XLAlignmentHorizontalValues.Right;

        // Conditional formatting for Win Rate (B8)
        var winRateRange = worksheet.Range("B8");
        winRateRange.AddConditionalFormat()
            .WhenIsTrue("B8>=0.333")
            .Fill.SetBackgroundColor(softGreen);
        winRateRange.AddConditionalFormat()
            .WhenIsTrue("AND(B8<0.333,B8>0)")
            .Fill.SetBackgroundColor(softRed);

        // Conditional formatting for Total Profit/Loss (B9)
        var totalPnlRange = worksheet.Range("B9");
        totalPnlRange.AddConditionalFormat()
            .WhenIsTrue("B9>0")
            .Fill.SetBackgroundColor(softGreen);
        totalPnlRange.AddConditionalFormat()
            .WhenIsTrue("B9<0")
            .Fill.SetBackgroundColor(softRed);

        // Conditional formatting for Profit Factor (B12)
        var pfRange = worksheet.Range("B12");
        pfRange.AddConditionalFormat()
            .WhenIsTrue("B12>=1.0")
            .Fill.SetBackgroundColor(softGreen);
        pfRange.AddConditionalFormat()
            .WhenIsTrue("AND(B12<1.0,B12>0)")
            .Fill.SetBackgroundColor(softRed);

        // Conditional formatting for Mean and Median Net P&L (B16, B17)
        var meanRange = worksheet.Range("B16");
        meanRange.AddConditionalFormat()
            .WhenIsTrue("B16>0")
            .Fill.SetBackgroundColor(softGreen);
        meanRange.AddConditionalFormat()
            .WhenIsTrue("B16<0")
            .Fill.SetBackgroundColor(softRed);

        var medianRange = worksheet.Range("B17");
        medianRange.AddConditionalFormat()
            .WhenIsTrue("B17>0")
            .Fill.SetBackgroundColor(softGreen);
        medianRange.AddConditionalFormat()
            .WhenIsTrue("B17<0")
            .Fill.SetBackgroundColor(softRed);

        // Explicit generous column widths to ensure numbers NEVER display as #####
        worksheet.Column(1).Width = 34;
        worksheet.Column(2).Width = 20;
    }

    private static void SetSingleStatRow(
        IXLWorksheet worksheet,
        int row,
        string metric,
        string formula,
        string numberFormat,
        XLColor? bgColor = null)
    {
        worksheet.Cell(row, 1).Value = metric;
        worksheet.Cell(row, 2).FormulaA1 = formula;
        worksheet.Cell(row, 2).Style.NumberFormat.Format = numberFormat;

        if (bgColor != null)
            worksheet.Cell(row, 2).Style.Fill.BackgroundColor = bgColor;
    }

    private void SafeSave(XLWorkbook workbook)
    {
        var tempPath = Path.Combine(Path.GetDirectoryName(_filePath)!, "MasterJournal_temp.xlsx");

        workbook.SaveAs(tempPath);

        ExcelProcessHelper.EnsureFileAccessible(_filePath);

        try
        {
            if (File.Exists(_filePath))
                File.Delete(_filePath);

            File.Move(tempPath, _filePath);
        }
        catch (IOException)
        {
            Console.WriteLine("[NOTICE] MasterJournal.xlsx locked during save. Terminating Excel to finalize save...");
            ExcelProcessHelper.KillExcelProcesses();
            Thread.Sleep(800);

            try
            {
                if (File.Exists(_filePath))
                    File.Delete(_filePath);

                File.Move(tempPath, _filePath);
            }
            catch (Exception ex)
            {
                if (File.Exists(tempPath))
                    File.Delete(tempPath);

                throw new IOException($"Could not save to '{_filePath}'.", ex);
            }
        }
    }

    private XLWorkbook OpenOrCreateWorkbook()
    {
        ExcelProcessHelper.EnsureFileAccessible(_filePath);
        return File.Exists(_filePath) ? new XLWorkbook(_filePath) : new XLWorkbook();
    }

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

    /// <summary>
    /// Maps TradeId (col A) -> row number for existing rows in the MatchedTrades sheet, so
    /// ExportMatchedTrades can update a trade's row in place when a new leg (e.g. a trailing
    /// exit) arrives for a lot that already has a partial exit recorded.
    /// </summary>
    private static Dictionary<string, int> ReadExistingMatchedTradeRows(IXLWorksheet worksheet)
    {
        var map = new Dictionary<string, int>();
        var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;

        for (var row = 2; row <= lastRow; row++)
        {
            var id = worksheet.Cell(row, 1).GetString();
            if (!string.IsNullOrWhiteSpace(id))
                map[id] = row;
        }

        return map;
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
            "NetPnL", "BuyTime", "SellTime", "HoldingDays", "Trade Type", "StopLossPrice", "RiskAmount",
            "R-Multiple", "Grade (W/L)", "MaxPriceAfterExit", "ObservedTrailR", "Notes"
        };

        WriteHeaders(worksheet, headers);
    }

    private static void EnsureMatchedTradeColumns(IXLWorksheet worksheet)
    {
        var header12 = worksheet.Cell(1, 12).GetString().Trim();
        if (string.Equals(header12, "StopLossPrice", StringComparison.OrdinalIgnoreCase))
        {
            // Existing sheet using legacy column layout: insert "Trade Type" at column 12
            worksheet.Column(12).InsertColumnsBefore(1);
            worksheet.Cell(1, 12).Value = "Trade Type";
            StyleHeaderRow(worksheet);

            // Re-apply formulas for RiskAmount (col 14) and R-Multiple (col 15)
            var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;
            for (var row = 2; row <= lastRow; row++)
            {
                worksheet.Cell(row, 14).FormulaA1 = $"=IF(M{row}<>\"\", C{row}-M{row}, ROUND(1000/E{row}, 2))";
                worksheet.Cell(row, 15).FormulaA1 = $"=IF(M{row}<>\"\", H{row}/((C{row}-M{row})*E{row}), ROUND(H{row}/1000, 2))";
            }
        }
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
        var rMultipleRange = worksheet.Range("O2:O1000");
        rMultipleRange.AddConditionalFormat()
            .WhenIsTrue("O2>0")
            .Fill.SetBackgroundColor(XLColor.FromArgb(198, 239, 206));
        rMultipleRange.AddConditionalFormat()
            .WhenIsTrue("O2<0")
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
