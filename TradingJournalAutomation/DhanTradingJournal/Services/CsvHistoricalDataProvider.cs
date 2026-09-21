using System.Globalization;
using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public class CsvHistoricalDataProvider : IHistoricalDataProvider
{
    private readonly string _folder;

    public CsvHistoricalDataProvider(string folder)
    {
        _folder = folder;
    }

    public Task<List<HistoricalCandle>> GetDailyCandles(
        ScreenerInstrument instrument,
        DateTime from,
        DateTime to)
    {
        var filePath = GetFilePath(instrument);

        if (!File.Exists(filePath))
        {
            Console.WriteLine($"Historical cache not found for {instrument.Symbol}: {filePath}");
            return Task.FromResult(new List<HistoricalCandle>());
        }

        var candles = File.ReadLines(filePath)
            .Skip(1)
            .Select(ParseCandle)
            .Where(c => c != null)
            .Select(c => c!)
            .Where(c => c.Date.Date >= from.Date && c.Date.Date <= to.Date)
            .OrderBy(c => c.Date)
            .ToList();

        return Task.FromResult(candles);
    }

    private string GetFilePath(ScreenerInstrument instrument)
    {
        var yahooSymbol = string.IsNullOrWhiteSpace(instrument.YahooSymbol)
            ? $"{instrument.Symbol.ToUpperInvariant()}.NS"
            : instrument.YahooSymbol.ToUpperInvariant();

        return Path.Combine(_folder, $"{yahooSymbol}.csv");
    }

    private static HistoricalCandle? ParseCandle(string line)
    {
        if (string.IsNullOrWhiteSpace(line))
            return null;

        var columns = line.Split(',');
        if (columns.Length < 6)
            return null;

        if (!DateTime.TryParseExact(
                columns[0],
                "yyyy-MM-dd",
                CultureInfo.InvariantCulture,
                DateTimeStyles.None,
                out var date))
        {
            return null;
        }

        if (!TryParseDecimal(columns[1], out var open)) return null;
        if (!TryParseDecimal(columns[2], out var high)) return null;
        if (!TryParseDecimal(columns[3], out var low)) return null;
        if (!TryParseDecimal(columns[4], out var close)) return null;
        if (!long.TryParse(columns[5], NumberStyles.Any, CultureInfo.InvariantCulture, out var volume)) return null;

        return new HistoricalCandle
        {
            Date = date,
            Open = open,
            High = high,
            Low = low,
            Close = close,
            Volume = volume
        };
    }

    private static bool TryParseDecimal(string value, out decimal result) =>
        decimal.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out result);
}
