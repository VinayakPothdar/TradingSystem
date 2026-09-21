using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public class StockScreener
{
    private const int LookbackDays = 365;
    private const int BaseWindowDays = 30;
    private const int TrendWindowDays = 60;

    private readonly IHistoricalDataProvider _historicalDataProvider;

    public StockScreener(IHistoricalDataProvider historicalDataProvider)
    {
        _historicalDataProvider = historicalDataProvider;
    }

    public async Task<StockScreenResult> ScreenStock(ScreenerInstrument instrument)
    {
        var result = new StockScreenResult
        {
            Symbol = instrument.Symbol,
            SecurityId = instrument.SecurityId
        };

        var to = DateTime.Today;
        var from = to.AddDays(-LookbackDays);

        var candles = await _historicalDataProvider.GetDailyCandles(
            instrument,
            from,
            to);

        if (candles.Count < 210)
        {
            Console.WriteLine($"Insufficient data for {instrument.Symbol} ({candles.Count} candles)");
            return result;
        }

        var closes = candles.Select(c => c.Close).ToArray();
        var highs = candles.Select(c => c.High).ToArray();

        result.CurrentPrice = closes.Last();
        var ema200Series = CalculateEma(closes, 200);
        result.Ema200 = ema200Series.Last();
        result.PriceVsEma200Pct = Math.Round(((result.CurrentPrice - result.Ema200) / result.Ema200) * 100, 2);

        result.AthWithin63Days = highs.TakeLast(63).Max() >= highs.Max() * 0.995m;
        result.AboveEma200 = result.CurrentPrice >= result.Ema200;
        result.Ema200Rising = ema200Series.Last() > ema200Series[^11];
        result.WithinEmaZone = Math.Abs(result.PriceVsEma200Pct) <= 10m;

        var baseCandles = candles.TakeLast(BaseWindowDays).ToList();
        var trendCandles = candles
            .SkipLast(BaseWindowDays)
            .TakeLast(TrendWindowDays)
            .ToList();

        if (baseCandles.Count >= 10 && trendCandles.Count >= 20)
            ScoreBase(result, baseCandles, trendCandles);

        return result;
    }

    public async Task<List<StockScreenResult>> ScreenAll(
        List<ScreenerInstrument> instruments,
        int delayMs = 300)
    {
        var results = new List<StockScreenResult>();
        var total = instruments.Count;
        var done = 0;

        foreach (var instrument in instruments)
        {
            results.Add(await ScreenStock(instrument));
            done++;

            if (done % 10 == 0)
                Console.WriteLine($"  Screened {done}/{total}...");

            if (delayMs > 0)
                await Task.Delay(delayMs);
        }

        return [.. results
            .OrderByDescending(r => r.PassesMandatoryRules)
            .ThenByDescending(r => r.BaseScore)];
    }

    public static decimal[] CalculateEma(decimal[] prices, int period)
    {
        var ema = new decimal[prices.Length];
        var multiplier = 2m / (period + 1);

        var sum = 0m;
        for (var i = 0; i < period; i++)
            sum += prices[i];

        ema[period - 1] = sum / period;

        for (var i = period; i < prices.Length; i++)
            ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1];

        return ema;
    }

    private static void ScoreBase(
        StockScreenResult result,
        List<HistoricalCandle> baseCandles,
        List<HistoricalCandle> trendCandles)
    {
        var baseLows = baseCandles.Select(c => c.Low).ToList();
        var baseHighs = baseCandles.Select(c => c.High).ToList();
        var baseVolumes = baseCandles.Select(c => (double)c.Volume).ToList();
        var trendVolumes = trendCandles.Select(c => (double)c.Volume).ToList();

        var baseMax = baseHighs.Max();
        var baseMin = baseLows.Min();
        var baseRangePct = (baseMax - baseMin) / baseMin * 100;
        result.BaseTightRange = baseRangePct <= 15m;

        var trendAvgVol = trendVolumes.Average();
        result.BaseVolumeDryUp = trendAvgVol > 0 && baseVolumes.Average() < trendAvgVol * 0.50;

        result.BaseHigherLows = HasHigherLows(baseLows, requiredCount: 2);

        result.BaseSupportConfluence =
            Math.Abs((result.CurrentPrice - result.Ema200) / result.Ema200 * 100) <= 3m;

        var bodies = baseCandles.Select(c => Math.Abs(c.Close - c.Open)).ToList();
        result.BaseCalmCandles = bodies.Average() > 0 && bodies.Max() <= bodies.Average() * 1.5m;

        var supportLevel = baseLows.Min();
        var touches = baseLows.Count(low => Math.Abs((low - supportLevel) / supportLevel) <= 0.015m);
        result.BaseMultipleTouches = touches >= 2;
    }

    private static bool HasHigherLows(List<decimal> lows, int requiredCount)
    {
        if (lows.Count < requiredCount + 1)
            return false;

        var streak = 0;

        for (var i = 1; i < lows.Count; i++)
        {
            streak = lows[i] > lows[i - 1] ? streak + 1 : 0;

            if (streak >= requiredCount)
                return true;
        }

        return false;
    }
}
