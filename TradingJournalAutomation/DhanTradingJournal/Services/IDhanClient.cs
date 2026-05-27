using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public interface IDhanClient
{
    Task<List<TradeExecution>> GetTrades(DateOnly fromDate, DateOnly toDate, int maxPages = 10);

    Task<List<HistoricalCandle>> GetDailyCandles(
        string securityId,
        string exchangeSegment,
        DateTime from,
        DateTime to);
}

