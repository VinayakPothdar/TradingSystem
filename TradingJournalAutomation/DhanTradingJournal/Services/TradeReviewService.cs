using System.Globalization;
using ClosedXML.Excel;
using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public class TradeReviewService
{
    private readonly string _journalPath;
    private readonly string _historicalFolder;
    private readonly Dictionary<string, List<HistoricalCandle>> _candleCache = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<string, string> _aliases = WatchlistProvider.GetSymbolAliases();

    public TradeReviewService(string? journalPath = null, string? historicalFolder = null)
    {
        _journalPath = journalPath ?? @"D:\TradingJournal\MasterJournal.xlsx";
        _historicalFolder = ResolveHistoricalFolder(historicalFolder);
    }

    public (List<TradeReviewResult> Results, WinnersLosersComparison Summary) RunReview(string? tradeTypeFilter = "Swing")
    {
        Console.WriteLine("\nStarting Trade Review & Autopsy Analysis...");
        Console.WriteLine($"Journal path:      {_journalPath}");
        Console.WriteLine($"Historical folder: {_historicalFolder}");
        Console.WriteLine($"Trade Type Filter: {(string.IsNullOrWhiteSpace(tradeTypeFilter) ? "All Trades" : tradeTypeFilter)}");

        var allTrades = ReadMatchedTrades();
        var trades = string.IsNullOrWhiteSpace(tradeTypeFilter)
            ? allTrades
            : allTrades.Where(t => string.Equals(t.TradeGrade?.Trim(), tradeTypeFilter.Trim(), StringComparison.OrdinalIgnoreCase)).ToList();

        if (trades.Count == 0)
        {
            Console.WriteLine($"No matched trades found for filter '{(tradeTypeFilter ?? "All")}' in journal to review.");
            return (new List<TradeReviewResult>(), new WinnersLosersComparison());
        }

        Console.WriteLine($"Found {trades.Count} closed {(tradeTypeFilter ?? "All")} trades to review.");

        // Load Nifty 50 benchmark candles
        var niftyCandles = LoadCandles("^NSEI");
        var niftyEma20 = CalculateEma(niftyCandles, 20);
        var niftyEma50 = CalculateEma(niftyCandles, 50);

        var watchlist = WatchlistProvider.GetDefaultWatchlist();
        var watchlistLookup = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var inst in watchlist)
        {
            if (!string.IsNullOrWhiteSpace(inst.Name))
                watchlistLookup[inst.Name] = inst.Symbol;
            if (!string.IsNullOrWhiteSpace(inst.Symbol))
                watchlistLookup[inst.Symbol] = inst.Symbol;
        }

        var results = new List<TradeReviewResult>();

        foreach (var trade in trades)
        {
            var ticker = ResolveTicker(trade.Symbol, watchlistLookup);
            var stockCandles = LoadCandles(ticker);

            var review = AnalyzeTrade(trade, ticker, stockCandles, niftyCandles, niftyEma20, niftyEma50);
            results.Add(review);
        }

        var summary = BuildComparisonSummary(results);

        Console.WriteLine($"Autopsy complete: {summary.WinnersCount} Wins | {summary.LosersCount} Losses | Win Rate: {summary.WinRatePct:F1}%");
        Console.WriteLine($"Round-Trip Failures Identified: {summary.RoundTripFailuresCount} trades");

        return (results, summary);
    }

    private TradeReviewResult AnalyzeTrade(
        MatchedTrade trade,
        string ticker,
        List<HistoricalCandle> stockCandles,
        List<HistoricalCandle> niftyCandles,
        Dictionary<DateTime, decimal> niftyEma20,
        Dictionary<DateTime, decimal> niftyEma50)
    {
        var entryPrice = trade.EntryPrice;
        var exitPrice = trade.ExitPrice;
        var netPnL = trade.NetPnL;
        var buyDate = trade.BuyTime.Date;
        var sellDate = trade.SellTime.Date;

        var returnPct = entryPrice > 0 ? ((exitPrice - entryPrice) / entryPrice) * 100m : 0m;

        // Determine Initial Risk Per Share (1R)
        // Fixed Rs 1,000 risk per trade (1R = 1k)
        decimal initialRisk;
        if (trade.StopLossPrice.HasValue && trade.StopLossPrice.Value > 0 && trade.StopLossPrice.Value < entryPrice)
        {
            initialRisk = entryPrice - trade.StopLossPrice.Value;
        }
        else if (trade.Quantity > 0)
        {
            // Default 1k SL: 1R per share = Rs 1,000 / Quantity
            initialRisk = 1000.0m / trade.Quantity;
        }
        else
        {
            initialRisk = entryPrice * 0.04m; // 4% default swing stop
        }

        if (initialRisk <= 0) initialRisk = entryPrice * 0.04m;

        // Record implied stop price if not explicitly provided
        var stopLossPrice = (trade.StopLossPrice.HasValue && trade.StopLossPrice.Value > 0)
            ? trade.StopLossPrice.Value
            : (entryPrice - initialRisk);

        // Realized R: Net PnL / 1,000 when Quantity > 0 (reflecting true net 1R payoff)
        decimal? realizedR = trade.Quantity > 0 ? trade.NetPnL / 1000.0m : (exitPrice - entryPrice) / initialRisk;

        // In-Trade Candles (from Buy Date to Sell Date)
        var inTradeCandles = stockCandles
            .Where(c => c.Date.Date >= buyDate && c.Date.Date <= sellDate)
            .OrderBy(c => c.Date)
            .ToList();

        decimal peakPrice = entryPrice;
        decimal troughPrice = entryPrice;

        if (inTradeCandles.Count > 0)
        {
            peakPrice = inTradeCandles.Max(c => c.High);
            troughPrice = inTradeCandles.Min(c => c.Low);
        }
        else
        {
            peakPrice = Math.Max(entryPrice, exitPrice);
            troughPrice = Math.Min(entryPrice, exitPrice);
        }

        var mfePct = entryPrice > 0 ? ((peakPrice - entryPrice) / entryPrice) * 100m : 0m;
        var peakR = trade.Quantity > 0
            ? ((peakPrice - entryPrice) * trade.Quantity) / 1000.0m
            : (initialRisk > 0 ? (peakPrice - entryPrice) / initialRisk : (decimal?)null);

        var maePct = entryPrice > 0 ? ((troughPrice - entryPrice) / entryPrice) * 100m : 0m;
        var maxHeatR = trade.Quantity > 0
            ? ((troughPrice - entryPrice) * trade.Quantity) / 1000.0m
            : (initialRisk > 0 ? (troughPrice - entryPrice) / initialRisk : (decimal?)null);

        // Capture Efficiency
        decimal? captureEfficiency = null;
        if (netPnL > 0 && peakPrice > entryPrice)
        {
            var maxPossibleGain = peakPrice - entryPrice;
            var actualGain = exitPrice - entryPrice;
            captureEfficiency = maxPossibleGain > 0 ? (actualGain / maxPossibleGain) * 100m : 0m;
        }

        // Round-Trip Failure: trade reached >= 1.5R in profit, but reversed into a loss without breakeven stop
        var isRoundTrip = netPnL < 0 && peakR.HasValue && peakR.Value >= 1.5m;

        // Technical Posture at Entry
        var stockEma200 = CalculateEma(stockCandles, 200);
        var stockVolSma20 = CalculateVolumeSma(stockCandles, 20);

        var nearestEntryCandle = stockCandles.Where(c => c.Date.Date <= buyDate).OrderByDescending(c => c.Date).FirstOrDefault();

        decimal? priceVs200EmaPct = null;
        bool above200Ema = false;
        bool isOverextended = false;

        if (nearestEntryCandle != null && stockEma200.TryGetValue(nearestEntryCandle.Date, out var ema200Val) && ema200Val > 0)
        {
            priceVs200EmaPct = ((entryPrice - ema200Val) / ema200Val) * 100m;
            above200Ema = entryPrice >= ema200Val;
            isOverextended = priceVs200EmaPct.Value > 25.0m;
        }

        decimal? breakoutVolRatio = null;
        bool volumeSurge = false;

        if (nearestEntryCandle != null && stockVolSma20.TryGetValue(nearestEntryCandle.Date, out var volSmaVal) && volSmaVal > 0)
        {
            breakoutVolRatio = Math.Round((decimal)nearestEntryCandle.Volume / volSmaVal, 2);
            volumeSurge = breakoutVolRatio.Value >= 1.4m;
        }

        // Market Regime at Entry (Nifty 50)
        var nearestNiftyCandle = niftyCandles.Where(c => c.Date.Date <= buyDate).OrderByDescending(c => c.Date).FirstOrDefault();
        decimal? niftyClose = nearestNiftyCandle?.Close;
        string marketRegime = "Unknown";
        bool hasMarketTailwind = false;

        if (nearestNiftyCandle != null)
        {
            niftyEma20.TryGetValue(nearestNiftyCandle.Date, out var nEma20);
            niftyEma50.TryGetValue(nearestNiftyCandle.Date, out var nEma50);

            if (nEma20 > 0 && nEma50 > 0)
            {
                if (nearestNiftyCandle.Close >= nEma20)
                {
                    marketRegime = "Bullish / Trend";
                    hasMarketTailwind = true;
                }
                else if (nearestNiftyCandle.Close >= nEma50)
                {
                    marketRegime = "Pullback in Trend";
                    hasMarketTailwind = false;
                }
                else
                {
                    marketRegime = "Bearish / Correction";
                    hasMarketTailwind = false;
                }
            }
        }

        // Post-Exit Analysis (20 Trading Days following Sell Date)
        var postExitCandles = stockCandles
            .Where(c => c.Date.Date > sellDate)
            .OrderBy(c => c.Date)
            .Take(20)
            .ToList();

        decimal? maxPostExitPrice = null;
        decimal? postExitMaxReturnPct = null;
        decimal? postExitMaxR = null;
        bool leftMoneyOnTable = false;
        bool exitSavedDrawdown = false;

        if (postExitCandles.Count > 0)
        {
            maxPostExitPrice = postExitCandles.Max(c => c.High);
            var minPostExitPrice = postExitCandles.Min(c => c.Low);

            if (exitPrice > 0)
                postExitMaxReturnPct = ((maxPostExitPrice.Value - exitPrice) / exitPrice) * 100m;

            if (trade.Quantity > 0)
                postExitMaxR = ((maxPostExitPrice.Value - exitPrice) * trade.Quantity) / 1000.0m;
            else if (initialRisk > 0)
                postExitMaxR = (maxPostExitPrice.Value - exitPrice) / initialRisk;

            leftMoneyOnTable = (postExitMaxR.HasValue && postExitMaxR.Value >= 1.8m) || (postExitMaxReturnPct.HasValue && postExitMaxReturnPct.Value >= 5.0m);
            exitSavedDrawdown = minPostExitPrice < exitPrice * 0.96m;
        }

        // Diagnostic Classifier
        var (category, autopsyNote) = ClassifyTrade(
            netPnL,
            realizedR,
            returnPct,
            peakR,
            mfePct,
            maxHeatR,
            isRoundTrip,
            above200Ema,
            isOverextended,
            priceVs200EmaPct,
            breakoutVolRatio,
            hasMarketTailwind,
            marketRegime,
            leftMoneyOnTable,
            postExitMaxR,
            captureEfficiency);

        return new TradeReviewResult
        {
            TradeId = trade.TradeId,
            Symbol = trade.Symbol,
            YahooTicker = ticker,
            TradeType = string.IsNullOrWhiteSpace(trade.TradeGrade) ? "Swing" : trade.TradeGrade,
            BuyTime = trade.BuyTime,
            SellTime = trade.SellTime,
            HoldingDays = trade.HoldingDays,
            EntryPrice = entryPrice,
            ExitPrice = exitPrice,
            Quantity = trade.Quantity,
            NetPnL = netPnL,
            ReturnPct = Math.Round(returnPct, 2),
            StopLossPrice = stopLossPrice,
            InitialRiskPerShare = Math.Round(initialRisk, 2),
            RealizedR = realizedR.HasValue ? Math.Round(realizedR.Value, 2) : null,

            PeakPriceDuringTrade = peakPrice,
            MaxFavorableExcursionPct = Math.Round(mfePct, 2),
            MaxFavorableExcursionR = peakR.HasValue ? Math.Round(peakR.Value, 2) : null,

            TroughPriceDuringTrade = troughPrice,
            MaxAdverseExcursionPct = Math.Round(maePct, 2),
            MaxAdverseExcursionR = maxHeatR.HasValue ? Math.Round(maxHeatR.Value, 2) : null,

            CaptureEfficiencyPct = captureEfficiency.HasValue ? Math.Round(captureEfficiency.Value, 1) : null,
            IsRoundTripFailure = isRoundTrip,

            PriceVs200EmaPct = priceVs200EmaPct.HasValue ? Math.Round(priceVs200EmaPct.Value, 2) : null,
            Above200Ema = above200Ema,
            IsOverextended = isOverextended,
            BreakoutVolumeRatio = breakoutVolRatio,
            VolumeSurge = volumeSurge,

            Nifty50Close = niftyClose,
            MarketRegime = marketRegime,
            HasMarketTailwind = hasMarketTailwind,

            MaxPostExitPrice = maxPostExitPrice,
            PostExitMaxReturnPct = postExitMaxReturnPct.HasValue ? Math.Round(postExitMaxReturnPct.Value, 2) : null,
            PostExitMaxR = postExitMaxR.HasValue ? Math.Round(postExitMaxR.Value, 2) : null,
            LeftMoneyOnTable = leftMoneyOnTable,
            ExitSavedFromDrawdown = exitSavedDrawdown,

            DiagnosisCategory = category,
            AutopsyNotes = autopsyNote
        };
    }

    private static (string Category, string Notes) ClassifyTrade(
        decimal netPnL,
        decimal? realizedR,
        decimal returnPct,
        decimal? peakR,
        decimal mfePct,
        decimal? maxHeatR,
        bool isRoundTrip,
        bool above200Ema,
        bool isOverextended,
        decimal? priceVs200EmaPct,
        decimal? breakoutVolRatio,
        bool hasMarketTailwind,
        string marketRegime,
        bool leftMoneyOnTable,
        decimal? postExitMaxR,
        decimal? captureEfficiency)
    {
        if (netPnL <= 0)
        {
            // FAILURE MODES
            if (isRoundTrip)
            {
                return (
                    "Round-Trip Failure",
                    $"Peaked at +{peakR ?? 0:F1}R (+{mfePct:F1}%) before reversing into a loss. Profit taking or breakeven stop missed."
                );
            }

            if (!above200Ema)
            {
                return (
                    "Counter-Trend Entry",
                    $"Entered below 200 EMA ({priceVs200EmaPct ?? 0:F1}%). Structural downtrend headwind."
                );
            }

            if (isOverextended)
            {
                return (
                    "Overextended Entry",
                    $"Entered {priceVs200EmaPct ?? 0:F1}% above 200 EMA. High risk of mean-reversion pullback."
                );
            }

            if (breakoutVolRatio.HasValue && breakoutVolRatio.Value < 0.9m)
            {
                return (
                    "Low Volume Breakout",
                    $"Entry volume was only {breakoutVolRatio:F2}x 20d avg. Lack of institutional participation."
                );
            }

            if (!hasMarketTailwind)
            {
                return (
                    "Hostile Market Regime",
                    $"Entered during market {marketRegime} (Nifty < 20 EMA). Broader market drag."
                );
            }

            if (maxHeatR.HasValue && maxHeatR.Value <= -0.8m && (!peakR.HasValue || peakR.Value < 0.4m))
            {
                return (
                    "Immediate Heat Failure",
                    $"Stock plunged immediately with heavy heat ({maxHeatR:F1}R) and zero upside traction."
                );
            }

            return (
                "Normal Controlled Loss",
                $"Loss within normal statistical risk bounds ({realizedR ?? 0:F1}R). Stop-loss executed properly."
            );
        }

        // WINNER CLASSIFICATIONS
        if (leftMoneyOnTable)
        {
            return (
                "Choked Winner",
                $"Exited at +{realizedR ?? 0:F1}R (+{returnPct:F1}%), but stock surged another +{postExitMaxR ?? 0:F1}R over next 20 days."
            );
        }

        if (captureEfficiency.HasValue && captureEfficiency.Value >= 65m)
        {
            return (
                "High Efficiency Win",
                $"Captured {captureEfficiency:F0}% of peak move (+{peakR ?? 0:F1}R) with low heat ({maxHeatR ?? 0:F1}R)."
            );
        }

        if (breakoutVolRatio.HasValue && breakoutVolRatio.Value >= 1.4m && hasMarketTailwind)
        {
            return (
                "Institutional Trend Run",
                $"Volume surge ({breakoutVolRatio:F1}x) backed by Nifty market tailwind."
            );
        }

        return (
            "Clean Win",
            $"Profitable trade capturing +{realizedR ?? 0:F1}R (+{returnPct:F1}%) within planned timeframe."
        );
    }

    private static WinnersLosersComparison BuildComparisonSummary(List<TradeReviewResult> results)
    {
        var winners = results.Where(r => r.NetPnL > 0).ToList();
        var losers = results.Where(r => r.NetPnL <= 0).ToList();

        var total = results.Count;
        var wCount = winners.Count;
        var lCount = losers.Count;

        var wPnL = winners.Sum(r => r.NetPnL);
        var lPnL = losers.Sum(r => r.NetPnL);
        var totalPnL = results.Sum(r => r.NetPnL);

        var profitFactor = Math.Abs(lPnL) > 0 ? wPnL / Math.Abs(lPnL) : 0m;
        var winRate = total > 0 ? (decimal)wCount / total * 100m : 0m;

        // Averages
        var avgReturnWinners = wCount > 0 ? winners.Average(r => r.ReturnPct) : 0m;
        var avgReturnLosers = lCount > 0 ? losers.Average(r => r.ReturnPct) : 0m;

        var avgRWinners = wCount > 0 ? winners.Average(r => r.RealizedR ?? 0m) : 0m;
        var avgRLosers = lCount > 0 ? losers.Average(r => r.RealizedR ?? 0m) : 0m;

        var avgPeakRWinners = wCount > 0 ? winners.Average(r => r.MaxFavorableExcursionR ?? 0m) : 0m;
        var avgPeakRLosers = lCount > 0 ? losers.Average(r => r.MaxFavorableExcursionR ?? 0m) : 0m;

        var avgPeakPctWinners = wCount > 0 ? winners.Average(r => r.MaxFavorableExcursionPct) : 0m;
        var avgPeakPctLosers = lCount > 0 ? losers.Average(r => r.MaxFavorableExcursionPct) : 0m;

        var avgHeatRWinners = wCount > 0 ? winners.Average(r => r.MaxAdverseExcursionR ?? 0m) : 0m;
        var avgHeatRLosers = lCount > 0 ? losers.Average(r => r.MaxAdverseExcursionR ?? 0m) : 0m;

        var avgHeatPctWinners = wCount > 0 ? winners.Average(r => r.MaxAdverseExcursionPct) : 0m;
        var avgHeatPctLosers = lCount > 0 ? losers.Average(r => r.MaxAdverseExcursionPct) : 0m;

        var roundTrips = losers.Where(r => r.IsRoundTripFailure).ToList();
        var roundTripCount = roundTrips.Count;
        var roundTripLoss = roundTrips.Sum(r => r.NetPnL);

        var avgCaptureEff = wCount > 0 ? winners.Where(r => r.CaptureEfficiencyPct.HasValue).DefaultIfEmpty().Average(r => r?.CaptureEfficiencyPct ?? 0m) : 0m;

        var avgVolRatioWinners = wCount > 0 ? winners.Where(r => r.BreakoutVolumeRatio.HasValue).DefaultIfEmpty().Average(r => r?.BreakoutVolumeRatio ?? 0m) : 0m;
        var avgVolRatioLosers = lCount > 0 ? losers.Where(r => r.BreakoutVolumeRatio.HasValue).DefaultIfEmpty().Average(r => r?.BreakoutVolumeRatio ?? 0m) : 0m;

        var pctVolSurgeWinners = wCount > 0 ? (decimal)winners.Count(r => r.VolumeSurge) / wCount * 100m : 0m;
        var pctVolSurgeLosers = lCount > 0 ? (decimal)losers.Count(r => r.VolumeSurge) / lCount * 100m : 0m;

        var pctAbove200Winners = wCount > 0 ? (decimal)winners.Count(r => r.Above200Ema) / wCount * 100m : 0m;
        var pctAbove200Losers = lCount > 0 ? (decimal)losers.Count(r => r.Above200Ema) / lCount * 100m : 0m;

        var avgDist200Winners = wCount > 0 ? winners.Where(r => r.PriceVs200EmaPct.HasValue).DefaultIfEmpty().Average(r => r?.PriceVs200EmaPct ?? 0m) : 0m;
        var avgDist200Losers = lCount > 0 ? losers.Where(r => r.PriceVs200EmaPct.HasValue).DefaultIfEmpty().Average(r => r?.PriceVs200EmaPct ?? 0m) : 0m;

        var pctTailwindWinners = wCount > 0 ? (decimal)winners.Count(r => r.HasMarketTailwind) / wCount * 100m : 0m;
        var pctTailwindLosers = lCount > 0 ? (decimal)losers.Count(r => r.HasMarketTailwind) / lCount * 100m : 0m;

        var avgHoldWinners = wCount > 0 ? winners.Average(r => r.HoldingDays) : 0.0;
        var avgHoldLosers = lCount > 0 ? losers.Average(r => r.HoldingDays) : 0.0;

        var avgPostExitRWinners = wCount > 0 ? winners.Where(r => r.PostExitMaxR.HasValue).DefaultIfEmpty().Average(r => r?.PostExitMaxR ?? 0m) : 0m;
        var avgPostExitRLosers = lCount > 0 ? losers.Where(r => r.PostExitMaxR.HasValue).DefaultIfEmpty().Average(r => r?.PostExitMaxR ?? 0m) : 0m;

        var leftMoneyCount = results.Count(r => r.LeftMoneyOnTable);
        var drawdownSavedCount = results.Count(r => r.ExitSavedFromDrawdown);

        // Failure Modes Breakdown
        var failureModes = losers
            .GroupBy(l => l.DiagnosisCategory)
            .Select(g => new FailureModeCount
            {
                Mode = g.Key,
                Count = g.Count(),
                TotalLostPnL = g.Sum(l => l.NetPnL),
                Description = GetFailureModeDescription(g.Key)
            })
            .OrderByDescending(f => f.Count)
            .ToList();

        return new WinnersLosersComparison
        {
            TotalTrades = total,
            WinnersCount = wCount,
            LosersCount = lCount,
            WinRatePct = Math.Round(winRate, 1),
            TotalPnL = Math.Round(totalPnL, 2),
            WinnersPnL = Math.Round(wPnL, 2),
            LosersPnL = Math.Round(lPnL, 2),
            ProfitFactor = Math.Round(profitFactor, 2),

            AvgReturnPctWinners = Math.Round(avgReturnWinners, 2),
            AvgReturnPctLosers = Math.Round(avgReturnLosers, 2),
            AvgRealizedRWinners = Math.Round(avgRWinners, 2),
            AvgRealizedRLosers = Math.Round(avgRLosers, 2),

            AvgPeakRWinners = Math.Round(avgPeakRWinners, 2),
            AvgPeakRLosers = Math.Round(avgPeakRLosers, 2),
            AvgPeakPctWinners = Math.Round(avgPeakPctWinners, 2),
            AvgPeakPctLosers = Math.Round(avgPeakPctLosers, 2),

            AvgHeatRWinners = Math.Round(avgHeatRWinners, 2),
            AvgHeatRLosers = Math.Round(avgHeatRLosers, 2),
            AvgHeatPctWinners = Math.Round(avgHeatPctWinners, 2),
            AvgHeatPctLosers = Math.Round(avgHeatPctLosers, 2),

            RoundTripFailuresCount = roundTripCount,
            RoundTripLostPnL = Math.Round(roundTripLoss, 2),

            AvgCaptureEfficiencyPct = Math.Round(avgCaptureEff, 1),

            AvgVolumeRatioWinners = Math.Round(avgVolRatioWinners, 2),
            AvgVolumeRatioLosers = Math.Round(avgVolRatioLosers, 2),
            PctVolumeSurgeWinners = Math.Round(pctVolSurgeWinners, 1),
            PctVolumeSurgeLosers = Math.Round(pctVolSurgeLosers, 1),

            PctAbove200EmaWinners = Math.Round(pctAbove200Winners, 1),
            PctAbove200EmaLosers = Math.Round(pctAbove200Losers, 1),
            AvgDistanceTo200EmaWinners = Math.Round(avgDist200Winners, 1),
            AvgDistanceTo200EmaLosers = Math.Round(avgDist200Losers, 1),

            PctMarketTailwindWinners = Math.Round(pctTailwindWinners, 1),
            PctMarketTailwindLosers = Math.Round(pctTailwindLosers, 1),

            AvgHoldingDaysWinners = Math.Round(avgHoldWinners, 1),
            AvgHoldingDaysLosers = Math.Round(avgHoldLosers, 1),

            AvgPostExitMaxRWinners = Math.Round(avgPostExitRWinners, 2),
            AvgPostExitMaxRLosers = Math.Round(avgPostExitRLosers, 2),
            LeftMoneyOnTableCount = leftMoneyCount,
            ExitSavedFromDrawdownCount = drawdownSavedCount,

            FailureModes = failureModes
        };
    }

    private static string GetFailureModeDescription(string mode) => mode switch
    {
        "Round-Trip Failure" => "Trade reached >= 1.5R in profit, but reversed into a full loss without a breakeven stop",
        "Counter-Trend Entry" => "Entered while stock was below 200 EMA; fighting institutional long-term trend",
        "Overextended Entry" => "Entered >25% above 200 EMA; suffered rubber-band mean reversion pullback",
        "Low Volume Breakout" => "Breakout volume was dry (<0.9x 20d avg); lack of buying follow-through",
        "Hostile Market Regime" => "Entered when Nifty 50 was pulling back or declining below 20 EMA",
        "Immediate Heat Failure" => "Suffered immediate severe adverse excursion (>0.8R) right after entry",
        _ => "Standard operational loss within expected system parameters"
    };

    private List<MatchedTrade> ReadMatchedTrades()
    {
        var trades = new List<MatchedTrade>();
        if (!File.Exists(_journalPath))
            return trades;

        ExcelProcessHelper.EnsureFileAccessible(_journalPath);
        using var stream = new FileStream(_journalPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        using var workbook = new XLWorkbook(stream);

        var ws = workbook.Worksheets.FirstOrDefault(w => w.Name == "MatchedTrades");
        if (ws == null) return trades;

        var lastRow = ws.LastRowUsed()?.RowNumber() ?? 1;

        for (var row = 2; row <= lastRow; row++)
        {
            var tradeId = ws.Cell(row, 1).GetString().Trim();
            var symbol = ws.Cell(row, 2).GetString().Trim();
            if (string.IsNullOrWhiteSpace(tradeId) || string.IsNullOrWhiteSpace(symbol))
                continue;

            var entryPrice = ws.Cell(row, 3).GetValue<decimal>();
            var exitPrice = ws.Cell(row, 4).GetValue<decimal>();
            var quantity = ws.Cell(row, 5).GetValue<int>();
            var grossPnL = ws.Cell(row, 6).GetValue<decimal>();
            var charges = ws.Cell(row, 7).GetValue<decimal>();
            var netPnL = ws.Cell(row, 8).GetValue<decimal>();

            var buyTime = ws.Cell(row, 9).GetDateTime();
            var sellTime = ws.Cell(row, 10).GetDateTime();
            var holdingDays = ws.Cell(row, 11).GetValue<double>();
            var tradeType = ws.Cell(row, 12).GetString().Trim();

            decimal? stopLoss = null;
            var slCell = ws.Cell(row, 13);
            if (!slCell.IsEmpty() && decimal.TryParse(slCell.GetString(), NumberStyles.Any, CultureInfo.InvariantCulture, out var parsedSl))
                stopLoss = parsedSl;
            else if (!slCell.IsEmpty() && slCell.DataType == XLDataType.Number)
                stopLoss = slCell.GetValue<decimal>();

            trades.Add(new MatchedTrade
            {
                TradeId = tradeId,
                Symbol = symbol,
                EntryPrice = entryPrice,
                ExitPrice = exitPrice,
                Quantity = quantity,
                GrossPnL = grossPnL,
                Charges = charges,
                NetPnL = netPnL,
                BuyTime = buyTime,
                SellTime = sellTime,
                HoldingDays = holdingDays,
                TradeGrade = tradeType, // store Trade Type here
                StopLossPrice = stopLoss
            });
        }

        return trades;
    }

    private string ResolveTicker(string rawSymbol, Dictionary<string, string> watchlistLookup)
    {
        var clean = rawSymbol.Trim();
        if (_aliases.TryGetValue(clean, out var aliasTicker))
            return aliasTicker.EndsWith(".NS", StringComparison.OrdinalIgnoreCase) ? aliasTicker[..^3] : aliasTicker;

        if (watchlistLookup.TryGetValue(clean, out var wlTicker))
            return wlTicker;

        // Try partial match
        foreach (var (k, v) in watchlistLookup)
        {
            if (clean.Contains(k, StringComparison.OrdinalIgnoreCase) || k.Contains(clean, StringComparison.OrdinalIgnoreCase))
                return v;
        }

        return clean.ToUpperInvariant();
    }

    private List<HistoricalCandle> LoadCandles(string tickerOrSymbol)
    {
        var yahooName = tickerOrSymbol.StartsWith("^")
            ? tickerOrSymbol
            : (tickerOrSymbol.EndsWith(".NS", StringComparison.OrdinalIgnoreCase) ? tickerOrSymbol : $"{tickerOrSymbol}.NS");

        if (_candleCache.TryGetValue(yahooName, out var cached))
            return cached;

        var filePath = Path.Combine(_historicalFolder, $"{yahooName}.csv");
        if (!File.Exists(filePath))
        {
            // Try without .NS if index or alternate
            filePath = Path.Combine(_historicalFolder, $"{tickerOrSymbol}.csv");
        }

        if (!File.Exists(filePath))
        {
            _candleCache[yahooName] = new List<HistoricalCandle>();
            return _candleCache[yahooName];
        }

        var candles = new List<HistoricalCandle>();
        foreach (var line in File.ReadLines(filePath).Skip(1))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var parts = line.Split(',');
            if (parts.Length < 6) continue;

            if (!DateTime.TryParseExact(parts[0], "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var date))
                continue;

            if (!decimal.TryParse(parts[1], NumberStyles.Any, CultureInfo.InvariantCulture, out var open)) continue;
            if (!decimal.TryParse(parts[2], NumberStyles.Any, CultureInfo.InvariantCulture, out var high)) continue;
            if (!decimal.TryParse(parts[3], NumberStyles.Any, CultureInfo.InvariantCulture, out var low)) continue;
            if (!decimal.TryParse(parts[4], NumberStyles.Any, CultureInfo.InvariantCulture, out var close)) continue;
            if (!long.TryParse(parts[5], NumberStyles.Any, CultureInfo.InvariantCulture, out var vol)) continue;

            candles.Add(new HistoricalCandle
            {
                Date = date,
                Open = open,
                High = high,
                Low = low,
                Close = close,
                Volume = vol
            });
        }

        candles = candles.OrderBy(c => c.Date).ToList();
        _candleCache[yahooName] = candles;
        return candles;
    }

    private static Dictionary<DateTime, decimal> CalculateEma(List<HistoricalCandle> candles, int period)
    {
        var emaMap = new Dictionary<DateTime, decimal>();
        if (candles.Count == 0) return emaMap;

        var k = 2.0m / (period + 1);
        decimal prevEma = 0m;

        for (var i = 0; i < candles.Count; i++)
        {
            var close = candles[i].Close;
            if (i < period)
            {
                // Simple average for seed
                prevEma = (prevEma * i + close) / (i + 1);
            }
            else
            {
                prevEma = (close * k) + (prevEma * (1.0m - k));
            }

            emaMap[candles[i].Date.Date] = prevEma;
        }

        return emaMap;
    }

    private static Dictionary<DateTime, decimal> CalculateVolumeSma(List<HistoricalCandle> candles, int period)
    {
        var volMap = new Dictionary<DateTime, decimal>();
        if (candles.Count == 0) return volMap;

        for (var i = 0; i < candles.Count; i++)
        {
            var start = Math.Max(0, i - period + 1);
            var slice = candles.GetRange(start, i - start + 1);
            var avgVol = (decimal)slice.Average(c => c.Volume);
            volMap[candles[i].Date.Date] = avgVol;
        }

        return volMap;
    }

    private static string ResolveHistoricalFolder(string? folder)
    {
        if (!string.IsNullOrWhiteSpace(folder) && Directory.Exists(folder))
            return folder;

        var candidate1 = Path.Combine(AppContext.BaseDirectory, "Data", "Historical", "Yahoo");
        if (Directory.Exists(candidate1)) return candidate1;

        var candidate2 = Path.Combine(Directory.GetCurrentDirectory(), "Data", "Historical", "Yahoo");
        if (Directory.Exists(candidate2)) return candidate2;

        var candidate3 = @"D:\TradingSystem\TradingJournalAutomation\DhanTradingJournal\Data\Historical\Yahoo";
        if (Directory.Exists(candidate3)) return candidate3;

        return candidate1;
    }
}
