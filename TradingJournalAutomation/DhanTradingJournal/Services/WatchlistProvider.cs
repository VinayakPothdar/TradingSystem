using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public static class WatchlistProvider
{
    private static readonly string[] Nifty500FileNames =
    [
        "nifty500.csv",
        "nifty500.csv.csv"
    ];

    public static List<ScreenerInstrument> GetDefaultWatchlist()
    {
        var filePath = FindFile(Nifty500FileNames);

        if (filePath == null)
        {
            Console.WriteLine("Nifty 500 watchlist CSV not found in Data\\Watchlists.");
            return [];
        }

        return ReadNifty500Csv(filePath);
    }

    public static List<(string Name, string Ticker, string Category)> GetAvailableIndices()
    {
        var filePath = FindFile(["indices.csv"]);
        if (filePath == null) return [];

        var list = new List<(string Name, string Ticker, string Category)>();
        foreach (var line in File.ReadLines(filePath).Skip(1))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var cols = SplitCsvLine(line);
            if (cols.Count >= 2)
            {
                var name = cols[0].Trim();
                var ticker = cols[1].Trim();
                var category = cols.Count >= 3 ? cols[2].Trim() : "General";
                if (!string.IsNullOrWhiteSpace(name) && !string.IsNullOrWhiteSpace(ticker))
                    list.Add((name, ticker, category));
            }
        }

        return list;
    }

    public static Dictionary<string, string> GetSymbolAliases()
    {
        var filePath = FindFile(["symbol_aliases.csv"]);
        var dict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        if (filePath == null) return dict;

        foreach (var line in File.ReadLines(filePath).Skip(1))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var cols = SplitCsvLine(line);
            if (cols.Count >= 2)
            {
                var tradeSym = cols[0].Trim();
                var yahooTicker = cols[1].Trim();
                if (!string.IsNullOrWhiteSpace(tradeSym) && !string.IsNullOrWhiteSpace(yahooTicker))
                    dict[tradeSym] = yahooTicker;
            }
        }

        return dict;
    }

    private static string? FindFile(string[] candidateNames)
    {
        var folders = new[]
        {
            Path.Combine(AppContext.BaseDirectory, "Data", "Watchlists"),
            Path.Combine(Directory.GetCurrentDirectory(), "Data", "Watchlists"),
            @"D:\TradingSystem\TradingJournalAutomation\DhanTradingJournal\Data\Watchlists"
        };

        foreach (var folder in folders)
        {
            if (!Directory.Exists(folder)) continue;
            foreach (var fileName in candidateNames)
            {
                var path = Path.Combine(folder, fileName);
                if (File.Exists(path)) return path;
            }
        }

        return null;
    }

    private static List<ScreenerInstrument> ReadNifty500Csv(string filePath)
    {
        var instruments = new List<ScreenerInstrument>();

        foreach (var line in File.ReadLines(filePath).Skip(1))
        {
            if (string.IsNullOrWhiteSpace(line))
                continue;

            var columns = SplitCsvLine(line);

            if (columns.Count < 3)
                continue;

            var symbol = columns[2].Trim();

            if (string.IsNullOrWhiteSpace(symbol))
                continue;

            instruments.Add(new ScreenerInstrument
            {
                Name = columns[0].Trim(),
                Industry = columns[1].Trim(),
                Symbol = symbol,
                YahooSymbol = ToYahooSymbol(symbol),
                ExchangeSegment = "NSE_EQ"
            });
        }

        return instruments;
    }

    private static string ToYahooSymbol(string nseSymbol) => $"{nseSymbol.Trim().ToUpperInvariant()}.NS";

    private static List<string> SplitCsvLine(string line)
    {
        var values = new List<string>();
        var current = new List<char>();
        var inQuotes = false;

        for (var i = 0; i < line.Length; i++)
        {
            var c = line[i];

            if (c == '"')
            {
                if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                {
                    current.Add('"');
                    i++;
                }
                else
                {
                    inQuotes = !inQuotes;
                }

                continue;
            }

            if (c == ',' && !inQuotes)
            {
                values.Add(new string([.. current]));
                current.Clear();
                continue;
            }

            current.Add(c);
        }

        values.Add(new string([.. current]));
        return values;
    }
}
