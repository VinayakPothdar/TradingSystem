using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public static class WatchlistProvider
{
    public static List<ScreenerInstrument> GetDefaultWatchlist() =>
    [
        new() { SecurityId = "523445", Symbol = "RELIANCE", ExchangeSegment = "NSE_EQ" },
        new() { SecurityId = "11536", Symbol = "TATASTEEL", ExchangeSegment = "NSE_EQ" },
        new() { SecurityId = "10440", Symbol = "HINDALCO", ExchangeSegment = "NSE_EQ" },
        new() { SecurityId = "7229", Symbol = "MARUTI", ExchangeSegment = "NSE_EQ" },
        new() { SecurityId = "3456", Symbol = "TATAMOTORS", ExchangeSegment = "NSE_EQ" },
        new() { SecurityId = "317", Symbol = "BAJAJ-AUTO", ExchangeSegment = "NSE_EQ" },
        new() { SecurityId = "15355", Symbol = "CANBK", ExchangeSegment = "NSE_EQ" },
    ];
}
